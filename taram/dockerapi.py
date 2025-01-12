from collections.abc import Mapping
from contextlib import asynccontextmanager

import aiodocker
from attrs import define, field
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse


@define(frozen=True)
class DockerapiContainer(Mapping):

    info = field()
    container = field()

    def __getitem__(self, key):
        return self.info[key]

    def __iter__(self):
        return iter(self.info)

    def __len__(self):
        return len(self.info)

    async def call(self, action: str) -> None:
        func = getattr(self.container, action)
        await func()

    def matches(self, name) -> bool:
        return (
            name == self.get("Id")
            or name.startswith("~")
            and (
                name[1:] == self.get("Name", "")[1:]
                or name[1:] == self.get("Config", {}).get("Labels", {}).get("com.docker.compose.service")
            )
        )


@define(frozen=True)
class Dockerapi:

    docker = field()

    @classmethod
    def from_url(cls, url) -> "Dockerapi":
        docker = aiodocker.Docker(url=url)
        return cls(docker)

    async def close(self) -> None:
        await self.docker.close()

    async def get_containers(self):
        for container in await self.docker.containers.list():
            info = await container.show()
            yield DockerapiContainer(info, container)

    async def get_container(self, name: str):
        async for container in self.get_containers():
            if container.matches(name):
                return container

        raise KeyError(f"Container not found: {name}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.dockerapi = Dockerapi.from_url("unix:///var/run/docker.sock")

    yield

    await app.dockerapi.close()


app = FastAPI(lifespan=lifespan)


@app.get("/containers")
async def get_containers():
    containers = {c["Id"]: c.info async for c in app.dockerapi.get_containers()}
    return JSONResponse(containers)


@app.get("/containers/{name}")
async def get_container(name: str):
    try:
        container = await app.dockerapi.get_container(name)
    except KeyError as e:
        raise HTTPException(404, details="Container not found") from e

    return JSONResponse(container.info)


@app.post("/containers/{name}/{action}")
async def post_container_action(name: str, action: str):
    try:
        container = await app.dockerapi.get_container(name)
    except KeyError as e:
        raise HTTPException(404, details="Container not found") from e

    try:
        await container.call(action)
    except AttributeError as e:
        raise HTTPException(400, "Unsupported action") from e

    return JSONResponse({"message": "action completed successfully"})


@app.exception_handler(Exception)
async def unicorn_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        {"message": str(exc)},
        status_code=500,
    )

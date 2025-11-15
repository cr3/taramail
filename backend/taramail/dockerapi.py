import json
import logging
import os
from contextlib import asynccontextmanager

import aiodocker
from attrs import define, field
from fastapi import (
    FastAPI,
    Request,
)
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

logger = logging.getLogger("uvicorn")


class DockerapiError(Exception):
    """Base exception for dockerapi errors."""


class DockerapiNotFoundError(DockerapiError):
    """Raised when a dockerapi service or action is not found."""


@define(frozen=True)
class DockerapiService:

    name = field()
    containers = field(factory=list)

    async def call(self, action: str) -> None:
        for container in self.containers:
            try:
                func = getattr(container, action)
            except AttributeError as e:
                raise DockerapiNotFoundError(f"Action not found: {action}") from e

            await func()


@define(frozen=True)
class Dockerapi:

    docker = field()
    project = field()

    @classmethod
    def from_url(cls, url: str, project: str) -> "Dockerapi":
        docker = aiodocker.Docker(url=url)
        return cls(docker, project)

    async def close(self) -> None:
        await self.docker.close()

    async def get_services(self):
        services = {}
        filters = json.dumps({
            "label": [
                f"com.docker.compose.project={self.project}",
            ],
        })
        for container in await self.docker.containers.list(all=True, filters=filters):
            info = await container.show()
            name = info["Config"]["Labels"]["com.docker.compose.service"]
            services.setdefault(name, DockerapiService(name))
            services[name].containers.append(container)

        return services.values()

    async def get_service(self, name: str):
        filters = json.dumps({
            "label": [
                f"com.docker.compose.project={self.project}",
                f"com.docker.compose.service={name}",
            ],
        })
        containers = await self.docker.containers.list(all=True, filters=filters)
        if not containers:
            raise DockerapiNotFoundError(f"Service not found: {name}")

        return DockerapiService(name, containers)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.dockerapi = Dockerapi.from_url(
        "unix:///var/run/docker.sock",
        os.environ["COMPOSE_PROJECT_NAME"],
    )

    yield

    await app.dockerapi.close()


app = FastAPI(lifespan=lifespan)


@app.get("/services")
async def get_services():
    services = [
        {
            "name": s.name,
            "containers": [c.id for c in s.containers],
        }
        for s in await app.dockerapi.get_services()
    ]
    return JSONResponse(services)


@app.get("/services/{name}")
async def get_service(name: str):
    service = await app.dockerapi.get_service(name)

    return JSONResponse({
        "name": service.name,
        "containers": [c.id for c in service.containers],
    })


@app.post("/services/{name}/{action}")
async def post_service_action(name: str, action: str):
    service = await app.dockerapi.get_service(name)
    await service.call(action)

    return JSONResponse({"message": "action completed successfully"})


error_handlers = {
    DockerapiNotFoundError: 404,
}

def create_error_handler(exc_class, status_code):
    async def error_handler(request: Request, exc: Exception):
        logger.warning(f"{exc_class.__name__} at {request.url}: {exc}")
        return JSONResponse(
            status_code=status_code,
            content={"message": exc_class.__name__, "detail": str(exc)},
        )
    return error_handler

for exc_type, status in error_handlers.items():
    app.exception_handler(exc_type)(create_error_handler(exc_type, status))


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception at {request.url}")
    return JSONResponse(
        status_code=500,
        content={"message": "Unhandled exception"},
    )


# Simplify operation IDs to use route names.
for route in app.routes:
    if isinstance(route, APIRoute):
        route.operation_id = route.name

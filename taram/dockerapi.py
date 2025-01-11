from contextlib import asynccontextmanager

import aiodocker
import docker
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.sync_docker = docker.DockerClient(base_url="unix://var/run/docker.sock", version="auto")
    app.async_docker = aiodocker.Docker(url="unix:///var/run/docker.sock")

    yield

    app.sync_docker.close()
    await app.async_docker.close()


app = FastAPI(lifespan=lifespan)


@app.get("/containers")
async def get_containers():
    containers = {}
    for container in await app.async_docker.containers.list():
        info = await container.show()
        containers.update({info["Id"]: info})

    return JSONResponse(containers)


@app.get("/containers/{container_id}")
async def get_container(container_id: str):
    for container in await app.async_docker.containers.list():
        if container._id == container_id:
            info = await container.show()
            return JSONResponse(info)

    raise HTTPException(404, details="Container ID not found")


@app.post("/containers/{container_id}/{post_action}")
async def post_container_action(container_id: str, post_action: str):
    if post_action == "restart":
        filters = {"id": container_id}
        for container in app.sync_docker.containers.list(all=True, filters=filters):
            container.restart()
    else:
        raise HTTPException(400, "Unsupported action")

    res = {"type": "success", "msg": "command completed successfully"}
    return JSONResponse(res)


@app.exception_handler(Exception)
async def unicorn_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        {"message": str(exc)},
        status_code=500,
    )

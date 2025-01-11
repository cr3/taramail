"""Dockerapi server module."""

from contextlib import contextmanager
from datetime import datetime

from attrs import define
from pytest_xdocker.docker import DockerContainer
from pytest_xdocker.docker_xrun import docker_xrun
from pytest_xdocker.process import ProcessData, ProcessServer


@define(frozen=True)
class DockerapiClient:
    """Dockerapi client.

    :param name: Name of the dockerapi container.
    """

    name: str

    @property
    def container(self):
        return DockerContainer(self.name)

    @property
    def container_id(self):
        return self.container.inspect["Id"]

    @property
    def started_at(self):
        started_at = self.container.inspect["State"]["StartedAt"]
        return datetime.fromisoformat(started_at)


class DockerapiServer(ProcessServer):
    def __init__(self, image, **kwargs):
        """Initilize an dockerapi docker server."""
        super().__init__(**kwargs)
        self.image = image

    def __repr__(self):
        return "{cls}(image={image!r})".format(
            cls=self.__class__.__name__,
            image=self.image,
        )

    def prepare_func(self, controldir):
        """Prepare the function to run the dockerapi image."""
        command = (
            docker_xrun(self.image)
            .with_name(controldir.basename)
            .with_publish(*self.get_cache_publish(controldir, 443))
            .with_volume("/var/run/docker.sock", options="ro")
        )

        return ProcessData("Uvicorn running on", command)

    @contextmanager
    def run(self, name):
        """Return an `DockerapiClient` to the running server."""
        with super().run(name):
            client = DockerapiClient(name)
            yield client

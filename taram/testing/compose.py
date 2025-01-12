"""Compose server module."""

from contextlib import contextmanager
from datetime import datetime

from attrs import define
from more_itertools import only
from pytest_xdocker.docker import DockerContainer, docker
from pytest_xdocker.process import ProcessData, ProcessServer


@define(frozen=True)
class ComposeClient:
    """Compose client.

    :param name: Name of the compose service container.
    """

    name: str

    @property
    def container(self):
        return DockerContainer(self.name)

    @property
    def container_id(self):
        return self.container.inspect["Id"]

    @property
    def ip(self):
        network_settings = self.container.inspect["NetworkSettings"]
        network = only(network_settings["Networks"].values())
        return network["IPAddress"]

    @property
    def started_at(self):
        started_at = self.container.inspect["State"]["StartedAt"]
        return datetime.fromisoformat(started_at)


class ComposeServer(ProcessServer):
    def __init__(self, pattern, project="test", **kwargs):
        """Initilize a compose service."""
        super().__init__(**kwargs)
        self.pattern = pattern
        self.project = project

    def __repr__(self):
        return "{cls}(pattern={pattern!r}, project={project!r})".format(
            cls=self.__class__.__name__,
            pattern=self.pattern,
            project=self.project,
        )

    def prepare_func(self, controldir):
        """Prepare the function to run the compose service."""
        command = (
            docker.compose().with_project_name(self.project).up(controldir.basename).with_force_recreate().with_build()
        )

        return ProcessData(self.pattern, command)

    @contextmanager
    def run(self, name):
        """Return an `ComposeClient` to the running service."""
        with super().run(name):
            yield ComposeClient(f"{self.project}-{name}-1")

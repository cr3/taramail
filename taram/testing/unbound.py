"""Unbound server module."""

from contextlib import contextmanager

from attrs import define
from dns.nameserver import Do53Nameserver
from dns.resolver import Resolver
from pytest_xdocker.docker import DockerContainer
from pytest_xdocker.docker_xrun import docker_xrun
from pytest_xdocker.process import ProcessData, ProcessServer


@define(frozen=True)
class UnboundClient:
    """Unbound client.

    :param name: Name of the unbound container.
    """

    name: str

    @property
    def nameserver(self):
        """Nameserver pointing to the container."""
        container = DockerContainer(self.name)
        ip = container.host_ip(53)
        port = container.host_port(53)
        return Do53Nameserver(ip, port)

    def resolve(self, name):
        """Resolve for address records."""
        resolver = Resolver()
        resolver.nameservers = [self.nameserver]
        return resolver.resolve_name(name)


class UnboundServer(ProcessServer):
    def __init__(self, image, **kwargs):
        """Initilize an unbound docker server."""
        super().__init__(**kwargs)
        self.image = image

    def __repr__(self):
        return "{cls}(image={image!r})".format(
            cls=self.__class__.__name__,
            image=self.image,
        )

    def prepare_func(self, controldir):
        """Prepare the function to run the unbound image."""
        _, host_ports, host_ip = self.get_cache_publish(controldir, 53)
        command = (
            docker_xrun(self.image)
            .with_name(controldir.basename)
            .with_volume("unbound/unbound.conf", "/etc/unbound/unbound.conf", "ro,z")
            .with_publish("53/tcp", host_ports, host_ip)
            .with_publish("53/udp", host_ports, host_ip)
        )

        return ProcessData("start of service", command)

    @contextmanager
    def run(self, name):
        """Return an `UnboundClient` to the running server."""
        with super().run(name):
            client = UnboundClient(name)
            yield client

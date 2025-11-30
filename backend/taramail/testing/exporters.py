"""Exporter fixtures."""

import pytest
from attrs import define
from prometheus_client.parser import text_string_to_metric_families
from yarl import URL

from taramail.http import HTTPSession
from taramail.testing.compose import ComposeService


@define
class Exporter:

    host: str
    port: int

    @classmethod
    def from_service(cls, service: ComposeService) -> "Exporter":
        host = service.ip
        port = service.container.exposed_port
        return cls(host, port)

    @property
    def url(self) -> URL:
        return URL.build(scheme="http", host=self.host, port=self.port)

    def get_metrics(self, path="/metrics", params=None):
        session = HTTPSession(self.url)
        response = session.get(path, params=params)
        return text_string_to_metric_families(response.text)


@pytest.fixture(scope="session")
def blackbox_exporter(compose_server):
    """Blackbox exporter fixture."""
    server = compose_server("Listening on")
    with server.run("blackbox-exporter") as service:
        yield Exporter.from_service(service)


@pytest.fixture(scope="session")
def dovecot_exporter(dovecot_service):
    """Dovecot exporter fixture."""
    return Exporter(dovecot_service.ip, 9166)


@pytest.fixture(scope="session")
def mysqld_exporter(compose_server):
    """Mysqld exporter fixture."""
    server = compose_server("Listening on")
    with server.run("mysqld-exporter") as service:
        yield Exporter.from_service(service)


@pytest.fixture(scope="session")
def postfix_exporter(compose_server):
    """Postfix exporter fixture."""
    server = compose_server("Listening on")
    with server.run("postfix-exporter") as service:
        yield Exporter.from_service(service)

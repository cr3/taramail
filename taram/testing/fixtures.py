"""Taram fixtures."""

import re
from subprocess import check_output

import pytest

from taram.testing.dockerapi import DockerapiServer
from taram.testing.unbound import UnboundServer


def build_image(name):
    """Build an image using docker compose."""
    output = check_output(
        ["docker", "compose", "build", name],  # noqa: S603, S607
        universal_newlines=True,
    )
    match = re.search(r"naming to (?P<name>.*) done", output)
    return match.group("name")


@pytest.fixture
def dockerapi_app():
    from fastapi.testclient import TestClient

    from taram.dockerapi import app

    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def dockerapi_image():
    """Name of the dockerapi image."""
    return build_image("dockerapi")


@pytest.fixture(scope="session")
def dockerapi_client(process, dockerapi_image):
    """Dockerapi client fixture."""
    server = DockerapiServer(dockerapi_image, process=process)
    with server.run("test-dockerapi") as client:
        yield client


@pytest.fixture(scope="session")
def dyndns_image():
    """Name of the dyndns image."""
    return build_image("dyndns")


@pytest.fixture(scope="session")
def unbound_image():
    """Name of the unbound image."""
    return build_image("unbound")


@pytest.fixture(scope="session")
def unbound_client(process, unbound_image):
    """Unbound client fixture."""
    server = UnboundServer(unbound_image, process=process)
    with server.run("test-unbound") as client:
        yield client

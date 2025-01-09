"""Taram fixtures."""

import pytest
from pytest_xdocker.docker import docker

from taram.testing.unbound import UnboundServer


@pytest.fixture(scope="session")
def dyndns_image():
    """Tag for the dyndns image."""
    tag = "test-dyndns"
    docker.build("dyndns").with_tag(tag).execute()
    return tag


@pytest.fixture(scope="session")
def unbound_image():
    """Tag for the unbound image."""
    tag = "test-unound"
    docker.build("unbound").with_tag(tag).execute()
    return tag


@pytest.fixture(scope="session")
def unbound(unbound_image):
    """Unbound client fixture."""
    server = UnboundServer(unbound_image)
    with server.run("test-unbound") as name:
        yield name

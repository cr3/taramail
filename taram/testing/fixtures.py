"""Taram fixtures."""

import pytest

from taram.testing.compose import ComposeServer


@pytest.fixture
def dockerapi_app():
    from fastapi.testclient import TestClient

    from taram.dockerapi import app

    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def dockerapi_client(process):
    """Dockerapi client fixture."""
    server = ComposeServer("Uvicorn running on", process=process)
    with server.run("dockerapi") as client:
        yield client


@pytest.fixture(scope="session")
def unbound_client(process):
    """Unbound client fixture."""
    server = ComposeServer("start of service", process=process)
    with server.run("unbound") as client:
        yield client

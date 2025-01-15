"""Taram fixtures."""

import os
from unittest.mock import patch

import pytest

from taram.testing.compose import ComposeServer


@pytest.fixture(scope="session")
def project():
    return "test"


@pytest.fixture
def dockerapi_app(project):
    from fastapi.testclient import TestClient

    from taram.dockerapi import app

    with patch.dict(os.environ, {"COMPOSE_PROJECT_NAME": project}), TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def dockerapi_client(project, process):
    """Dockerapi client fixture."""
    server = ComposeServer("Uvicorn running on", project=project, process=process)
    with server.run("dockerapi") as client:
        yield client


@pytest.fixture(scope="session")
def unbound_client(project, process):
    """Unbound client fixture."""
    server = ComposeServer("start of service", project=project, process=process)
    with server.run("unbound") as client:
        yield client

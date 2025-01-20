"""Taram fixtures."""

import logging
import os
from unittest.mock import patch

import pytest

from taram.logger import setup_logger
from taram.testing.compose import ComposeServer
from taram.testing.logger import LoggerHandler


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
def clamd_client(project, process):
    """Clamd client fixture."""
    server = ComposeServer("socket found, clamd started", project=project, process=process)
    with server.run("clamd") as client:
        yield client


@pytest.fixture(scope="session")
def dockerapi_client(project, process):
    """Dockerapi client fixture."""
    server = ComposeServer("Uvicorn running on", project=project, process=process)
    with server.run("dockerapi") as client:
        yield client


@pytest.fixture(scope="session")
def redis_client(project, process):
    """Redis client fixture."""
    from redis import StrictRedis as Redis

    server = ComposeServer("Ready to accept connections tcp", project=project, process=process)
    with server.run("redis") as client:
        environ = {
            "REDIS_SLAVEOF_IP": client.ip,
            "REDIS_SLAVEOF_PORT": "6379",
        }
        with patch.dict(os.environ, environ):
            redis = Redis(host=client.ip, port=6379, decode_responses=True, db=0)
            yield redis


@pytest.fixture(scope="session")
def rspamd_client(project, process):
    """Clamd client fixture."""
    server = ComposeServer("listening for control commands", project=project, process=process)
    with server.run("rspamd") as client:
        yield client


@pytest.fixture(scope="session")
def unbound_client(project, process):
    """Unbound client fixture."""
    server = ComposeServer("start of service", project=project, process=process)
    with server.run("unbound") as client:
        yield client


@pytest.fixture(autouse=True)
def logger_handler():
    """Logger handler fixture."""
    handler = LoggerHandler()
    setup_logger(logging.DEBUG, handler)
    try:
        yield handler
    finally:
        setup_logger()

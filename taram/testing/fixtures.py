"""Taram fixtures."""

import logging
import os
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import pytest

from taram.logger import setup_logger
from taram.testing.compose import ComposeServer
from taram.testing.logger import LoggerHandler


@contextmanager
def temp_env_file(env):
    """Yield a temporary env file that can be passed to docker compose."""
    with NamedTemporaryFile(delete=False) as tmp:
        for k, v in env.items():
            tmp.write(f"{k}={v}\n".encode())
        tmp.close()

        try:
            yield tmp.name
        finally:
            os.unlink(tmp.name)


@pytest.fixture(scope="session")
def project():
    return "test"


@pytest.fixture
def dockerapi_app(project):
    from fastapi.testclient import TestClient

    from taram.dockerapi import app

    env = {
        "COMPOSE_PROJECT_NAME": project,
    }
    with patch.dict(os.environ, env), TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def clamd_client(project, process):
    """Clamd client fixture."""
    server = ComposeServer(
        "socket found, clamd started",
        project=project,
        process=process,
    )
    with server.run("clamd") as client:
        yield client


@pytest.fixture(scope="session")
def dockerapi_client(project, process):
    """Dockerapi client fixture."""
    env = {
        "COMPOSE_PROJECT_NAME": project,
    }
    with temp_env_file(env) as env_file:
        server = ComposeServer(
            "Uvicorn running on",
            env_file=env_file,
            project=project,
            process=process,
        )
        with server.run("dockerapi") as client, patch.dict(os.environ, env):
            yield client


@pytest.fixture(scope="session")
def mysql_client(project, process):
    """MySQL client fixture."""
    # These must be static because they are persisted in mysql-vol-1.
    env = {
        "DBNAME": "test",
        "DBUSER": "test",
        "DBPASS": "test",
        "DBROOT": "test",
    }
    with temp_env_file(env) as env_file:
        server = ComposeServer(
            "mysqld: ready for connections",
            env_file=env_file,
            project=project,
            process=process,
        )
        with server.run("mysql") as client, patch.dict(os.environ, env):
            yield client


@pytest.fixture(scope="session")
def redis_client(project, process):
    """Redis client fixture."""
    from redis import StrictRedis

    server = ComposeServer(
        "Ready to accept connections tcp",
        project=project,
        process=process,
    )
    with server.run("redis") as client:
        env = {
            "REDIS_SLAVEOF_IP": client.ip,
            "REDIS_SLAVEOF_PORT": "6379",
        }
        with patch.dict(os.environ, env):
            redis = StrictRedis(
                host=client.ip,
                port=6379,
                decode_responses=True,
                db=0,
            )
            yield redis


@pytest.fixture(scope="session")
def rspamd_client(redis_client, project, process):
    """Clamd client fixture."""
    connection = redis_client.monitor().connection
    env = {
        "REDIS_SLAVEOF_IP": connection.host,
        "REDIS_SLAVEOF_PORT": str(connection.port),
    }
    with temp_env_file(env) as env_file:
        server = ComposeServer(
            "listening for control commands",
            env_file=env_file,
            project=project,
            process=process,
        )
        with server.run("rspamd") as client:
            yield client


@pytest.fixture(scope="session")
def unbound_client(project, process):
    """Unbound client fixture."""
    server = ComposeServer(
        "start of service",
        project=project,
        process=process,
    )
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

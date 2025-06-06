"""Testing fixtures."""

import logging
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from taramail.api import (
    app,
    get_db,
    get_memcached,
    get_queue,
    get_store,
)
from taramail.logger import setup_logger
from taramail.testing.logger import LoggerHandler


@pytest.fixture
def api_app(db_session, memcached_store, redis_queue, redis_store):
    """API testing app."""
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_memcached] = lambda: memcached_store
    app.dependency_overrides[get_queue] = lambda: redis_queue
    app.dependency_overrides[get_store] = lambda: redis_store

    url = db_session.bind.engine.url
    env = {
        "DBDRIVER": url.drivername,
        "DBNAME": url.database,
    }

    with patch.dict(os.environ, env), TestClient(app) as client:
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

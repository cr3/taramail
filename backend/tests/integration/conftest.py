"""Integration testing fixtures."""

import pytest
from sqlalchemy import create_engine

from taramail.db import get_db_url


@pytest.fixture(scope="session")
def db_url(mysql_service):
    """Create a SQLAlchemy engine."""
    return get_db_url()


@pytest.fixture(scope="session")
def db_engine(db_url):
    """Create a SQLAlchemy engine."""
    return create_engine(db_url, echo=True)

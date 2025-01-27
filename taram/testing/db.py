"""Taram database fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from taram.models import SQLModel


def pytest_addoption(parser):
    parser.addoption(
        "--db-url",
        action="store",
        default="sqlite:///:memory:",
        help="Database URL to use for tests.",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    db_url = session.config.getoption("--db-url")
    try:
        # Attempt to create an engine and connect to the database.
        engine = create_engine(
            db_url,
            poolclass=StaticPool,
        )
        connection = engine.connect()
        # Close the connection right after a successful connect.
        connection.close()
    except OperationalError as e:
        pytest.exit(f"Failed to connect to the database at {db_url}: {e}")


@pytest.fixture(scope="session")
def db_url(request):
    """Fixture to get the database URL."""
    return request.config.getoption("--db-url")


@pytest.fixture(scope="session")
def db_engine(db_url):
    """Create a SQLAlchemy engine."""
    connect_args = {"check_same_thread": False}
    engine = create_engine(db_url, connect_args=connect_args)
    SQLModel.metadata.create_all(engine)
    try:
        yield engine
    finally:
        SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a new database session with a rollback at the end of the test."""
    # Create a sessionmaker to manage sessions
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    # Create tables in the database
    connection = db_engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()

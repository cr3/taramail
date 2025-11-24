"""Unit tests for the db module."""

import pytest
from sqlalchemy import select

from taramail.db import (
    db_replace_into,
    get_db_url,
)

from ..models import TextTest


@pytest.mark.parametrize(
    "env, expected",
    [
        ({"DBDRIVER": "driver"}, "driver://"),
        ({"DBDRIVER": "driver", "DBUSER": "user"}, "driver://user@"),
        ({"DBDRIVER": "driver", "DBUSER": "user", "DBPASS": "pass"}, "driver://user:pass@"),
        ({"DBDRIVER": "driver", "DBPORT": "1234"}, "driver://:1234"),
        ({"DBDRIVER": "driver", "DBNAME": "name"}, "driver:///name"),
    ],
)
def test_get_db_url(env, expected):
    """Getting a database URL should get DB variables from the environment."""
    url = get_db_url(env)
    assert url.render_as_string(hide_password=False) == expected



def test_db_replace_into_once(db_session, unique):
    """Replacing into once should insert the value."""
    test_id = unique("integer")
    db_replace_into(db_session, TextTest, {"test_id": test_id, "value": "a"})
    result = db_session.scalar(
        select(TextTest)
        .where(TextTest.test_id == test_id)
        .limit(1)
    )
    assert result.value == "a"


def test_db_replace_into_twice(db_session, unique):
    """Replacing into twice should replace the value."""
    test_id = unique("integer")
    db_replace_into(db_session, TextTest, {"test_id": test_id, "value": "a"})
    db_replace_into(db_session, TextTest, {"test_id": test_id, "value": "b"})
    result = db_session.scalar(
        select(TextTest)
        .where(TextTest.test_id == test_id)
        .limit(1)
    )
    assert result.value == "b"

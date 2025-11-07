"""Integration tests for the SOGo service."""

from hamcrest import (
    assert_that,
    contains_string,
)

from taramail.http import HTTPSession


def test_sogo_service(sogo_service, unique):
    """The SOGo service should return it's name."""
    http_session = HTTPSession(f"http://{sogo_service.ip}:20000/")
    response = http_session.get("/SOGo.index")
    assert_that(response.text, contains_string("SOGo Groupware"))

"""Integration tests for the dockerapi service."""

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    has_entries,
    has_item,
    has_length,
    has_properties,
)
from requests import HTTPError


def test_dockerapi_get_services(dockerapi_session):
    """Getting services should include the dockerapi fixture."""
    result = dockerapi_session.get("/services")
    assert_that(
        result.json(),
        has_item(
            has_entries({
                "name": "dockerapi",
                "containers": has_length(1),
            }),
        ),
    )


def test_dockerapi_get_service(dockerapi_session):
    """Getting a service should include containers."""
    result = dockerapi_session.get("/services/dockerapi")
    assert_that(
        result.json(),
        has_entries({
            "name": "dockerapi",
            "containers": has_length(1),
        }),
    )


def test_dockerapi_post_service_action(dockerapi_session):
    """Posting a show action should return a success message."""
    result = dockerapi_session.post("/services/dockerapi/show")
    assert_that(
        result.json(),
        has_entries({
            "message": contains_string("success"),
        }),
    )


def test_dockerapi_post_invalid_service_action(dockerapi_session):
    """Posting an invalid action should return a 400 status code."""
    with pytest.raises(HTTPError):
        dockerapi_session.post("/services/dockerapi/test")


def test_dockerapi_metrics(dockerapi_exporter):
    """The Docker API service should expose metrics."""
    metrics = dockerapi_exporter.get_metrics()

    assert_that(metrics, has_item(has_properties(name="http_requests")))

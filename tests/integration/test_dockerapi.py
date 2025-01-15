"""Integration tests for the dockerapi service."""

from hamcrest import (
    assert_that,
    has_entries,
    has_item,
    has_length,
)


def test_dockerapi_get_services(dockerapi_app, dockerapi_client):
    """Getting services should include the dockerapi fixture."""
    result = dockerapi_app.get("/services")
    assert_that(
        result.json(),
        has_item(
            has_entries({
                "name": "dockerapi",
                "containers": has_length(1),
            }),
        ),
    )


def test_dockerapi_get_service(dockerapi_app, dockerapi_client):
    """Getting a service should include containers."""
    result = dockerapi_app.get("/services/dockerapi")
    assert_that(
        result.json(),
        has_entries({
            "name": "dockerapi",
            "containers": has_length(1),
        }),
    )


def test_dockerapi_post_service_action(dockerapi_app, dockerapi_client):
    """Posting a restart action should update the StartedAt time."""
    started_at_before = dockerapi_client.started_at
    dockerapi_app.post("/services/dockerapi/restart")
    started_at_after = dockerapi_client.started_at
    assert started_at_before < started_at_after


def test_dockerapi_post_invalid_service_action(dockerapi_app, dockerapi_client):
    """Posting an invalid action should return a 400 status code."""
    result = dockerapi_app.post("/services/dockerapi/test")
    assert result.status_code == 400

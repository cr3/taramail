"""Integration tests for the dockerapi service."""

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    has_entry,
    has_key,
    has_value,
)


def test_dockerapi_get_containers(dockerapi_app, dockerapi_client):
    """Getting containers should include the test-dockerapi fixture."""
    result = dockerapi_app.get("/containers")
    assert_that(
        result.json(),
        has_value(has_entry("Name", contains_string("dockerapi"))),
    )


@pytest.mark.parametrize(
    "name_func",
    [
        pytest.param(lambda c: c.container_id, id="id"),
        pytest.param(lambda c: f"~{c.name}", id="name"),
    ],
)
def test_dockerapi_get_container(dockerapi_app, dockerapi_client, name_func):
    """Getting a container should include IP addresses."""
    name = name_func(dockerapi_client)
    result = dockerapi_app.get(f"/containers/{name}")
    assert_that(result.json(), has_key("Id"))


@pytest.mark.parametrize(
    "name_func",
    [
        pytest.param(lambda c: c.container_id, id="id"),
        pytest.param(lambda c: f"~{c.name}", id="name"),
    ],
)
def test_dockerapi_post_container_action(dockerapi_app, dockerapi_client, name_func):
    """Posting a restart action should update the StartedAt time."""
    started_at_before = dockerapi_client.started_at
    name = name_func(dockerapi_client)
    dockerapi_app.post(f"/containers/{name}/restart")
    started_at_after = dockerapi_client.started_at
    assert started_at_before < started_at_after


def test_dockerapi_post_invalid_container_action(dockerapi_app, dockerapi_client):
    """Posting an invalid action should return a 400 status code."""
    result = dockerapi_app.post(f"/containers/{dockerapi_client.container_id}/test")
    assert result.status_code == 400

"""Integration tests for the dockerapi service."""

from hamcrest import assert_that, has_entry, has_key, has_value


def test_dockerapi_get_containers(dockerapi_app, dockerapi_client):
    """Getting containers should include the test-dockerapi fixture."""
    result = dockerapi_app.get("/containers")
    assert_that(
        result.json(),
        has_value(
            has_entry(
                "Name",
                "/test-dockerapi",
            ),
        ),
    )


def test_dockerapi_get_container(dockerapi_app, dockerapi_client):
    """Getting a container should include IP addresses."""
    result = dockerapi_app.get(f"/containers/{dockerapi_client.container_id}")
    assert_that(
        result.json(),
        has_entry(
            "NetworkSettings",
            has_entry(
                "Networks",
                has_entry(
                    "bridge",
                    has_key("IPAddress"),
                ),
            ),
        ),
    )


def test_dockerapi_post_container_action(dockerapi_app, dockerapi_client):
    """Posting a restart action should update the StartedAt time."""
    started_at_before = dockerapi_client.started_at
    dockerapi_app.post(f"/containers/{dockerapi_client.container_id}/restart")
    started_at_after = dockerapi_client.started_at
    assert started_at_before < started_at_after

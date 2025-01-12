"""Unit tests for the dockerapi module."""

import pytest

from taram.dockerapi import DockerapiContainer


@pytest.mark.parametrize(
    "name, info",
    [
        pytest.param("a", {"Id": "a"}, id="id"),
        pytest.param("~a", {"Name": "/a"}, id="name"),
        pytest.param("~a", {"Config": {"Labels": {"com.docker.compose.service": "a"}}}, id="label"),
    ],
)
def test_dockerapi_container_matches(name, info):
    """A dockerapi container should match on id, name, and service."""
    container = DockerapiContainer(info, None)
    assert container.matches(name)

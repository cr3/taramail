"""Taram fixtures."""

import pytest
from pytest_xdocker.docker import docker


@pytest.fixture(scope="session")
def dyndns_image():
    """Tag for the dyndns image."""
    tag = "test-dyndns"
    docker.build("dyndns").with_tag(tag).execute()
    return tag

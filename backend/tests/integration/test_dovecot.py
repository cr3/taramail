"""Integration tests for the Dovecot service."""

import socket

from hamcrest import (
    assert_that,
    has_item,
    has_properties,
)


def test_dovecot_auth(dovecot_service):
    """The Dovecot auth service should return the VERSION on port 10001."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((dovecot_service.ip, 10001))
        result = s.recv(7)
        assert result == b"VERSION"


def test_dovecot_stats(dovecot_exporter):
    """The Dovecot stats service should return metrics on port 9166."""
    metrics = dovecot_exporter.get_metrics()

    assert_that(metrics, has_item(has_properties(name="dovecot_build_info")))

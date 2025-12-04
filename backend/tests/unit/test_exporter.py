"""Unit tests for the exporter module."""

from unittest.mock import patch

from hamcrest import (
    assert_that,
    has_item,
    has_properties,
)
from prometheus_client.parser import text_string_to_metric_families


def test_exporter_health(exporter_app):
    """The /health endpoint should return 200."""
    response = exporter_app.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("taramail.exporter.check_rspamd_scoring")
@patch("taramail.exporter.check_rspamd_milter")
def test_exporter_check_mysql(mock_milter, mock_scoring, exporter_app):
    """The /check endpoint should check MySQL.."""
    response = exporter_app.get("/check")
    metrics = text_string_to_metric_families(response.text)

    assert_that(metrics, has_item(
        has_properties(
            name='mail_mysql_connection_check',
            samples=has_item(has_properties(value=1.0)),
        ),
    ))

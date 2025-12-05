"""Integration tests for the custom exporter."""

from hamcrest import (
    has_items,
    has_properties,
)
from pytest_xdocker.retry import retry


def test_exporter_check_rspamd(custom_exporter, rspamd_service):
    """The /check endpoint should chck Rspamd."""
    def get_metrics(custom_exporter, rspamd_host):
        return list(custom_exporter.get_metrics("/check", params={
            "rspamd_host": rspamd_host,
        }))

    retry(get_metrics, custom_exporter, rspamd_service.ip).until(has_items(
        has_properties(
            name='mail_rspamd_scoring_check',
            samples=has_items(has_properties(value=1.0)),
        ),
        has_properties(
            name='mail_rspamd_milter_check',
            samples=has_items(has_properties(value=1.0)),
        ),
    ))

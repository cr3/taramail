"""Integration tests for the custom exporter."""

from hamcrest import (
    assert_that,
    has_items,
    has_properties,
)


def test_exporter_check_rspamd(custom_exporter, rspamd_service):
    """The /check endpoint should chck Rspamd."""
    metrics = custom_exporter.get_metrics("/check", params={
        "rspamd_host": rspamd_service.ip,
    })

    assert_that(metrics, has_items(
        has_properties(
            name='mail_rspamd_scoring_check',
            samples=has_items(has_properties(value=1.0)),
        ),
        has_properties(
            name='mail_rspamd_milter_check',
            samples=has_items(has_properties(value=1.0)),
        ),
    ))

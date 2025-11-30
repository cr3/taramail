"""Integration tests for the postfix exporter."""

from hamcrest import (
    assert_that,
    has_item,
    has_properties,
)


def test_postfix_exporter(postfix_exporter):
    """The postfix exporter should expose postfix metrics."""
    metrics = postfix_exporter.get_metrics()

    assert_that(metrics, has_item(has_properties(name="postfix_up")))

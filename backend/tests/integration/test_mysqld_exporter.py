"""Integration tests for the mysqld exporter."""

from hamcrest import (
    assert_that,
    has_item,
    has_properties,
)


def test_mysqld_exporter(mysqld_exporter):
    """The mysqld exporter should expose mysql metrics."""
    metrics = mysqld_exporter.get_metrics()

    assert_that(metrics, has_item(has_properties(name="mysql_version_info")))

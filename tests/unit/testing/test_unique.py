"""Unit tests for the testing unique module."""

from taram.testing.unique import unique_domain


def test_unique_domain_default(unique):
    """Getting a unique domain should return a .com TLD by default."""
    assert unique_domain(unique).endswith(".com")


def test_unique_domain_tld(unique):
    """Getting a unique domain should be able to pass a `tld` argument."""
    assert unique_domain(unique, tld="ca").endswith(".ca")


def test_unique_domain_twice(unique):
    """Getting a domain twice should not return the same value."""
    assert unique_domain(unique) != unique_domain(unique)

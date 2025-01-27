"""Unique data generation."""


def unique_domain(unique, tld="com"):
    """Returns a domain unique to this factory instance."""
    suffix = f".{tld}"
    return unique("text", separator="", suffix=suffix)

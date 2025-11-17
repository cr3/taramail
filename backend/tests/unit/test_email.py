"""Unit tests for the email module."""

import pytest

from taramail.email import (
    InvalidEmail,
    is_email,
    join_email,
    split_email,
    strip_email_tags,
)


@pytest.mark.parametrize("email, expected", [
    ("a@example.com", True),
    ("a@a.com", True),
    ("@a.com", False),
    ("a@", False),
    ("@", False),
    ("a", False),
])
def test_is_email(email, expected):
    """This should return when the string is an email or not."""
    assert is_email(email) is expected


def test_join_email():
    """Joining an email should concatenate the local_part and domain."""
    email = join_email("a", "b.com")
    assert email == "a@b.com"


def test_split_email():
    """Splitting an email should return the local_part and domain."""
    local_part, domain = split_email("a@b.com")
    assert local_part == "a" and domain == "b.com"


def test_split_email_error():
    """Splitting an invalid email should raise."""
    with pytest.raises(InvalidEmail):
        split_email("a")


@pytest.mark.parametrize("email, expected", [
    ("a@example.com", "a@example.com"),
    ("a+tag@example.com", "a@example.com"),
])
def test_strip_email_tags(email, expected):
    """Stripping email tags should return an email without tags."""
    assert strip_email_tags(email) == expected

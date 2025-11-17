"""Email convenience functions."""

import re

from pydantic import (
    EmailStr,
    TypeAdapter,
    ValidationError,
)


class InvalidEmail(Exception):
    """Raised when an invalid email is provided."""


def is_email(email: str) -> bool:
    email_adapter = TypeAdapter(EmailStr)
    try:
        return bool(email_adapter.validate_python(email))
    except ValidationError:
        return False


def split_email(email: str) -> tuple[str, str]:
    if not is_email(email):
        raise InvalidEmail(f"Invalid email: {email}")

    return email.split("@")


def join_email(local_part: str, domain: str) -> str:
    return f"{local_part}@{domain}"


def strip_email_tags(email: str) -> str:
    """Strip tags (plus addressing) from email address."""
    return re.sub(r"^(.*?)\+.*(@.*)$", r"\1\2", email)

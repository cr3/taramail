"""Unit tests for the schema module."""

import pytest
from pydantic import (
    BaseModel,
    ValidationError,
    validate_call,
)

from taramail.schema import DomainStr


class Site(BaseModel):
    domain: DomainStr


def test_domain_str_type():
    """A domain should be a string."""
    with pytest.raises(ValidationError) as e:
        Site(domain=123)  # type: ignore[arg-type]
    assert "should be a valid string" in str(e.value)


@pytest.mark.parametrize("domain, expected", [
    ("example.com", "example.com"),
    ("sub.domain.co.uk", "sub.domain.co.uk"),
    ("MiXeD-Case.Com", "mixed-case.com"),
])
def test_domain_str_lower(domain, expected):
    """An domain should return lower case."""
    assert Site(domain=domain).domain == expected


@pytest.mark.parametrize("domain, expected", [
    ("  example.com", "example.com"),
    ("example.com  ", "example.com"),
    ("  example.com  ", "example.com"),
])
def test_domain_str_trim(domain, expected):
    """A domain should return trimmed."""
    assert Site(domain=domain).domain == expected


@pytest.mark.parametrize("domain", [
    "bücher.de",
    "mañana.es",
    "δoκiμή.gr",
    "пpимep.pф",
    "xn--bcher-kva.de",
])
def test_domain_str_idn(domain):
    """A domain should accept unicode."""
    assert Site(domain=domain).domain == domain.lower()


@pytest.mark.parametrize("domain", [
    "localhost",
])
def test_domain_str_missing_tld(domain):
    """A domain without a TLD should raise."""
    with pytest.raises(ValidationError) as e:
        Site(domain=domain)

    assert "must include a TLD" in str(e.value)


@pytest.mark.parametrize("domain", [
    "-example.com",
    "example-.com",
    "sub.-bad.com",
    "sub.bad-.com",
])
def test_domain_str_hyphen(domain):
    """A domain with a leading or trailing hyphen should raise."""
    with pytest.raises(ValidationError) as e:
        Site(domain=domain)
    assert "Label must not start or end with a hyphen" in str(e.value)


@pytest.mark.parametrize("domain", [
    "exa_mple.com",
    "exa$mple.com",
    "examp🔥le.com",
])
def test_domain_str_invalid(domain):
    """A domain with invalid characters should raise."""
    with pytest.raises(ValidationError) as e:
        Site(domain=domain)
    assert "not allowed" in str(e.value)


def test_domain_str_label_length():
    """A domain with a label greater than 63 characters should raise."""
    ok_label = "a" * 63
    Site(domain=f"{ok_label}.com")  # ok

    bad_label = "a" * 64
    with pytest.raises(ValidationError) as e:
        Site(domain=f"{bad_label}.com")
    assert "Label too long" in str(e.value)


def test_domain_str_total_length():
    """A domain with total length greater than 253 characters should raise."""
    long_labels = ["a" * 63, "b" * 63, "c" * 63, "d" * 63]  # plus dots pushes >253
    too_long = ".".join(long_labels)
    with pytest.raises(ValidationError) as e:
        Site(domain=f"{too_long}.com")
    assert "Domain too long" in str(e.value)


def test_domain_str_optional():
    """A DomainStr could be optional."""
    class MaybeSite(BaseModel):
        domain: DomainStr | None = None

    assert MaybeSite().domain is None
    assert MaybeSite(domain=None).domain is None
    assert MaybeSite(domain="example.com").domain == "example.com"


def test_domain_str_validate_call():
    """A DomainStr could be be used by validate_call."""
    @validate_call
    def create_site(domain: DomainStr) -> str:
        return domain

    assert create_site("example.com") == "example.com"
    with pytest.raises(ValidationError):
        create_site("bad_domain")


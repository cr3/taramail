"""Unit tests for the schemas module."""

import pytest
from pydantic import (
    BaseModel,
    ValidationError,
    validate_call,
)

from taramail.schemas import (
    AliasStr,
    DomainStr,
    GotoStr,
)


class Site(BaseModel):
    alias: AliasStr | None = None
    domain: DomainStr | None = None
    goto: GotoStr | None = None


def test_alias_str_type():
    """A alias should be a string."""
    with pytest.raises(ValidationError) as e:
        Site(alias=123)  # type: ignore[arg-type]
    assert "should be a valid string" in str(e.value)


@pytest.mark.parametrize("alias, expected", [
    ("@example.com", "@example.com"),
    ("@example.com  ", "@example.com"),
    ("  @example.com  ", "@example.com"),
    ("user@example.com", "user@example.com"),
    ("user@example.com  ", "user@example.com"),
    ("  user@example.com  ", "user@example.com"),
])
def test_alias_str_trim(alias, expected):
    """A alias should return trimmed."""
    assert Site(alias=alias).alias == expected


@pytest.mark.parametrize("alias", [
    "example.com",
    "user@",
])
def test_alias_str_invalid(alias):
    """A alias with invalid characters should raise."""
    with pytest.raises(ValidationError) as e:
        Site(alias=alias)
    assert "Invalid alias" in str(e.value)


def test_alias_str_optional():
    """A AliasStr could be optional."""
    assert Site().alias is None
    assert Site(alias=None).alias is None
    assert Site(alias="user@example.com").alias == "user@example.com"


def test_alias_str_validate_call():
    """A AliasStr could be be used by validate_call."""
    @validate_call
    def create_site(alias: AliasStr) -> str:
        return alias

    assert create_site("user@example.com") == "user@example.com"
    with pytest.raises(ValidationError):
        create_site("bad_alias")


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

    assert "should include a TLD" in str(e.value)


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
    assert Site().domain is None
    assert Site(domain=None).domain is None
    assert Site(domain="example.com").domain == "example.com"


def test_domain_str_validate_call():
    """A DomainStr could be be used by validate_call."""
    @validate_call
    def create_site(domain: DomainStr) -> str:
        return domain

    assert create_site("example.com") == "example.com"
    with pytest.raises(ValidationError):
        create_site("bad_domain")


def test_goto_str_type():
    """A goto should be a string."""
    with pytest.raises(ValidationError) as e:
        Site(goto=123)  # type: ignore[arg-type]
    assert "should be a valid string" in str(e.value)


@pytest.mark.parametrize("goto, expected", [
    ("user@localhost", "user@localhost"),
    ("user@example.com", "user@example.com"),
    ("user@example.com  ", "user@example.com"),
    ("  user@example.com  ", "user@example.com"),
    ("user@example.com,", "user@example.com"),
    (",user@example.com", "user@example.com"),
    ("user1@example.com,user2@example.com", "user1@example.com,user2@example.com"),
    ("user1@example.com, user2@example.com", "user1@example.com,user2@example.com"),
    ("user1@example.com ,user2@example.com", "user1@example.com,user2@example.com"),
    (" user1@example.com , user2@example.com ", "user1@example.com,user2@example.com"),
])
def test_goto_str_trim(goto, expected):
    """A goto should return trimmed."""
    assert Site(goto=goto).goto == expected


@pytest.mark.parametrize("goto", [
    "",
    ",",
])
def test_goto_str_empty(goto):
    """An empty goto should raise."""
    with pytest.raises(ValidationError) as e:
        Site(goto=goto)
    assert "should not be empty" in str(e.value)


@pytest.mark.parametrize("goto", [
    "example.com",
    "user@",
    "user@example.com,example.com",
    "example.com,user@example.com",
])
def test_goto_str_invalid_email(goto):
    """A goto with invalid emails should raise."""
    with pytest.raises(ValidationError) as e:
        Site(goto=goto)
    assert "should be a valid email" in str(e.value)


def test_goto_str_optional():
    """A GotoStr could be optional."""
    assert Site().goto is None
    assert Site(goto=None).goto is None
    assert Site(goto="user@example.com").goto == "user@example.com"


def test_goto_str_validate_call():
    """A GotoStr could be be used by validate_call."""
    @validate_call
    def create_site(goto: GotoStr) -> str:
        return goto

    assert create_site("user@example.com") == "user@example.com"
    with pytest.raises(ValidationError):
        create_site("bad_goto")

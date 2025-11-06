"""Unit tests for the dkim module."""

import pytest
from hamcrest import (
    assert_that,
    greater_than,
    has_length,
    has_properties,
    starts_with,
)
from pydantic import ValidationError

from taramail.dkim import (
    DKIMCreate,
    DKIMDuplicate,
)


def test_dkim_create_invalid_domain(dkim_manager):
    """Specifying an invalid domain should raise."""
    with pytest.raises(ValidationError):
        DKIMCreate(domain="localhost")


def test_dkim_create_invalid_selector(dkim_manager, unique):
    """Specifying an invalid selector should raise."""
    with pytest.raises(ValidationError):
        DKIMCreate(domain=unique("domain"), dkim_selector="bad-selector!")


def test_dkim_manager_get_details_without_privkey(dkim_manager, unique):
    """Getting details without privkey should return an empty privkey."""
    create = DKIMCreate(domain=unique("domain"))
    key = dkim_manager.create_key(create)
    details = dkim_manager.get_details(create.domain)
    assert_that(details, has_properties(
        pubkey=key,
        privkey='',
        length="2048",
        dkim_selector=create.dkim_selector,
        dkim_txt=starts_with("v=DKIM1"),
    ))


def test_dkim_manager_get_details_with_privkey(dkim_manager, unique):
    """Getting details with privkey should return a non-empty privkey."""
    create = DKIMCreate(domain=unique("domain"))
    dkim_manager.create_key(create)
    details = dkim_manager.get_details(create.domain, privkey=True)
    assert_that(details, has_properties(privkey=has_length(greater_than(0))))


def test_dkim_manager_add_keys_store(dkim_manager, unique):
    """Adding keys for a domain should set DKIM keys in the store."""
    create = DKIMCreate(domain=unique("domain"), dkim_selector=unique("text"))
    key = dkim_manager.create_key(create)
    store = dkim_manager.store
    assert store.hget("DKIM_PUB_KEYS", create.domain) == key
    assert store.hget("DKIM_SELECTORS", create.domain) == create.dkim_selector
    assert "BEGIN RSA PRIVATE KEY" in store.hget("DKIM_PRIV_KEYS", f"{create.dkim_selector}.{create.domain}")


def test_dkim_manager_duplicate_keys(dkim_manager, unique):
    """Duplicating a key should duplicate for to_domain."""
    create = DKIMCreate(domain=unique("domain"), dkim_selector=unique("text"))
    duplicate = DKIMDuplicate(from_domain=create.domain, to_domain=unique("domain"))
    key = dkim_manager.create_key(create)
    dkim_manager.duplicate_key(duplicate)
    store = dkim_manager.store
    assert store.hget("DKIM_PUB_KEYS", duplicate.to_domain) == key
    assert store.hget("DKIM_SELECTORS", duplicate.to_domain) == create.dkim_selector
    assert "BEGIN RSA PRIVATE KEY" in store.hget("DKIM_PRIV_KEYS", f"{create.dkim_selector}.{duplicate.to_domain}")


def test_dkim_manager_delete_keys(dkim_manager, unique):
    """Deleting keys should delete keys for a domain."""
    create = DKIMCreate(domain=unique("domain"))
    dkim_manager.create_key(create)
    dkim_manager.delete_key(create.domain)
    keys = dkim_manager.get_keys()
    assert keys == {}


def test_dkim_manager_get_keys_empty(dkim_manager):
    """Getting keys for a domain without keys should return an empty dict."""
    keys = dkim_manager.get_keys()
    assert keys == {}


def test_dkim_manager_get_keys_single(dkim_manager, unique):
    """Getting keys for a domain with keys should return a dict of keys."""
    create = DKIMCreate(domain=unique("domain"))
    key = dkim_manager.create_key(create)
    result = dkim_manager.get_keys()
    assert result == {create.domain: key}

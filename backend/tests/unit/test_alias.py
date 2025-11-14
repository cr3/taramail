"""Unit tests for the alias module."""

import pytest
from hamcrest import (
    assert_that,
    has_properties,
)

from taramail.alias import (
    AliasAlreadyExistsError,
    AliasCreate,
    AliasNotFoundError,
    AliasUpdate,
    AliasValidationError,
)
from taramail.domain import (
    DomainCreate,
    DomainNotFoundError,
    DomainUpdate,
)


@pytest.fixture
def domain(domain_manager, unique):
    """Return the domain name for a managed domain."""
    domain = unique("domain")
    domain_create = DomainCreate(domain=domain)
    domain_manager.create_domain(domain_create)
    domain_manager.db.flush()

    return domain


@pytest.mark.parametrize("params, goto", [
    ({"goto": "test@example.com"}, "test@example.com"),
    ({"goto_null": True}, "null@localhost"),
    ({"goto_spam": True}, "spam@localhost"),
    ({"goto_ham": True}, "ham@localhost"),
])
def test_alias_manager_create_alias_goto(params, goto, domain, alias_manager, unique):
    """Creating an alias should create an alias row."""
    address = unique("email", domain=domain)
    alias_create = AliasCreate(
        address=address,
        **params,
    )
    result = alias_manager.create_alias(alias_create)
    alias_manager.db.flush()

    assert_that(result, has_properties(
        address=address,
        goto=goto,
        domain=domain,
    ))


def test_alias_manager_create_alias_catchall(domain, alias_manager, unique):
    """Creating an alias with a catchall should create an alias row."""
    goto = unique("email")
    address = f"@{domain}"
    alias_create = AliasCreate(
        address=address,
        goto=goto,
    )
    result = alias_manager.create_alias(alias_create)
    alias_manager.db.flush()

    assert_that(result, has_properties(
        address=address,
        goto=goto,
        domain=domain,
    ))


def test_alias_manager_create_alias_duplicate(domain, alias_manager, unique):
    """Creating a duplicate alias should raise."""
    address = unique("email", domain=domain)
    alias_create = AliasCreate(
        address=address,
        goto_null=True,
    )
    alias_manager.create_alias(alias_create)
    alias_manager.db.flush()

    with pytest.raises(AliasAlreadyExistsError):
        alias_manager.create_alias(alias_create)


def test_alias_manager_create_alias_max(domain, alias_manager, domain_manager, unique):
    """Creating an alias beyond max aliases should raise."""
    address = unique("email", domain=domain)
    domain_update = DomainUpdate(aliases=0)
    domain_manager.update_domain(domain, domain_update)
    alias_create = AliasCreate(
        address=address,
        goto_null=True,
    )
    with pytest.raises(AliasValidationError):
        alias_manager.create_alias(alias_create)


def test_alias_manager_create_alias_invalid_domain(alias_manager, unique):
    """Creating an alias with an invalid domain should raise."""
    address = unique("email")
    alias_create = AliasCreate(
        address=address,
        goto_null=True,
    )
    with pytest.raises(DomainNotFoundError):
        alias_manager.create_alias(alias_create)


def test_alias_manager_update_alias(domain, alias_manager, unique):
    """Updatig an alias should return the updated details."""
    address = unique("email", domain=domain)
    alias_create = AliasCreate(
        address=address,
        goto_null=True,
    )
    alias_manager.create_alias(alias_create)
    alias_manager.db.flush()

    alias_update = AliasUpdate(
        internal=True,
        active=False,
        sogo_visible=False,
        private_comment="private",
        public_comment="public",
    )
    result = alias_manager.update_alias(address, alias_update)

    assert_that(result, has_properties(
        internal=True,
        active=False,
        sogo_visible=False,
        private_comment="private",
        public_comment="public",
    ))


@pytest.mark.parametrize("params, goto", [
    ({"goto": "test@example.com"}, "test@example.com"),
    ({"goto_null": True}, "null@localhost"),
    ({"goto_spam": True}, "spam@localhost"),
    ({"goto_ham": True}, "ham@localhost"),
])
def test_alias_manager_update_alias_goto(params, goto, domain, alias_manager, unique):
    """Updatig an alias goto should update the goto address."""
    address = unique("email", domain=domain)
    alias_create = AliasCreate(
        address=address,
        goto_null=True,
    )
    alias_manager.create_alias(alias_create)
    alias_manager.db.flush()

    alias_update = AliasUpdate(**params)
    result = alias_manager.update_alias(address, alias_update)

    assert_that(result, has_properties(goto=goto))


def test_alias_manager_delete_alias(domain, alias_manager, unique):
    """Deleting an alias should delete it from everywhere."""
    address = unique("email", domain=domain)
    alias_create = AliasCreate(
        address=address,
        goto_null=True,
    )
    alias_manager.create_alias(alias_create)
    alias_manager.db.flush()

    alias_manager.delete_alias(address)
    with pytest.raises(AliasNotFoundError):
        alias_manager.get_alias_details(address)

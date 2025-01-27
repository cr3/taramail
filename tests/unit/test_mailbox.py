"""Unit tests for the mailbox module."""

import pytest

from taram.mailbox import Mailbox
from taram.models import (
    AliasDomainModel,
    DomainModel,
)
from taram.schemas import (
    DomainCreate,
    DomainUpdate,
)


def test_mailbox_get_origin_domain_without_alias(db_session):
    """Getting an origin domain without an alias should return the domain."""
    result = Mailbox(db_session).get_origin_domain("a.com")
    assert result == "a.com"


def test_mailbox_get_origin_domain_with_alias(db_session):
    """Getting an origin domain with an alias should return the alias."""
    alias_domain = AliasDomainModel(alias_domain="a.com", target_domain="b.com")
    db_session.add(alias_domain)
    db_session.flush()
    result = Mailbox(db_session).get_origin_domain("a.com")
    assert result == "b.com"


def test_mailbox_get_domain_details(db_session):
    """Getting domain details should at least include the domain name."""
    domain = DomainModel(domain="a.com")
    db_session.add(domain)
    db_session.flush()
    result = Mailbox(db_session).get_domain_details("a.com")
    assert result.domain == "a.com"


def test_mailbox_create_domain(db_session):
    """Getting domain templates should return at least one template."""
    domain_create = DomainCreate(
        domain="a.com",
    )
    mailbox = Mailbox(db_session)
    mailbox.create_domain(domain_create)
    db_session.flush()
    result = mailbox.get_domain_details("a.com")
    assert result.domain == "a.com"


def test_mailbox_update_domain(db_session):
    """Updating a domain should return the updated details."""
    domain = DomainModel(domain="a.com", active=True)
    db_session.add(domain)
    db_session.flush()
    domain_update = DomainUpdate(active=False)
    result = Mailbox(db_session).update_domain("a.com", domain_update)
    assert result.active is False


def test_mailbox_delete_domain(db_session):
    """Deleting a domain should delete it from everywhere."""
    domain = DomainModel(domain="a.com", active=True)
    db_session.add(domain)
    mailbox = Mailbox(db_session)
    mailbox.delete_domain("a.com")
    with pytest.raises(KeyError):
        mailbox.get_domain_details("a.com")

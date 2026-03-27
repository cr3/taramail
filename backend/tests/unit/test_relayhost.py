"""Unit tests for the relayhost module."""

import pytest

from taramail.relayhost import (
    RelayHostCreate,
    RelayHostNotFoundError,
    RelayHostUpdate,
    RelayHostValidationError,
)


def test_relayhost_manager_get_relayhost_details(relayhost_manager, unique):
    """Getting relayhost details should include the hostname."""
    hostname = unique("text")
    create = RelayHostCreate(hostname=hostname)
    relayhost = relayhost_manager.create_relayhost(create)
    relayhost_manager.db.flush()

    result = relayhost_manager.get_relayhost_details(relayhost.id)
    assert result.hostname == hostname


def test_relayhost_manager_get_relayhost_details_not_found(relayhost_manager):
    """Getting details for a nonexistent relayhost should raise."""
    with pytest.raises(RelayHostNotFoundError):
        relayhost_manager.get_relayhost_details(99999)


def test_relayhost_manager_get_relayhosts(relayhost_manager, unique):
    """Getting relayhosts should return all relayhosts."""
    hostname = unique("text")
    create = RelayHostCreate(hostname=hostname)
    relayhost_manager.create_relayhost(create)
    relayhost_manager.db.flush()

    result = relayhost_manager.get_relayhosts()
    assert any(r.hostname == hostname for r in result)


def test_relayhost_manager_create_relayhost(relayhost_manager, unique):
    """Creating a relayhost should make the details available."""
    hostname = unique("text")
    create = RelayHostCreate(hostname=hostname, username="user", password="pass")
    relayhost = relayhost_manager.create_relayhost(create)
    relayhost_manager.db.flush()

    result = relayhost_manager.get_relayhost_details(relayhost.id)
    assert result.hostname == hostname
    assert result.username == "user"


def test_relayhost_manager_create_relayhost_empty_hostname(relayhost_manager):
    """Creating a relayhost with empty hostname should raise."""
    create = RelayHostCreate(hostname="  ")
    with pytest.raises(RelayHostValidationError):
        relayhost_manager.create_relayhost(create)


def test_relayhost_manager_create_relayhost_with_credentials(relayhost_manager, unique):
    """Creating a relayhost should store username and password as-is."""
    hostname = unique("text")
    create = RelayHostCreate(hostname=hostname, username="us:er", password="pa:ss")
    relayhost = relayhost_manager.create_relayhost(create)
    relayhost_manager.db.flush()

    result = relayhost_manager.get_relayhost_details(relayhost.id)
    assert result.username == "us:er"


def test_relayhost_manager_update_relayhost(relayhost_manager, unique):
    """Updating a relayhost should return the updated details."""
    hostname = unique("text")
    create = RelayHostCreate(hostname=hostname)
    relayhost = relayhost_manager.create_relayhost(create)
    relayhost_manager.db.flush()

    new_hostname = unique("text")
    update = RelayHostUpdate(hostname=new_hostname)
    relayhost_manager.update_relayhost(relayhost.id, update)

    result = relayhost_manager.get_relayhost_details(relayhost.id)
    assert result.hostname == new_hostname


def test_relayhost_manager_update_relayhost_not_found(relayhost_manager):
    """Updating a nonexistent relayhost should raise."""
    update = RelayHostUpdate(hostname="new.host.com")
    with pytest.raises(RelayHostNotFoundError):
        relayhost_manager.update_relayhost(99999, update)


def test_relayhost_manager_update_relayhost_active(relayhost_manager, unique):
    """Updating relayhost active status should reflect in details."""
    hostname = unique("text")
    create = RelayHostCreate(hostname=hostname)
    relayhost = relayhost_manager.create_relayhost(create)
    relayhost_manager.db.flush()

    update = RelayHostUpdate(active=False)
    relayhost_manager.update_relayhost(relayhost.id, update)

    result = relayhost_manager.get_relayhost_details(relayhost.id)
    assert result.active is False


def test_relayhost_manager_delete_relayhost(relayhost_manager, unique):
    """Deleting a relayhost should remove it."""
    hostname = unique("text")
    create = RelayHostCreate(hostname=hostname)
    relayhost = relayhost_manager.create_relayhost(create)
    relayhost_manager.db.flush()

    relayhost_manager.delete_relayhost(relayhost.id)
    with pytest.raises(RelayHostNotFoundError):
        relayhost_manager.get_relayhost_details(relayhost.id)


def test_relayhost_manager_delete_relayhost_not_found(relayhost_manager):
    """Deleting a nonexistent relayhost should raise."""
    with pytest.raises(RelayHostNotFoundError):
        relayhost_manager.delete_relayhost(99999)

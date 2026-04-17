"""Unit tests for the transport module."""

import pytest

from taramail.transport import (
    TransportAlreadyExistsError,
    TransportCreate,
    TransportNotFoundError,
    TransportUpdate,
    TransportValidationError,
)


def test_transport_manager_get_transport_details(transport_manager, unique):
    """Getting transport details should include the destination and nexthop."""
    destination = unique("domain")
    create = TransportCreate(destination=destination, nexthop="smtp.example.com")
    transport = transport_manager.create_transport(create)
    transport_manager.db.flush()

    result = transport_manager.get_transport_details(transport.id)
    assert result.destination == destination
    assert result.nexthop == "smtp.example.com"


def test_transport_manager_get_transport_details_not_found(transport_manager):
    """Getting details for a nonexistent transport should raise."""
    with pytest.raises(TransportNotFoundError):
        transport_manager.get_transport_details(99999)


def test_transport_manager_get_transports(transport_manager, unique):
    """Getting transports should return all transports."""
    destination = unique("domain")
    create = TransportCreate(destination=destination, nexthop="smtp.example.com")
    transport_manager.create_transport(create)
    transport_manager.db.flush()

    result = transport_manager.get_transports()
    assert any(t.destination == destination for t in result)


def test_transport_manager_create_transport(transport_manager, unique):
    """Creating a transport should make the details available."""
    destination = unique("domain")
    create = TransportCreate(
        destination=destination,
        nexthop="smtp.example.com",
        username="user",
        password="pass",
    )
    transport = transport_manager.create_transport(create)
    transport_manager.db.flush()

    result = transport_manager.get_transport_details(transport.id)
    assert result.destination == destination
    assert result.username == "user"
    assert result.password_short.startswith("pas")


def test_transport_manager_create_transport_wraps_ip_nexthop(transport_manager, unique):
    """Creating a transport with an IP nexthop should wrap it in brackets."""
    create = TransportCreate(destination=unique("domain"), nexthop="10.0.0.1")
    transport = transport_manager.create_transport(create)
    transport_manager.db.flush()

    result = transport_manager.get_transport_details(transport.id)
    assert result.nexthop == "[10.0.0.1]"


def test_transport_manager_create_transport_empty_nexthop(transport_manager, unique):
    """Creating a transport with empty nexthop should raise."""
    create = TransportCreate(destination=unique("domain"), nexthop="  ")
    with pytest.raises(TransportValidationError):
        transport_manager.create_transport(create)


def test_transport_manager_create_transport_invalid_destination(transport_manager):
    """Creating a transport with an invalid destination should raise."""
    create = TransportCreate(destination="..nope", nexthop="smtp.example.com")
    with pytest.raises(TransportValidationError):
        transport_manager.create_transport(create)


def test_transport_manager_create_transport_wildcard_destination(transport_manager):
    """The "*" wildcard should be a valid destination."""
    create = TransportCreate(destination="*", nexthop="smtp.example.com")
    transport = transport_manager.create_transport(create)
    transport_manager.db.flush()

    result = transport_manager.get_transport_details(transport.id)
    assert result.destination == "*"


def test_transport_manager_create_transport_duplicate_destination(transport_manager, unique):
    """Creating a transport for an existing destination should raise."""
    destination = unique("domain")
    transport_manager.create_transport(
        TransportCreate(destination=destination, nexthop="smtp1.example.com")
    )
    transport_manager.db.flush()

    with pytest.raises(TransportAlreadyExistsError):
        transport_manager.create_transport(
            TransportCreate(destination=destination, nexthop="smtp2.example.com")
        )


def test_transport_manager_create_transport_nexthop_credential_mismatch(transport_manager, unique):
    """Adding a transport with the same nexthop but a different username should raise."""
    transport_manager.create_transport(
        TransportCreate(
            destination=unique("domain"),
            nexthop="smtp.example.com",
            username="alice",
            password="secret",
        )
    )
    transport_manager.db.flush()

    with pytest.raises(TransportValidationError):
        transport_manager.create_transport(
            TransportCreate(
                destination=unique("domain"),
                nexthop="smtp.example.com",
                username="bob",
                password="secret",
            )
        )


def test_transport_manager_create_transport_syncs_credentials(transport_manager, unique):
    """Creating a second transport for the same nexthop should sync credentials."""
    first = transport_manager.create_transport(
        TransportCreate(
            destination=unique("domain"),
            nexthop="smtp.example.com",
            username="alice",
            password="old",
        )
    )
    transport_manager.db.flush()

    transport_manager.create_transport(
        TransportCreate(
            destination=unique("domain"),
            nexthop="smtp.example.com",
            username="alice",
            password="new",
        )
    )
    transport_manager.db.flush()

    result = transport_manager.get_transport_details(first.id)
    assert result.password_short.startswith("new")


def test_transport_manager_update_transport(transport_manager, unique):
    """Updating a transport should return the updated details."""
    transport = transport_manager.create_transport(
        TransportCreate(destination=unique("domain"), nexthop="smtp.example.com")
    )
    transport_manager.db.flush()

    new_destination = unique("domain")
    transport_manager.update_transport(
        transport.id, TransportUpdate(destination=new_destination)
    )

    result = transport_manager.get_transport_details(transport.id)
    assert result.destination == new_destination


def test_transport_manager_update_transport_not_found(transport_manager):
    """Updating a nonexistent transport should raise."""
    update = TransportUpdate(destination="example.com")
    with pytest.raises(TransportNotFoundError):
        transport_manager.update_transport(99999, update)


def test_transport_manager_update_transport_clears_password_when_username_empty(
    transport_manager, unique
):
    """Clearing the username should clear the password."""
    transport = transport_manager.create_transport(
        TransportCreate(
            destination=unique("domain"),
            nexthop="smtp.example.com",
            username="alice",
            password="secret",
        )
    )
    transport_manager.db.flush()

    transport_manager.update_transport(transport.id, TransportUpdate(username=""))

    result = transport_manager.get_transport_details(transport.id)
    assert result.username == ""
    assert result.password_short == ""


def test_transport_manager_delete_transport(transport_manager, unique):
    """Deleting a transport should remove it."""
    transport = transport_manager.create_transport(
        TransportCreate(destination=unique("domain"), nexthop="smtp.example.com")
    )
    transport_manager.db.flush()

    transport_manager.delete_transport(transport.id)
    with pytest.raises(TransportNotFoundError):
        transport_manager.get_transport_details(transport.id)


def test_transport_manager_delete_transport_not_found(transport_manager):
    """Deleting a nonexistent transport should raise."""
    with pytest.raises(TransportNotFoundError):
        transport_manager.delete_transport(99999)

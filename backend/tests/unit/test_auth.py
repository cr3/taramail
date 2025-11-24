"""Unit tests for the auth module."""

from unittest.mock import Mock

import pytest

from taramail.auth import (
    AuthBackend,
    AuthContext,
    AuthMailboxBackend,
    AuthManager,
)
from taramail.models import (
    DomainModel,
    MailboxModel,
)
from taramail.password import hash_password


@pytest.fixture
def auth_context(unique):
    ip, service = unique("ip"), unique("text")
    return AuthContext(ip=ip, service=service)


def test_auth_mailbox_backend_success(auth_context, db_model, db_session, unique):
    """Authenticating with a valid password should return True."""
    password = unique("password")
    hashed_password = hash_password(password)
    domain = db_model(DomainModel)
    mailbox = db_model(MailboxModel, domain=domain.domain, password=hashed_password)
    backend = AuthMailboxBackend(db_session)
    result = backend.authenticate(mailbox.username, password, auth_context)
    assert result is True


@pytest.mark.parametrize("domain_attrs, mailbox_attrs", [
    ({"active": False}, {}),
    ({}, {"active": False}),
    ({}, {"kind": "location"}),
])
def test_auth_mailbox_backend_failure(domain_attrs, mailbox_attrs, auth_context, db_model, db_session, unique):
    """Authenticating with an invalid mailbox should return False."""
    password = unique("password")
    hashed_password = hash_password(password)
    domain = db_model(DomainModel, **domain_attrs)
    mailbox = db_model(MailboxModel, domain=domain.domain, password=hashed_password, **mailbox_attrs)
    backend = AuthMailboxBackend(db_session)
    result = backend.authenticate(mailbox.username, password, auth_context)
    assert result is False


def test_auth_manager_authenticate_success(auth_context, unique):
    """Authenticating with a passing backend should return True."""
    username, password = unique("email"), unique("password")
    backends = [
        Mock(spec=AuthBackend, authenticate=Mock(return_value=False)),
        Mock(spec=AuthBackend, authenticate=Mock(return_value=True)),
    ]
    manager = AuthManager(backends)
    result = manager.authenticate(username, password, auth_context)
    assert result is True


def test_auth_manager_authenticate_failure(auth_context, unique):
    """Authenticating with all failing backends should return False."""
    username, password = unique("email"), unique("password")
    backends = [
        Mock(spec=AuthBackend, authenticate=Mock(return_value=False)),
        Mock(spec=AuthBackend, authenticate=Mock(return_value=False)),
    ]
    manager = AuthManager(backends)
    result = manager.authenticate(username, password, auth_context)
    assert result is False

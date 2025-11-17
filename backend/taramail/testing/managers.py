"""Manager fixtures."""

from unittest.mock import Mock

import pytest

from taramail.alias import AliasManager
from taramail.dkim import DKIMManager
from taramail.domain import DomainManager
from taramail.mailbox import MailboxManager
from taramail.password import PasswordPolicyManager
from taramail.sogo import Sogo


@pytest.fixture
def alias_manager(db_session, domain_manager):
    """Alias manager fixture."""
    return AliasManager(db_session, domain_manager)


@pytest.fixture
def dkim_manager(redis_store):
    """DKIM manager fixture."""
    return DKIMManager(redis_store)


@pytest.fixture
def domain_manager(db_session, redis_store):
    """Domain manager fixture."""
    dockerapi = Mock()
    return DomainManager(db_session, redis_store, dockerapi)


@pytest.fixture
def mailbox_manager(db_session, redis_store, password_policy_manager, sogo):
    """Mailbox manager fixture."""
    return MailboxManager(db_session, redis_store, password_policy_manager, sogo)


@pytest.fixture
def password_policy_manager(redis_store):
    """Password policy manager fixture."""
    manager = PasswordPolicyManager(redis_store)
    try:
        yield manager
    finally:
        manager.reset_policy()


@pytest.fixture
def sogo(db_session, memcached_store):
    """Sogo fixture."""
    return Sogo(db_session, memcached_store)

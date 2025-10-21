"""Manager fixtures."""

from unittest.mock import Mock

import pytest

from taramail.dkim import DKIMManager
from taramail.domain import DomainManager
from taramail.mailbox import MailboxManager
from taramail.sogo import Sogo


@pytest.fixture
def sogo(db_session, memcached_store):
    """Sogo fixture."""
    return Sogo(db_session, memcached_store)


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
def mailbox_manager(db_session, redis_store, sogo):
    """Mailbox manager fixture."""
    return MailboxManager(db_session, redis_store, sogo)

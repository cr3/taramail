"""Unit testing fixtures."""

import pytest

from taramail.store import MemoryStore

redis_queue = pytest.fixture(lambda memory_queue: memory_queue)
redis_store = pytest.fixture(lambda: MemoryStore())
memcached_store = pytest.fixture(lambda: MemoryStore())

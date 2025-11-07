"""FastAPI dependencies."""

from functools import partial
from typing import Annotated

from fastapi import Depends

from taramail.db import (
    DBSession,
    get_db_session,
)
from taramail.queue import (
    Queue,
    RedisQueue,
)
from taramail.store import (
    MemcachedStore,
    RedisStore,
    Store,
)


async def get_db():
    with get_db_session() as db:
        yield db

DbDep = Annotated[DBSession, Depends(get_db)]

get_queue = RedisQueue.from_env
QueueDep = Annotated[Queue, Depends(get_queue)]

get_store = RedisStore.from_env
StoreDep = Annotated[Store, Depends(get_store)]

get_memcached = partial(MemcachedStore.from_host, "memcached")
MemcachedDep = Annotated[Store, Depends(get_memcached)]

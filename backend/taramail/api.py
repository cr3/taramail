"""API service."""

import logging
from functools import partial
from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Response,
)
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles

from taramail.db import (
    DBSession,
    db_transaction,
    get_db_session,
)
from taramail.dkim import (
    DKIMAlreadyExistsError,
    DKIMCreate,
    DKIMDetails,
    DKIMDuplicate,
    DKIMManager,
    DKIMNotFoundError,
    DKIMValidationError,
)
from taramail.domain import (
    DomainAlreadyExistsError,
    DomainManager,
    DomainNotFoundError,
    DomainValidationError,
)
from taramail.mailbox import (
    MailboxAlreadyExistsError,
    MailboxManager,
    MailboxNotFoundError,
    MailboxValidationError,
)
from taramail.queue import (
    Queue,
    RedisQueue,
)
from taramail.schemas import (
    DomainCreate,
    DomainDetails,
    DomainUpdate,
    MailboxCreate,
    MailboxDetails,
    MailboxUpdate,
)
from taramail.sogo import Sogo
from taramail.store import (
    MemcachedStore,
    RedisStore,
    Store,
)

logger = logging.getLogger("uvicorn")
app = FastAPI(
    docs_url="/api/swagger",
    openapi_url="/api/openapi.json",
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

def get_sogo(db: DbDep, memcached: MemcachedDep):
    return Sogo(db, memcached)

SogoDep = Annotated[Sogo, Depends(get_sogo)]

def get_dkim_manager(store: StoreDep):
    return DKIMManager(store)

DKIMManagerDep = Annotated[DKIMManager, Depends(get_dkim_manager)]

def get_domain_manager(db: DbDep, store: StoreDep):
    return DomainManager(db, store)

DomainManagerDep = Annotated[DomainManager, Depends(get_domain_manager)]

def get_mailbox_manager(db: DbDep, store: StoreDep, sogo: SogoDep):
    return MailboxManager(db, store, sogo)

MailboxManagerDep = Annotated[MailboxManager, Depends(get_mailbox_manager)]


@app.get("/api/domains")
def get_domains(manager: DomainManagerDep) -> list[str]:
    return [d.domain for d in manager.get_domains()]


@app.get("/api/domains/{domain}")
def get_domain(domain: str, manager: DomainManagerDep) -> DomainDetails:
    return manager.get_domain_details(domain)


@app.post("/api/domains")
def post_domain(create: DomainCreate, manager: DomainManagerDep) -> DomainDetails:
    with db_transaction(manager.db):
        domain = manager.create_domain(create)
    return manager.get_domain_details(domain.domain)


@app.put("/api/domains/{domain}")
def put_domain(domain: str, update: DomainUpdate, manager: DomainManagerDep) -> DomainDetails:
    with db_transaction(manager.db):
        domain = manager.update_domain(domain, update)

    return manager.get_domain_details(domain.domain)


@app.delete("/api/domains/{domain}")
def delete_domain(domain: str, manager: DomainManagerDep) -> None:
    with db_transaction(manager.db):
        manager.delete_domain(domain)


@app.get("/api/mailboxes")
def get_mailboxes(manager: MailboxManagerDep) -> list[str]:
    return [d.username for d in manager.get_mailboxes()]


@app.get("/api/mailboxes/{username}")
def get_mailbox(username: str, manager: MailboxManagerDep) -> MailboxDetails:
    return manager.get_mailbox_details(username)


@app.post("/api/mailboxes")
def post_mailbox(create: MailboxCreate, manager: MailboxManagerDep) -> MailboxDetails:
    with db_transaction(manager.db):
        mailbox = manager.create_mailbox(create)
    return manager.get_mailbox_details(mailbox.username)


@app.put("/api/mailboxes/{username}")
def put_mailbox(username: str, update: MailboxUpdate, manager: MailboxManagerDep) -> MailboxDetails:
    with db_transaction(manager.db):
        mailbox = manager.update_mailbox(username, update)

    return manager.get_mailbox_details(mailbox.username)


@app.delete("/api/mailboxes/{username}")
def delete_mailbox(username: str, manager: MailboxManagerDep) -> None:
    with db_transaction(manager.db):
        manager.delete_mailbox(username)


@app.get("/api/dkim")
def get_dkim_keys(manager: DKIMManagerDep) -> dict[str, str]:
    return manager.get_keys()


@app.get("/api/dkim/{domain}")
def get_dkim_details(domain: str, manager: DKIMManagerDep) -> DKIMDetails:
    return manager.get_details(domain)


@app.post("/api/dkim")
def post_dkim(create: DKIMCreate, manager: DKIMManagerDep) -> DKIMDetails:
    manager.create_key(create)
    return manager.get_details(create.domain)


@app.post("/api/dkim/duplicate")
def post_dkim_duplicate(duplicate: DKIMDuplicate, manager: DKIMManagerDep) -> DKIMDetails:
    manager.duplicate_key(duplicate)
    return manager.get_details(duplicate.to_domain)


@app.delete("/api/dkim/{domain}")
def delete_dkim(domain: str, manager: DKIMManagerDep) -> None:
    manager.delete_key(domain)


@app.get("/sogo-auth")
def get_sogo_auth(response: Response) -> None:
    response.headers["X-User"] = ""
    response.headers["X-Auth"] = ""
    response.headers["X-Auth-Type"] = ""


@app.get("/rspamd/error")
def get_rspamd_error(request: Request, queue: QueueDep) -> None:
    queue.publish("F2B_CHANNEL", f"Rspamd UI: Invalid password by {request.client.host}")
    raise HTTPException(401, "Invalid password")


error_handlers = {
    DKIMAlreadyExistsError: 409,
    DKIMNotFoundError: 404,
    DKIMValidationError: 400,
    DomainAlreadyExistsError: 409,
    DomainNotFoundError: 404,
    DomainValidationError: 400,
    MailboxAlreadyExistsError: 409,
    MailboxNotFoundError: 404,
    MailboxValidationError: 400,
}

for exc_type, status in error_handlers.items():
    @app.exception_handler(exc_type)
    async def error_handler(request: Request, exc: exc_type, exc_type=exc_type, status=status):
        logger.warning(f"{exc_type.__name__} at {request.url}: {exc}")
        return JSONResponse(
            status_code=status,
            content={"error": exc_type.__name__, "detail": str(exc)},
        )


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception at {request.url}")
    return JSONResponse(
        status_code=500,
        content={"error": "Unhandled exception"},
    )


app.mount("/docs", StaticFiles(directory="./build/html", html=True, check_dir=False))

# Simplify operation IDs to use route names.
for route in app.routes:
    if isinstance(route, APIRoute):
        route.operation_id = route.name

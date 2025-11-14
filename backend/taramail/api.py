"""API service."""

import logging
import re
from pathlib import Path
from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Response,
)
from fastapi.responses import (
    JSONResponse,
)
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape,
)
from pydantic import EmailStr

from taramail.alias import (
    AliasAlreadyExistsError,
    AliasCreate,
    AliasDetails,
    AliasManager,
    AliasNotFoundError,
    AliasUpdate,
    AliasValidationError,
)
from taramail.db import db_transaction
from taramail.deps import (
    DbDep,
    MemcachedDep,
    QueueDep,
    StoreDep,
)
from taramail.dkim import (
    DKIMAlreadyExistsError,
    DKIMCreate,
    DKIMDetails,
    DKIMDuplicate,
    DKIMManager,
    DKIMNotFoundError,
)
from taramail.domain import (
    DomainAlreadyExistsError,
    DomainCreate,
    DomainDetails,
    DomainManager,
    DomainNotFoundError,
    DomainUpdate,
    DomainValidationError,
)
from taramail.mailbox import (
    MailboxAlreadyExistsError,
    MailboxCreate,
    MailboxDetails,
    MailboxManager,
    MailboxNotFoundError,
    MailboxUpdate,
    MailboxValidationError,
)
from taramail.rspamd import RspamdSettings
from taramail.schemas import (
    AliasStr,
    DomainStr,
)
from taramail.sogo import Sogo

logger = logging.getLogger("uvicorn")
app = FastAPI(
    docs_url="/api/swagger",
    openapi_url="/api/openapi.json",
)

env = Environment(
    loader=FileSystemLoader(Path(__file__).with_name("templates")),
    autoescape=select_autoescape(["j2"]),
)
env.filters["regex_replace"] = lambda s, p, r: re.sub(p, r, s)
templates = Jinja2Templates(env=env)


def get_sogo(db: DbDep, memcached: MemcachedDep):
    return Sogo(db, memcached)

SogoDep = Annotated[Sogo, Depends(get_sogo)]

def get_alias_manager(db: DbDep):
    return AliasManager(db)

AliasManagerDep = Annotated[AliasManager, Depends(get_alias_manager)]

def get_dkim_manager(store: StoreDep):
    return DKIMManager(store)

DKIMManagerDep = Annotated[DKIMManager, Depends(get_dkim_manager)]

def get_domain_manager(db: DbDep, store: StoreDep):
    return DomainManager(db, store)

DomainManagerDep = Annotated[DomainManager, Depends(get_domain_manager)]

def get_mailbox_manager(db: DbDep, store: StoreDep, sogo: SogoDep):
    return MailboxManager(db, store, sogo)

MailboxManagerDep = Annotated[MailboxManager, Depends(get_mailbox_manager)]

def get_rspamd_service(db: DbDep):
    return RspamdSettings(db)

RspamdSettingsDep = Annotated[RspamdSettings, Depends(get_rspamd_service)]


@app.get("/api/domains")
def get_domains(manager: DomainManagerDep) -> list[str]:
    return [d.domain for d in manager.get_domains()]


@app.get("/api/domains/{domain}")
def get_domain(domain: DomainStr, manager: DomainManagerDep) -> DomainDetails:
    return manager.get_domain_details(domain)


@app.post("/api/domains")
def post_domain(create: DomainCreate, manager: DomainManagerDep) -> DomainDetails:
    with db_transaction(manager.db):
        domain = manager.create_domain(create)
    return manager.get_domain_details(domain.domain)


@app.put("/api/domains/{domain}")
def put_domain(domain: DomainStr, update: DomainUpdate, manager: DomainManagerDep) -> DomainDetails:
    with db_transaction(manager.db):
        domain = manager.update_domain(domain, update)

    return manager.get_domain_details(domain.domain)


@app.delete("/api/domains/{domain}")
def delete_domain(domain: DomainStr, manager: DomainManagerDep) -> None:
    with db_transaction(manager.db):
        manager.delete_domain(domain)


@app.get("/api/mailboxes")
def get_mailboxes(manager: MailboxManagerDep) -> list[str]:
    return [m.username for m in manager.get_mailboxes()]


@app.get("/api/mailboxes/{username}")
def get_mailbox(username: EmailStr, manager: MailboxManagerDep) -> MailboxDetails:
    return manager.get_mailbox_details(username)


@app.post("/api/mailboxes")
def post_mailbox(create: MailboxCreate, manager: MailboxManagerDep) -> MailboxDetails:
    with db_transaction(manager.db):
        mailbox = manager.create_mailbox(create)
    return manager.get_mailbox_details(mailbox.username)


@app.put("/api/mailboxes/{username}")
def put_mailbox(username: EmailStr, update: MailboxUpdate, manager: MailboxManagerDep) -> MailboxDetails:
    with db_transaction(manager.db):
        mailbox = manager.update_mailbox(username, update)

    return manager.get_mailbox_details(mailbox.username)


@app.delete("/api/mailboxes/{username}")
def delete_mailbox(username: EmailStr, manager: MailboxManagerDep) -> None:
    with db_transaction(manager.db):
        manager.delete_mailbox(username)


@app.get("/api/aliases")
def get_aliases(domain: DomainStr, manager: AliasManagerDep) -> list[str]:
    return [a.address for a in manager.get_aliases(domain)]


@app.get("/api/aliases/{address}")
def get_alias(address: AliasStr, manager: AliasManagerDep) -> AliasDetails:
    return manager.get_alias_details(address)


@app.post("/api/aliases")
def post_alias(create: AliasCreate, manager: AliasManagerDep) -> AliasDetails:
    with db_transaction(manager.db):
        alias = manager.create_alias(create)
    return manager.get_alias_details(alias.address)


@app.put("/api/aliases/{address}")
def put_alias(address: AliasStr, update: AliasUpdate, manager: AliasManagerDep) -> AliasDetails:
    with db_transaction(manager.db):
        alias = manager.update_alias(address, update)

    return manager.get_alias_details(alias.address)


@app.delete("/api/aliases/{address}")
def delete_alias(address: AliasStr, manager: AliasManagerDep) -> None:
    with db_transaction(manager.db):
        manager.delete_alias(address)


@app.get("/api/dkim")
def get_dkim_keys(manager: DKIMManagerDep) -> dict[str, str]:
    return manager.get_keys()


@app.get("/api/dkim/{domain}")
def get_dkim_details(domain: DomainStr, manager: DKIMManagerDep) -> DKIMDetails:
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
def delete_dkim(domain: DomainStr, manager: DKIMManagerDep) -> None:
    manager.delete_key(domain)


@app.api_route("/rspamd/settings", methods=["GET", "HEAD"])
def get_rspamd_settings(request: Request, settings: RspamdSettingsDep) -> Response:
    return templates.TemplateResponse("rspamd_settings.j2", {
        "request": request,
        "allowed_domains_regex": settings.get_allowed_domains_regex(),
        "internal_aliases": settings.get_internal_aliases(),
        "custom_scores": settings.get_custom_scores(),
        "sogo_wl": settings.get_sogo_wl(),
        "whitelist_blocks": settings.get_blocks("whitelist_from", "whitelist_from_mime"),
        "blacklist_blocks": settings.get_blocks("blacklist_from", "blacklist_from_mime"),
    })


@app.get("/rspamd/error")
def get_rspamd_error(request: Request, queue: QueueDep) -> None:
    queue.publish("F2B_CHANNEL", f"Rspamd UI: Invalid password by {request.client.host}")
    raise HTTPException(401, "Invalid password")


@app.get("/sogo-auth")
def get_sogo_auth(response: Response) -> None:
    response.headers["X-User"] = ""
    response.headers["X-Auth"] = ""
    response.headers["X-Auth-Type"] = ""


error_handlers = {
    AliasAlreadyExistsError: 409,
    AliasNotFoundError: 404,
    AliasValidationError: 400,
    DKIMAlreadyExistsError: 409,
    DKIMNotFoundError: 404,
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

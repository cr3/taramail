"""Rspamd router."""

import re
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)
from fastapi.templating import Jinja2Templates
from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape,
)

from taramail.deps import (
    DbDep,
    QueueDep,
)
from taramail.rspamd.settings import RspamdSettings

router = APIRouter(prefix="/rspamd", tags=["rspamd"])

env = Environment(
    loader=FileSystemLoader(Path(__file__).with_name("templates")),
    autoescape=select_autoescape(["j2"]),
)
env.filters["regex_replace"] = lambda s, p, r: re.sub(p, r, s)
templates = Jinja2Templates(env=env)

def get_rspamd_service(db: DbDep):
    return RspamdSettings(db)

RspamdSettingsDep = Annotated[RspamdSettings, Depends(get_rspamd_service)]

@router.api_route("/settings", methods=["GET", "HEAD"])
def get_rspamd_settings(request: Request, settings: RspamdSettingsDep) -> None:
    return templates.TemplateResponse("settings.j2", {
        "request": request,
        "allowed_domains_regex": settings.get_allowed_domains_regex(),
        "internal_aliases": settings.get_internal_aliases(),
        "custom_scores": settings.get_custom_scores(),
        "sogo_wl": settings.get_sogo_wl(),
        "whitelist_blocks": settings.get_blocks("whitelist_from", "whitelist_from_mime"),
        "blacklist_blocks": settings.get_blocks("blacklist_from", "blacklist_from_mime"),
    })


@router.get("/error")
def get_rspamd_error(request: Request, queue: QueueDep) -> None:
    queue.publish("F2B_CHANNEL", f"Rspamd UI: Invalid password by {request.client.host}")
    raise HTTPException(401, "Invalid password")

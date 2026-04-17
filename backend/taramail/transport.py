"""Mail transport management."""

import logging
import re
from ipaddress import ip_address

import idna
from attrs import define
from pydantic import BaseModel
from sqlalchemy import (
    delete,
    select,
    update,
)
from sqlalchemy.exc import (
    IntegrityError,
    NoResultFound,
)

from taramail.db import DBSession
from taramail.email import is_email
from taramail.models import TransportsModel

logger = logging.getLogger(__name__)


class TransportError(Exception):
    """Base exception for transport errors."""


class TransportAlreadyExistsError(TransportError):
    """Raised when a transport already exists."""


class TransportNotFoundError(TransportError):
    """Raised when a transport is not found."""


class TransportValidationError(TransportError):
    """Raised when a transport is invalid."""


class TransportCreate(BaseModel):

    destination: str
    nexthop: str
    username: str = ""
    password: str = ""
    is_mx_based: bool = False
    active: bool = True


class TransportDetails(BaseModel):

    id: int
    destination: str
    nexthop: str
    username: str
    password_short: str
    is_mx_based: bool
    active: bool


class TransportUpdate(BaseModel):

    destination: str | None = None
    nexthop: str | None = None
    username: str | None = None
    password: str | None = None
    is_mx_based: bool | None = None
    active: bool | None = None


_NEXTHOP_BRACKETED = re.compile(r"\[(.+)\].*")


def _normalize_nexthop(nexthop: str) -> str:
    """Wrap bare IP addresses in brackets, as Postfix expects."""
    nexthop = nexthop.strip()
    try:
        ip_address(nexthop)
    except ValueError:
        return nexthop
    return f"[{nexthop}]"


def _strip_brackets(nexthop: str) -> str:
    match = _NEXTHOP_BRACKETED.match(nexthop)
    return match.group(1) if match else nexthop


def _is_valid_domain(value: str) -> bool:
    if not value:
        return False
    try:
        ascii_domain = idna.encode(value, uts46=True).decode("ascii")
    except idna.IDNAError:
        return False
    return len(ascii_domain.split(".")) >= 2


def _validate_destination(destination: str, is_mx_based: bool) -> None:
    if not destination:
        raise TransportValidationError("Destination cannot be empty")

    if is_mx_based:
        try:
            re.compile(destination)
        except re.error as e:
            raise TransportValidationError(f"Invalid destination: {destination}") from e
        return

    if destination == "*" or is_email(destination):
        return

    # ".domain.tld" is allowed, "..domain" is not
    candidate = destination[1:] if destination.startswith(".") else destination
    if not _is_valid_domain(candidate):
        raise TransportValidationError(f"Invalid destination: {destination}")


@define(frozen=True)
class TransportManager:

    db: DBSession

    def get_transport_details(self, transport_id: int) -> TransportDetails:
        try:
            model = self.db.scalars(
                select(TransportsModel)
                .where(TransportsModel.id == transport_id)
            ).one()
        except NoResultFound as e:
            raise TransportNotFoundError(f"Transport {transport_id} not found") from e

        password_short = model.password[:3] + "..." if model.password else ""

        return TransportDetails(
            id=model.id,
            destination=model.destination,
            nexthop=model.nexthop,
            username=model.username,
            password_short=password_short,
            is_mx_based=model.is_mx_based,
            active=model.active,
        )

    def get_transports(self) -> list[TransportsModel]:
        return self.db.scalars(
            select(TransportsModel)
        ).all()

    def create_transport(self, transport_create: TransportCreate) -> TransportsModel:
        nexthop = _normalize_nexthop(transport_create.nexthop)
        if not nexthop:
            raise TransportValidationError("Nexthop cannot be empty")

        destination = transport_create.destination.strip()
        _validate_destination(destination, transport_create.is_mx_based)

        self._check_conflicts(
            destination=destination,
            nexthop=nexthop,
            username=transport_create.username,
            exclude_id=None,
        )

        model = TransportsModel(
            destination=destination,
            nexthop=nexthop,
            username=transport_create.username,
            password=transport_create.password,
            is_mx_based=transport_create.is_mx_based,
            active=transport_create.active,
        )
        self.db.add(model)
        try:
            self.db.flush()
        except IntegrityError as e:
            raise TransportAlreadyExistsError(f"Transport already exists: {destination}") from e

        # Postfix requires identical credentials per nexthop
        self._sync_nexthop_credentials(nexthop, transport_create.username, transport_create.password)
        return model

    def update_transport(self, transport_id: int, transport_update: TransportUpdate) -> TransportsModel:
        try:
            model = self.db.scalars(
                select(TransportsModel)
                .where(TransportsModel.id == transport_id)
            ).one()
        except NoResultFound as e:
            raise TransportNotFoundError(f"Transport {transport_id} not found") from e

        destination = (
            transport_update.destination.strip()
            if transport_update.destination is not None
            else model.destination
        )
        nexthop = (
            _normalize_nexthop(transport_update.nexthop)
            if transport_update.nexthop is not None
            else model.nexthop
        )
        is_mx_based = (
            transport_update.is_mx_based
            if transport_update.is_mx_based is not None
            else model.is_mx_based
        )
        username = (
            transport_update.username
            if transport_update.username is not None
            else model.username
        )

        if not nexthop:
            raise TransportValidationError("Nexthop cannot be empty")
        _validate_destination(destination, is_mx_based)
        self._check_conflicts(
            destination=destination,
            nexthop=nexthop,
            username=username,
            exclude_id=transport_id,
        )

        model.destination = destination
        model.nexthop = nexthop
        model.is_mx_based = is_mx_based
        model.username = username

        if transport_update.password is not None:
            model.password = transport_update.password
        if transport_update.active is not None:
            model.active = transport_update.active

        # Empty username clears the password
        if not model.username:
            model.password = ""

        self._sync_nexthop_credentials(nexthop, model.username, model.password)
        return model

    def delete_transport(self, transport_id: int) -> None:
        result = self.db.execute(
            delete(TransportsModel)
            .where(TransportsModel.id == transport_id)
        )
        if result.rowcount == 0:
            raise TransportNotFoundError(f"Transport {transport_id} not found")

    def _check_conflicts(
        self,
        destination: str,
        nexthop: str,
        username: str,
        exclude_id: int | None,
    ) -> None:
        next_hop_clean = _strip_brackets(nexthop)
        for existing in self.get_transports():
            if exclude_id is not None and existing.id == exclude_id:
                continue
            if existing.destination == destination:
                raise TransportAlreadyExistsError(f"Destination already exists: {destination}")
            same_nexthop = (
                existing.nexthop == nexthop
                or _strip_brackets(existing.nexthop) == next_hop_clean
            )
            if same_nexthop and existing.username != username:
                raise TransportValidationError(f"Nexthop {nexthop} requires matching credentials")

    def _sync_nexthop_credentials(self, nexthop: str, username: str, password: str) -> None:
        self.db.execute(
            update(TransportsModel)
            .where(TransportsModel.nexthop == nexthop)
            .values(username=username, password=password)
        )

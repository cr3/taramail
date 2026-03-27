"""Relay host management."""

import logging

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
from taramail.models import (
    DomainModel,
    RelayHostsModel,
    UserAttributesModel,
)

logger = logging.getLogger(__name__)


class RelayHostError(Exception):
    """Base exception for relay host errors."""


class RelayHostAlreadyExistsError(RelayHostError):
    """Raised when a relay host already exists."""


class RelayHostNotFoundError(RelayHostError):
    """Raised when a relay host is not found."""


class RelayHostValidationError(RelayHostError):
    """Raised when a relay host is invalid."""


class RelayHostCreate(BaseModel):

    hostname: str
    username: str = ""
    password: str = ""
    active: bool = True


class RelayHostDetails(BaseModel):

    id: int
    hostname: str
    username: str
    password_short: str
    active: bool
    used_by_domains: str
    used_by_mailboxes: str


class RelayHostUpdate(BaseModel):

    hostname: str | None = None
    username: str | None = None
    password: str | None = None
    active: bool | None = None


@define(frozen=True)
class RelayHostManager:

    db: DBSession

    def get_relayhost_details(self, relayhost_id: int) -> RelayHostDetails:
        try:
            model = self.db.scalars(
                select(RelayHostsModel)
                .where(RelayHostsModel.id == relayhost_id)
            ).one()
        except NoResultFound as e:
            raise RelayHostNotFoundError(f"Relay host {relayhost_id} not found") from e

        used_by_domains = ", ".join(
            self.db.scalars(
                select(DomainModel.domain)
                .where(DomainModel.relayhost == relayhost_id)
            ).all()
        )

        used_by_mailboxes = ", ".join(
            self.db.scalars(
                select(UserAttributesModel.username)
                .where(UserAttributesModel.relayhost == relayhost_id)
            ).all()
        )

        password_short = model.password[:3] + "..." if model.password else ""

        return RelayHostDetails(
            id=model.id,
            hostname=model.hostname,
            username=model.username,
            password_short=password_short,
            active=model.active,
            used_by_domains=used_by_domains,
            used_by_mailboxes=used_by_mailboxes,
        )

    def get_relayhosts(self) -> list[RelayHostsModel]:
        return self.db.scalars(
            select(RelayHostsModel)
        ).all()

    def create_relayhost(self, relayhost_create: RelayHostCreate) -> RelayHostsModel:
        hostname = relayhost_create.hostname.strip()
        if not hostname:
            raise RelayHostValidationError("Hostname cannot be empty")

        model = RelayHostsModel(
            hostname=hostname,
            username=relayhost_create.username,
            password=relayhost_create.password,
            active=relayhost_create.active,
        )
        self.db.add(model)
        try:
            self.db.flush()
        except IntegrityError as e:
            raise RelayHostAlreadyExistsError(f"Relay host already exists: {hostname}") from e

        return model

    def update_relayhost(self, relayhost_id: int, relayhost_update: RelayHostUpdate) -> RelayHostsModel:
        try:
            model = self.db.scalars(
                select(RelayHostsModel)
                .where(RelayHostsModel.id == relayhost_id)
            ).one()
        except NoResultFound as e:
            raise RelayHostNotFoundError(f"Relay host {relayhost_id} not found") from e

        if relayhost_update.hostname is not None:
            hostname = relayhost_update.hostname.strip()
            if not hostname:
                raise RelayHostValidationError("Hostname cannot be empty")
            model.hostname = hostname

        if relayhost_update.username is not None:
            model.username = relayhost_update.username

        if relayhost_update.password is not None:
            model.password = relayhost_update.password

        if relayhost_update.active is not None:
            model.active = relayhost_update.active

        return model

    def delete_relayhost(self, relayhost_id: int) -> None:
        result = self.db.execute(
            delete(RelayHostsModel)
            .where(RelayHostsModel.id == relayhost_id)
        )
        if result.rowcount == 0:
            raise RelayHostNotFoundError(f"Relay host {relayhost_id} not found")

        # Clear relayhost references on domains and mailboxes
        self.db.execute(
            update(DomainModel)
            .where(DomainModel.relayhost == relayhost_id)
            .values(relayhost=0)
        )
        self.db.execute(
            update(UserAttributesModel)
            .where(UserAttributesModel.relayhost == relayhost_id)
            .values(relayhost=0)
        )

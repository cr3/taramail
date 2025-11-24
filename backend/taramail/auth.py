"""Authentication layer."""

from abc import (
    ABC,
    abstractmethod,
)

from attrs import define
from pydantic import (
    BaseModel,
    EmailStr,
)
from sqlalchemy import select

from taramail.db import DBSession
from taramail.models import (
    DomainModel,
    MailboxModel,
)
from taramail.password import verify_password


class AuthContext(BaseModel):

    ip: str
    service: str


class AuthBackend(ABC):

    @abstractmethod
    def authenticate(self, username: EmailStr, password: str, context: AuthContext) -> bool:
        """Authenticate a username and password."""


@define(frozen=True)
class AuthMailboxBackend(AuthBackend):

    db: DBSession

    def authenticate(self, username: EmailStr, password: str, context: AuthContext) -> bool:
        """Authenticate a mailbox."""
        if hashed_password := self.db.scalar(
            select(
                MailboxModel.password
            )
            .join(DomainModel, MailboxModel.domain == DomainModel.domain)
            .where(
                MailboxModel.kind.not_in(["location", "thing", "group"]),
                MailboxModel.username == username,
                MailboxModel.active == 1,
                DomainModel.active == 1,
            ).limit(1)
        ):
            return verify_password(password, hashed_password)

        return False


@define(frozen=True)
class AuthManager:

    backends: list[AuthBackend]

    def authenticate(self, username: EmailStr, password: str, context: AuthContext) -> bool:
        return any(
            backend.authenticate(username, password, context)
            for backend in self.backends
        )

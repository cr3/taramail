from attrs import define
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    model_validator,
)
from sqlalchemy import (
    and_,
    delete,
    literal,
    or_,
    select,
)
from sqlalchemy.exc import NoResultFound

from taramail.db import DBSession
from taramail.domain import (
    DomainDetails,
    DomainManager,
)
from taramail.models import (
    AliasDomainModel,
    AliasModel,
    MailboxModel,
    SenderAclModel,
    SpamaliasModel,
)
from taramail.schemas import (
    AliasStr,
    DomainStr,
    GotoStr,
)


class AliasError(Exception):
    """Base exception for alias errors."""


class AliasAlreadyExistsError(AliasError):
    """Raised when a alias already exists."""


class AliasNotFoundError(AliasError):
    """Raised when a alias is not found."""


class AliasValidationError(AliasError):
    """Raised when a alias is invalid."""


class AliasGoto(BaseModel):

    goto: GotoStr | None = None
    goto_null: bool | None = None
    goto_spam: bool | None = None
    goto_ham: bool | None = None


class AliasCreate(AliasGoto):

    address: AliasStr
    internal: bool = False
    active: bool = True
    sogo_visible: bool = True
    private_comment: str = Field("", max_length=160)
    public_comment: str = Field("", max_length=160)

    @model_validator(mode="after")
    def check_goto(self):
        if sum(map(bool, [self.goto, self.goto_null, self.goto_spam, self.goto_ham])) != 1:
            raise ValueError("Creating an alias takes only one of goto, goto_null, goto_spam, or goto_ham")

        return self


class AliasDetails(BaseModel):

    address: AliasStr
    goto: GotoStr
    domain: DomainStr
    internal: bool
    active: bool
    sogo_visible: bool
    private_comment: str
    public_comment: str
    in_primary_domain: DomainStr | None


class AliasUpdate(AliasGoto):

    internal: bool | None = None
    active: bool | None = None
    sogo_visible: bool | None = None
    private_comment: str | None = Field(None, max_length=160)
    public_comment: str | None = Field(None, max_length=160)

    @model_validator(mode="after")
    def check_goto(self):
        if sum(map(bool, [self.goto, self.goto_null, self.goto_spam, self.goto_ham])) > 1:
            raise ValueError("Updating an alias takes at most one of goto, goto_null, goto_spam, or goto_ham")

        return self

@define(frozen=True)
class AliasManager:

    db: DBSession

    def get_alias(self, address: EmailStr) -> AliasModel:
        try:
            return self.db.scalars(
                select(AliasModel)
                .where(AliasModel.address == address)
            ).one()
        except NoResultFound as e:
            raise AliasNotFoundError(f"Alias for {address} not found") from e

    def get_alias_details(self, address: EmailStr) -> AliasDetails:
        alias = self.get_alias(address)

        try:
            in_primary_domain = self.db.scalars(
                select(AliasDomainModel.target_domain)
                .where(AliasDomainModel.alias_domain == alias.domain)
            ).one()
        except NoResultFound:
            in_primary_domain = None

        return AliasDetails(
            address=alias.address,
            goto=alias.goto,
            domain=alias.domain,
            internal=alias.internal,
            active=alias.active,
            sogo_visible=alias.sogo_visible,
            private_comment=alias.private_comment,
            public_comment=alias.public_comment,
            in_primary_domain=in_primary_domain,
        )

    def get_aliases(self, domain: DomainStr) -> list[AliasModel]:
        return self.db.scalars(
            select(AliasModel)
            .where(
                AliasModel.domain == domain,
                AliasModel.address != AliasModel.goto,
            )
        ).all()

    def create_alias(self, alias_create: AliasCreate) -> AliasModel:
        # Validate address and goto.
        address = self._validate_address(alias_create.address)
        goto = self._validate_goto(address, alias_create)

        # Validate domain limits.
        local_part, domain = alias_create.address.split("@")
        domain_details = self._get_domain_details(domain)
        if not domain_details.aliases_left:
            raise AliasValidationError("Max aliases exceeded")

        model = AliasModel(
            address=address,
            goto=goto,
            domain=domain,
            internal=alias_create.internal,
            private_comment=alias_create.private_comment,
            public_comment=alias_create.public_comment,
            sogo_visible=alias_create.sogo_visible,
            active=alias_create.active,
        )
        self.db.add(model)

        return model

    def update_alias(self, address: AliasStr, alias_update: AliasUpdate) -> AliasModel:
        alias = self.get_alias(address)

        for attr in ["internal", "active", "sogo_visible", "private_comment", "public_comment"]:
            value = getattr(alias_update, attr)
            if value is not None:
                setattr(alias, attr, value)

        if goto := self._validate_goto(address, alias_update):
            alias.goto = goto

            # Delete from sender_acl to prevent duplicates
            for logged_in_as in goto.split(","):
                self.db.execute(
                    delete(SenderAclModel)
                    .where(
                        SenderAclModel.logged_in_as == logged_in_as,
                        SenderAclModel.send_as == address,
                    )
                )

        return alias

    def delete_alias(self, address: AliasStr) -> None:
        self.db.execute(delete(AliasModel).where(AliasModel.address == address))
        self.db.execute(delete(SenderAclModel).where(SenderAclModel.send_as == address))

    def _validate_address(self, address: AliasStr) -> AliasStr:
        local_part, domain = address.split("@")
        if self.db.scalar(select(AliasModel).where(
            or_(
                AliasModel.address == address,
                AliasModel.address.in_(
                    select(MailboxModel.username)
                    .select_from(MailboxModel, AliasDomainModel)
                    .where(
                        and_(
                            AliasDomainModel.alias_domain == domain,
                            MailboxModel.username == (
                                local_part
                                + literal("@")
                                + AliasDomainModel.target_domain
                            ),
                        )
                    )
                )
            ),
        ).limit(1)):
            raise AliasAlreadyExistsError(f"{address} is already known as an alias, a mailbox or an alias address expanded from an alias domain")

        if self.db.scalar(select(SpamaliasModel).where(SpamaliasModel.address == address).limit(1)):
            raise AliasAlreadyExistsError(f"{address} is already known as a temporary alias address (spam alias address)")

        return address

    def _validate_goto(self, address: AliasStr, alias: AliasGoto) -> GotoStr | None:
        if alias.goto_null:
            goto = "null@localhost"
        elif alias.goto_spam:
            goto = "spam@localhost"
        elif alias.goto_ham:
            goto = "ham@localhost"
        elif alias.goto:
            gotos = alias.goto.split(",")
            if address in gotos:
                raise AliasValidationError("Cannot alias an address to itself")

            for username in gotos:
                if self.db.scalar(select(MailboxModel).filter(
                        MailboxModel.kind.in_(["location", "thing", "group"]),
                        MailboxModel.username == username,
                    ).limit(1)):
                    raise AliasNotFoundError(f"Goto username is invalid: {username}")

            goto = ",".join(gotos)
        else:
            goto = None

        return goto

    def _get_domain_details(self, domain) -> DomainDetails:
        domain_manager = DomainManager(self.db)
        return domain_manager.get_domain_details(domain)

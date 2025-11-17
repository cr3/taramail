"""Rspamd service."""

import re
from collections import defaultdict
from contextlib import suppress
from dataclasses import dataclass

from attrs import (
    define,
    field,
)
from pydantic import (
    EmailStr,
    validate_call,
)
from sqlalchemy import (
    or_,
    select,
)

from taramail.db import DBSession
from taramail.domain import DomainNotFoundError
from taramail.email import (
    InvalidEmail,
    is_email,
    join_email,
    split_email,
    strip_email_tags,
)
from taramail.models import (
    AliasDomainModel,
    AliasModel,
    BccMapsModel,
    DomainModel,
    FilterconfModel,
    MailboxModel,
    SogoFolderInfoModel,
    SogoQuickContactModel,
)
from taramail.schemas import DomainStr
from taramail.store import Store


def escape_slash(s):
    """Convenience function to escape a slash with a backslash."""
    return s.replace("/", "\\/")


@dataclass
class RspamdScoreBlock:
    username_sane: str
    rcpts: list[str]
    reject: float
    greylist: float
    add_header: float


@dataclass
class RspamdListBlock:
    username_sane: str
    priority: int
    rcpts: list[str]
    from_list: list[str]
    from_mime_list: list[str]


@define(frozen=True)
class RspamdSettings:

    db: DBSession

    def get_allowed_domains_regex(self) -> str:
        alias_pairs = self.db.execute(
            select(AliasDomainModel.alias_domain, AliasDomainModel.target_domain)
        ).all()
        alias_domains = {a for a, _ in alias_pairs}
        targets = {t for _, t in alias_pairs}

        active_domains = self.db.scalars(
            select(DomainModel.domain)
            .where(DomainModel.active == 1)
        ).all()
        allowed = sorted(set(active_domains) | alias_domains | targets)
        return "(" + "|".join(re.escape(d) for d in allowed) + ")" if allowed else "()"

    def get_internal_aliases(self) -> list[str]:
        return self.db.scalars(
            select(AliasModel.address)
            .where(AliasModel.active == 1, AliasModel.internal == 1)
        ).all()

    def get_sogo_wl(self) -> dict[str, list[str]]:
        """Whitelist emails from SOGo quick contacts, grouped by user."""
        res = defaultdict(list)
        rows = self.db.execute(
            select(SogoFolderInfoModel.c_path2, SogoQuickContactModel.c_mail)
            .select_from(SogoFolderInfoModel)
            .join(SogoQuickContactModel, SogoQuickContactModel.c_folder_id == SogoFolderInfoModel.c_folder_id)
            .distinct()
        ).all()
        for user, contacts in rows:
            user = user or ""
            for contact in (contacts or "").split(","):
                contact = contact.strip()
                if is_email(contact):
                    res[user].append(contact)
        return res

    def get_custom_scores(self) -> list[RspamdScoreBlock]:
        custom_scores = []

        objects = self.db.scalars(
            select(FilterconfModel.object)
            .where(FilterconfModel.option.in_(["highspamlevel","lowspamlevel"]))
            .distinct()
        ).all()

        for obj in objects:
            rows = self.db.execute(
                select(FilterconfModel.option, FilterconfModel.value)
                .where(
                    FilterconfModel.object == obj,
                    FilterconfModel.option.in_(["highspamlevel","lowspamlevel"]),
                )
            ).all()
            kv = dict(rows)
            if "highspamlevel" in kv and "lowspamlevel" in kv:
                rcpts = self.get_rcpts(obj)
                high = float(kv["highspamlevel"])
                low = float(kv["lowspamlevel"])
                custom_scores.append(RspamdScoreBlock(
                    username_sane=re.sub(r"[^a-zA-Z0-9]+","", obj),
                    rcpts=rcpts,
                    reject=high,
                    greylist=low - 1,
                    add_header=low,
                ))

        return custom_scores

    def get_rcpts(self, obj: EmailStr | DomainStr) -> list[str]:
        return self.get_email_rcpts(obj) if is_email(obj) else self.get_domain_rcpts(obj)

    def get_email_rcpts(self, email: EmailStr) -> list[str]:
        rcpts: list[str] = []

        # Standard aliases (address -> goto = email; exclude domain catchall "@%")
        std_aliases = self.db.scalars(
            select(AliasModel.address)
            .where(AliasModel.goto == email, ~AliasModel.address.like("@%"))
        ).all()
        for addr in std_aliases:
            with suppress(InvalidEmail):
                local_part, domain = split_email(addr)
                rcpts.append(f"/^{escape_slash(local_part)}[+].*{escape_slash(domain)}$/i")
            rcpts.append(escape_slash(addr))

        # Aliases by alias domains
        adq = self.db.scalars(
            select(MailboxModel.local_part + "@" + AliasDomainModel.alias_domain)
            .select_from(MailboxModel)
            .outerjoin(AliasDomainModel, MailboxModel.domain == AliasDomainModel.target_domain)
            .where(MailboxModel.username == email)
        ).all()
        for alias_addr in adq:
            if alias_addr:
                with suppress(InvalidEmail):
                    local_part, domain = split_email(alias_addr)
                    rcpts.append(f"/^{escape_slash(local_part)}[+].*{escape_slash(domain)}$/i")
                rcpts.append(escape_slash(alias_addr))

        return rcpts

    def get_domain_rcpts(self, domain: DomainStr) -> list[str]:
        rcpts: list[str] = [f"/.*@{domain}/i"]

        # Alias domains mapping to this domain.
        ads = self.db.scalars(
            select(AliasDomainModel.alias_domain)
            .where(AliasDomainModel.target_domain == domain)
        ).all()
        rcpts.extend([f"/.*@{ad}/i" for ad in ads])

        # Standard aliases (address) for this domain.
        std = self.db.scalars(
            select(AliasModel.address)
            .where(AliasModel.address.like(f"%@{domain}"))
        ).all()
        for addr in std:
            with suppress(InvalidEmail):
                local_part, domain = split_email(addr)
                rcpts.append(f"/^{escape_slash(local_part)}[+].*{escape_slash(domain)}$/i")
            rcpts.append(escape_slash(addr))

        return rcpts

    def get_blocks(self, option_from: str, option_from_mime: str) -> list[RspamdListBlock]:
        blocks = []

        obj_rows = self.db.scalars(
            select(FilterconfModel.object)
            .where(
                or_(
                    FilterconfModel.option == option_from,
                    FilterconfModel.option == option_from_mime,
                )
            ).distinct()
        ).all()

        for obj in obj_rows:
            priority = 6 if is_email(obj) else 5
            rcpts = self.get_rcpts(obj)
            # lists
            from_list = [
                re.escape(v).replace("\\*", ".*")
                for v in self.db.scalars(
                    select(FilterconfModel.value)
                    .where(
                        FilterconfModel.object == obj,
                        FilterconfModel.option == option_from,
                    )
                ).all()
            ]
            from_mime_list = [
                re.escape(v).replace("\\*", ".*")
                for v in self.db.scalars(
                    select(FilterconfModel.value)
                    .where(
                        FilterconfModel.object == obj,
                        FilterconfModel.option == option_from_mime,
                    )
                ).all()
            ]
            blocks.append(RspamdListBlock(
                username_sane=re.sub(r"[^a-zA-Z0-9]+", "", obj),
                priority=priority,
                rcpts=rcpts,
                from_list=from_list,
                from_mime_list=from_mime_list,
            ))

        return blocks


@define(frozen=True)
class RspamdAliasexp:
    """Alias expansion for Rspamd."""

    db: DBSession
    store: Store
    max_loops: int = field(default=20)

    @validate_call
    def expand_alias(self, rcpt: EmailStr) -> str:
        """Expand an alias to its final mailbox recipient."""
        final_mailboxes: set[str] = set()

        email = strip_email_tags(rcpt)
        if gotos := self._get_gotos(email):
            loop_count = 0
            while gotos and loop_count <= self.max_loops:
                loop_count += 1
                new_gotos: list[str] = []

                for goto in gotos:
                    if username := self._get_mailbox(goto):
                        final_mailboxes.add(username)
                    elif goto_branches := self._expand_goto(goto):
                        new_gotos.extend(goto_branches)

                gotos = list(set(new_gotos))

        if len(final_mailboxes) == 1:
            return final_mailboxes.pop()

        return ""

    def _get_gotos(self, email: EmailStr) -> list[str]:
        """Get initial goto addresses for the recipient."""
        local_part, domain = split_email(email)
        if not self.store.hget("DOMAIN_MAP", domain):
            raise DomainNotFoundError(f"Domain not managed: {domain}")

        if alias := self.db.scalars(
            select(AliasModel.goto)
            .where(AliasModel.address == email, AliasModel.active == 1)
        ).first():
            return alias.split(",")

        if catchall := self.db.scalars(
            select(AliasModel.goto)
            .where(AliasModel.address == f"@{domain}", AliasModel.active == 1)
        ).first():
            return catchall.split(",")

        if target_domain := self.db.scalars(
            select(AliasDomainModel.target_domain)
            .where(AliasDomainModel.alias_domain == domain, AliasDomainModel.active == 1)
        ).first():
            return [join_email(local_part, target_domain)]

        return []

    def _get_mailbox(self, email: EmailStr) -> str | None:
        """Check if email is an active mailbox."""
        return self.db.scalars(
            select(MailboxModel.username)
            .where(
                MailboxModel.username == email,
                MailboxModel.active == 1,
            )
        ).first()

    def _expand_goto(self, goto: str) -> list[str]:
        """Expand a goto address to its branches."""
        try:
            local_part, domain = split_email(goto)
        except InvalidEmail:
            return []

        if not self.store.hget("DOMAIN_MAP", domain):
            return []

        if alias := self.db.scalars(
            select(AliasModel.goto)
            .where(
                AliasModel.address == goto,
                AliasModel.active == 1,
            )
        ).first():
            return alias.split(",")

        if target_domain := self.db.scalars(
            select(AliasDomainModel.target_domain)
            .where(
                AliasDomainModel.alias_domain == domain,
                AliasDomainModel.active == 1,
            )
        ).first():
            return [join_email(local_part, target_domain)]

        return []


@define(frozen=True)
class RspamdBcc:
    """BCC maps handler for Rspamd."""

    db: DBSession

    @validate_call
    def get_bcc_dest(self, rcpt: EmailStr | None = None, sender: EmailStr | None = None) -> str:
        """Get BCC destination for given recipient or sender."""
        for local_dest, bcc_type in [
            (rcpt, "rcpt"),
            (sender, "sender"),
        ]:
            if local_dest:
                local_dest = strip_email_tags(local_dest)
                bcc_dest = self.db.scalars(
                    select(BccMapsModel.bcc_dest)
                    .where(
                        BccMapsModel.type == bcc_type,
                        BccMapsModel.local_dest == local_dest,
                        BccMapsModel.active == 1,
                    )
                ).first()

                if bcc_dest and is_email(bcc_dest):
                    return bcc_dest

        return ""

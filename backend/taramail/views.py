"""Database views."""

from sqlalchemy import select
from sqlalchemy.sql import func
from sqlalchemy_utils.view import (
    CreateView,
    DropView,
    create_view,
)

from taramail.models import (
    AliasDomainModel,
    AliasModel,
    MailboxModel,
    SenderAclModel,
    SieveFiltersModel,
    SQLModel,
)


class SQLViewMixin:
    @classmethod
    def create(cls, op):
        cls.drop(op)
        create_sql = CreateView(cls.__table__.fullname, cls.selectable)
        op.execute(create_sql)
        for idx in cls.__table__.indexes:
            idx.create(op.get_bind())

    @classmethod
    def drop(cls, op):
        drop_sql = DropView(cls.__table__.fullname, cascade=False)
        op.execute(drop_sql)


class GroupedMailAliasesView(SQLViewMixin, SQLModel):
    """View of mail aliases grouped by goto.

    CREATE VIEW grouped_mail_aliases (username, aliases) AS
        SELECT goto, IFNULL(GROUP_CONCAT(address ORDER BY address SEPARATOR ' '), '') AS address FROM alias
        WHERE address!=goto
        AND active = '1'
        AND sogo_visible = '1'
        AND address NOT LIKE '@%'
        GROUP BY goto;
    """

    _base = (
        select(
            AliasModel.goto.label("username"),
            AliasModel.address.label("address"),
        )
        .where(
            AliasModel.address != AliasModel.goto,
            AliasModel.active == 1,
            AliasModel.sogo_visible == 1,
            ~AliasModel.address.like("@%"),
        )
        .order_by(AliasModel.address)
        .subquery()
    )

    selectable = (
        select(
            _base.c.username,
            func.coalesce(
                func.replace(func.group_concat(_base.c.address), ",", " "),
                ""
            ).label("aliases"),
        )
        .group_by(_base.c.username)
    )

    __table__ = create_view(
        "grouped_mail_aliases",
        selectable,
        SQLModel.metadata,
        cascade_on_drop=False,
    )


class GroupedDomainAliasAddressView(SQLViewMixin, SQLModel):
    """View of domain alias addresses grouped by username.

    CREATE VIEW grouped_domain_alias_address (username, ad_alias) AS
        SELECT username, IFNULL(GROUP_CONCAT(local_part, '@', alias_domain SEPARATOR ' '), '') AS ad_alias FROM mailbox
        LEFT OUTER JOIN alias_domain ON target_domain=domain
        GROUP BY username;
    """

    selectable = (
        select(
            MailboxModel.username.label("username"),
            func.coalesce(
                func.group_concat(MailboxModel.local_part + '@' + AliasDomainModel.alias_domain, ' '),
                "",
            ).label("ad_alias"),
        )
        .select_from(
            MailboxModel.__table__.outerjoin(AliasDomainModel, AliasDomainModel.target_domain == MailboxModel.domain)
        )
        .group_by(MailboxModel.username)
    )

    __table__ = create_view(
        "grouped_domain_alias_address",
        selectable,
        SQLModel.metadata,
        cascade_on_drop=False,
    )


class GroupedSenderAclView(SQLViewMixin, SQLModel):
    """View of sender ACLs grouped by logged_in_as.

    CREATE VIEW grouped_sender_acl (username, send_as_acl) AS
        SELECT logged_in_as, IFNULL(GROUP_CONCAT(send_as SEPARATOR ' '), '') AS send_as_acl FROM sender_acl
        WHERE send_as NOT LIKE '@%'
        GROUP BY logged_in_as;
    """

    selectable = (
        select(
            SenderAclModel.logged_in_as.label("username"),
            func.coalesce(func.group_concat(SenderAclModel.send_as), "").label("send_as_acl"),
        )
        .where(SenderAclModel.send_as.not_like("@%"))
        .group_by(SenderAclModel.logged_in_as)
    )

    __table__ = create_view(
        "grouped_sender_acl",
        selectable,
        SQLModel.metadata,
        cascade_on_drop=False,
    )


class GroupedSenderAclExternalView(SQLViewMixin, SQLModel):
    """View of sender ACLs that are external only grouped by logged_in_as.

    CREATE VIEW grouped_sender_acl_external (username, send_as_acl) AS
        SELECT logged_in_as, IFNULL(GROUP_CONCAT(send_as SEPARATOR ' '), '') AS send_as_acl FROM sender_acl
        WHERE send_as NOT LIKE '@%' AND external = '1'
        GROUP BY logged_in_as;
    """

    selectable = (
        select(
            SenderAclModel.logged_in_as.label("username"),
            func.coalesce(func.group_concat(SenderAclModel.send_as), "").label("send_as_acl"),
        )
        .where(
            SenderAclModel.send_as.not_like("@%"),
            SenderAclModel.external == 1,
        )
        .group_by(SenderAclModel.logged_in_as)
    )

    __table__ = create_view(
        "grouped_sender_acl_external",
        selectable,
        SQLModel.metadata,
        cascade_on_drop=False,
    )


class SieveBeforeView(SQLViewMixin, SQLModel):
    """View to apply sieve filtering rules before user's personal sieve rules.

    CREATE VIEW sieve_before (id, username, script_name, script_data) AS
        SELECT md5(script_data), username, script_name, script_data
        FROM sieve_filters
        WHERE filter_type = 'prefilter';
    """

    selectable = (
        select(
            func.md5(SieveFiltersModel.script_data).label("id"),
            SieveFiltersModel.username,
            SieveFiltersModel.script_name,
            SieveFiltersModel.script_data,
        )
        .where(
            SieveFiltersModel.filter_type == "prefilter",
        )
    )

    __table__ = create_view(
        "sieve_before",
        selectable,
        SQLModel.metadata,
        cascade_on_drop=False,
    )


class SieveAfterView(SQLViewMixin, SQLModel):
    """View to apply sieve filtering rules after user's personal sieve rules.

    CREATE VIEW sieve_after (id, username, script_name, script_data) AS
        SELECT md5(script_data), username, script_name, script_data
        FROM sieve_filters
        WHERE filter_type = 'postfilter';"
    """

    selectable = (
        select(
            func.md5(SieveFiltersModel.script_data).label("id"),
            SieveFiltersModel.username,
            SieveFiltersModel.script_name,
            SieveFiltersModel.script_data,
        )
        .where(
            SieveFiltersModel.filter_type == "postfilter",
        )
    )

    __table__ = create_view(
        "sieve_after",
        selectable,
        SQLModel.metadata,
        cascade_on_drop=False,
    )

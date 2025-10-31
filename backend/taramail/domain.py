from contextlib import suppress

from attrs import Factory, define, field
from sqlalchemy import or_, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.sql import func

from taramail.db import DBSession
from taramail.dkim import DKIMCreate, DKIMManager
from taramail.http import HTTPSession
from taramail.models import (
    AliasDomainModel,
    AliasModel,
    BccMapsModel,
    DomainModel,
    MailboxModel,
    Quota2Model,
    Quota2ReplicaModel,
    SenderAclModel,
    SpamaliasModel,
)
from taramail.schemas import (
    DomainCreate,
    DomainDetails,
    DomainUpdate,
)
from taramail.store import (
    RedisStore,
    Store,
)


@define(frozen=True)
class DomainManager:

    db: DBSession
    store: Store = field(factory=RedisStore.from_env)
    dockerapi: HTTPSession = HTTPSession("http://dockerapi/")
    dkim_manager: DKIMManager = field(default=Factory(
        lambda self: DKIMManager(self.store),
        takes_self=True,
    ))

    def get_origin_domain(self, domain):
        with suppress(NoResultFound):
            domain = self.db.query(AliasDomainModel).filter_by(alias_domain=domain).one().target_domain

        return domain

    def get_domain_details(self, domain):
        domain = self.get_origin_domain(domain)
        try:
            model = self.db.query(DomainModel).filter_by(domain=domain).one()
        except NoResultFound as e:
            raise KeyError(f"Domain not found: {domain}") from e

        mailbox_data_domain = self._get_mailbox_data_domain(domain)
        sum_quota_in_use = self._get_sum_quota_in_use(domain)

        max_new_mailbox_quota = max(model.quota - mailbox_data_domain.in_use, model.maxquota)
        def_new_mailbox_quota = max(max_new_mailbox_quota, model.defquota)
        quota_used_in_domain = mailbox_data_domain.in_use
        bytes_total = sum_quota_in_use.bytes_total or 0
        msgs_total = sum_quota_in_use.msgs_total or 0

        alias_data_domain = self._get_alias_data_domain(domain)
        aliases_in_domain = alias_data_domain.alias_count or 0
        aliases_left = model.aliases - aliases_in_domain

        return DomainDetails(
            max_new_mailbox_quota=max_new_mailbox_quota,
            def_new_mailbox_quota=def_new_mailbox_quota,
            quota_used_in_domain=quota_used_in_domain,
            bytes_total=bytes_total,
            msgs_total=msgs_total,
            mboxes_in_domain=mailbox_data_domain.count,
            mboxes_left=model.mailboxes - mailbox_data_domain.count,
            domain=model.domain,
            description=model.description,
            max_num_aliases_for_domain=model.aliases,
            max_num_mboxes_for_domain=model.mailboxes,
            def_quota_for_mbox=model.defquota,
            max_quota_for_mbox=model.maxquota,
            max_quota_for_domain=model.quota,
            relayhost=model.relayhost,
            backupmx=model.backupmx,
            gal=model.gal,
            active=model.active,
            relay_all_recipients=model.relay_all_recipients,
            relay_unknown_only=model.relay_unknown_only,
            aliases_in_domain=aliases_in_domain,
            aliases_left=aliases_left,
        )

    def get_domains(self):
        return self.db.query(DomainModel).filter_by(active=True).all()

    def create_domain(self, domain_create: DomainCreate):
        domain = domain_create.domain.lower().strip()
        if self.db.query(DomainModel).filter_by(domain=domain).count():
            raise KeyError("domain exists already")

        model = DomainModel(
            domain=domain,
            description=domain_create.description or domain,
            aliases=domain_create.aliases,
            mailboxes=domain_create.mailboxes,
            defquota=domain_create.defquota,
            maxquota=domain_create.maxquota,
            quota=domain_create.quota,
            backupmx=domain_create.backupmx,
            gal=domain_create.gal,
            relay_all_recipients=domain_create.relay_all_recipients,
            relay_unknown_only=domain_create.relay_unknown_only,
            active=domain_create.active,
        ).validate()

        self.db.query(SenderAclModel).filter(
            SenderAclModel.external == 1,
            SenderAclModel.send_as.like(f"%@{model.domain}"),
        ).delete()
        self.db.add(model)

        self.store.hset("DOMAIN_MAP", model.domain, 1)

        dkim_create = DKIMCreate(
            domain=model.domain,
            dkim_selector=domain_create.dkim_selector,
            key_size=domain_create.key_size,
        )
        self.dkim_manager.create_key(dkim_create)

        if domain_create.restart_sogo:
            self.dockerapi.post("/services/sogo/restart")

        return model

    def update_domain(self, domain, domain_update: DomainUpdate):
        details = self.get_domain_details(domain)
        model = self.db.query(DomainModel).filter_by(domain=domain).one()
        model.mailboxes = details.max_num_mboxes_for_domain
        model.defquota = details.def_quota_for_mbox
        model.maxquota = details.max_quota_for_mbox
        model.quota = details.max_quota_for_domain
        for key, value in domain_update.model_dump().items():
            if value is not None:
                setattr(model, key, value)

        model.validate()

        mailbox_data = self._get_mailbox_data(domain)
        alias_data = self._get_alias_data(domain)

        if mailbox_data.biggest_mailbox > model.maxquota:
            raise ValueError("max quota already used")
        if mailbox_data.quota_all > model.quota:
            raise ValueError("domain quota already used")
        if mailbox_data.count > model.mailboxes:
            raise ValueError("mailboxes already used")
        if alias_data.count > model.aliases:
            raise ValueError("aliases already used")

        return model

    def delete_domain(self, domain):
        count = self.db.query(func.count(MailboxModel.username)).filter_by(domain=domain).scalar()
        if count:
            raise ValueError("domain not empty")

        # TODO: cleanup dovecot
        self.db.query(DomainModel).filter_by(domain=domain).delete()
        self.db.query(AliasModel).filter_by(domain=domain).delete()
        self.db.query(AliasDomainModel).filter_by(target_domain=domain).delete()
        self.db.query(MailboxModel).filter_by(domain=domain).delete()
        self.db.query(SenderAclModel).filter(SenderAclModel.logged_in_as.like(domain)).delete()
        self.db.query(Quota2Model).filter(Quota2Model.username.like(domain)).delete()
        self.db.query(Quota2ReplicaModel).filter(Quota2ReplicaModel.username.like(domain)).delete()
        self.db.query(SpamaliasModel).filter(SpamaliasModel.address.like(domain)).delete()
        self.db.query(BccMapsModel).filter_by(local_dest=domain).delete()

        self.store.hdel("DOMAIN_MAP", domain)
        self.store.hdel("RL_VALUE", domain)

    def _get_mailbox_data(self, domain):
        return (
            self.db.query(
                func.count(MailboxModel.username).label("count"),
                func.coalesce(MailboxModel.quota, 0).label("biggest_mailbox"),
                func.coalesce(func.sum(MailboxModel.quota), 0).label("quota_all"),
            )
            .filter_by(kind="")
            .filter_by(domain=domain)
            .one()
        )

    def _get_mailbox_data_domain(self, domain):
        return (
            self.db.query(
                func.count(MailboxModel.username).label("count"),
                func.coalesce(func.sum(MailboxModel.quota), 0).label("in_use"),
            )
            .filter_by(kind="")
            .filter_by(domain=domain)
            .one()
        )

    def _get_alias_data(self, domain):
        return (
            self.db.query(
                func.count(AliasModel.id).label("count"),
            )
            .filter(
                AliasModel.domain == domain,
                ~AliasModel.address.in_(select(MailboxModel.username)),
            )
            .one()
        )

    def _get_alias_data_domain(self, domain):
        return (
            self.db.query(func.count(AliasModel.address).label("alias_count"))
            .filter(
                or_(
                    AliasModel.domain == domain,
                    AliasModel.domain.in_(
                        self.db.query(AliasDomainModel.alias_domain).filter_by(target_domain=domain)
                    ),
                )
            )
            .filter(AliasModel.address.not_in(self.db.query(MailboxModel.username)))
            .one()
        )

    def _get_sum_quota_in_use(self, domain):
        return (
            self.db.query(
                func.sum(Quota2Model.bytes).label("bytes_total"),
                func.sum(Quota2Model.messages).label("msgs_total"),
            )
            .filter(Quota2Model.username.in_(select(MailboxModel.username).filter_by(domain=domain)))
            .one()
        )

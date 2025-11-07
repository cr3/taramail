"""Unit tests for the rspamd module."""

import re

from hamcrest import (
    all_of,
    assert_that,
    contains_exactly,
    contains_inanyorder,
    contains_string,
    has_properties,
)

from taramail.models import (
    AliasDomainModel,
    AliasModel,
    DomainModel,
    FilterconfModel,
    MailboxModel,
    SogoFolderInfoModel,
    SogoQuickContactModel,
)
from taramail.rspamd.settings import RspamdSettings


def test_rspamd_get_allowed_domains_regex(db_model, db_session, unique):
    """The allowed domains regex should be the union of domains and alias domains."""
    domain = db_model(DomainModel)
    alias_domain = db_model(AliasDomainModel)
    result = RspamdSettings(db_session).get_allowed_domains_regex()
    assert_that(result, all_of(
        contains_string(re.escape(alias_domain.target_domain)),
        contains_string(re.escape(alias_domain.alias_domain)),
        contains_string(re.escape(domain.domain)),
    ))


def test_rspamd_get_internal_aliases(db_model, db_session):
    """Getting internal aliases should only return active aliases."""
    alias = db_model(AliasModel, active=1, internal=1)
    db_model(AliasModel, active=0, internal=1)
    db_model(AliasModel, active=1, internal=0)
    result = RspamdSettings(db_session).get_internal_aliases()
    assert_that(result, contains_exactly(alias.address))


def test_rspamd_get_sogo_wl(db_model, db_session, unique):
    """Getting the SOGo whitelist should lookup contacts."""
    user, contact = unique("text"), unique("email")
    folder_info = db_model(SogoFolderInfoModel, c_path2=user)
    db_model(SogoQuickContactModel, c_folder_id=folder_info.c_folder_id, c_mail=contact)
    result = RspamdSettings(db_session).get_sogo_wl()
    assert result == {user: [contact]}


def test_rspamd_get_custom_scores(db_model, db_session, unique):
    """Getting custom scores should look at filterconf for high and low spam levels."""
    obj = unique("domain")
    db_model(FilterconfModel, object=obj, option="lowspamlevel", value=1)
    db_model(FilterconfModel, object=obj, option="highspamlevel", value=2)
    result = RspamdSettings(db_session).get_custom_scores()
    assert_that(result, contains_exactly(
        has_properties(
            rcpts=contains_exactly(contains_string(obj)),
            reject=2.0,
            greylist=0.0,
            add_header=1.0,
        ),
    ))


def test_rspamd_get_email_rcpts_alias_domains(db_model, db_session, unique):
    """Getting email recipients for alias domains should match alias domain and alias email."""
    local_part, alias_domain, target_domain = unique("text"), unique("domain"), unique("domain")
    alias_email = f"{local_part}@{alias_domain}"
    target_email = f"{local_part}@{target_domain}"
    db_model(AliasDomainModel, alias_domain=alias_domain, target_domain=target_domain)
    db_model(MailboxModel, local_part=local_part, domain=target_domain, username=target_email)
    result = RspamdSettings(db_session).get_email_rcpts(target_email)
    assert_that(result, contains_inanyorder(
        contains_string(alias_domain),
        alias_email,
    ))


def test_rspamd_get_email_rcpts_standard_aliases(db_model, db_session, unique):
    """Getting email recipients for standard aliases should match address and local_part."""
    goto, local_part, domain = unique("email"), unique("text"), unique("domain")
    address = f"{local_part}@{domain}"
    db_model(AliasModel, address=address, goto=goto)
    result = RspamdSettings(db_session).get_email_rcpts(goto)
    assert_that(result, contains_inanyorder(
        contains_string(local_part),
        address,
    ))


def test_rspamd_get_domain_rcpts_alias_domains(db_model, db_session):
    """Getting domain recipients for alias domains should match alias domain and target domain."""
    alias_domain = db_model(AliasDomainModel)
    result = RspamdSettings(db_session).get_domain_rcpts(alias_domain.target_domain)
    assert_that(result, contains_inanyorder(
        contains_string(alias_domain.alias_domain),
        contains_string(alias_domain.target_domain),
    ))


def test_rspamd_get_domain_rcpts_standard_aliases(db_model, db_session, unique):
    """Getting domain recipients for standard aliases should match local_part, domain and address."""
    local_part, domain = unique("text"), unique("domain")
    address = f"{local_part}@{domain}"
    db_model(AliasModel, address=address)
    result = RspamdSettings(db_session).get_domain_rcpts(domain)
    assert_that(result, contains_inanyorder(
        contains_string(local_part),
        contains_string(domain),
        address,
    ))

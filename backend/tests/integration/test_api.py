"""Integration tests for the API service."""

from hamcrest import (
    assert_that,
    contains_string,
    has_entries,
    starts_with,
)


def test_api_domains(api_session, unique):
    """The API should expose a domains API."""
    domain = unique("domain")
    api_session.post("/api/domains", json={
        "domain": domain,
        "restart_sogo": False,
    })
    api_session.put(f"/api/domains/{domain}", json={"description": "test"})
    try:
        response = api_session.get(f"/api/domains/{domain}")
    finally:
        api_session.delete(f"/api/domains/{domain}")

    assert_that(response.json(), has_entries(domain=domain, description="test"))


def test_api_mailboxes(api_session, unique):
    """The API should expose a mailboxes API."""
    local_part = unique("text")
    domain = unique("domain")
    password = unique("password")
    username = f"{local_part}@{domain}"
    api_session.post("/api/domains", json={
        "domain": domain,
        "restart_sogo": False,
    })
    api_session.post("/api/mailboxes", json={
        "local_part": local_part,
        "domain": domain,
        "password": password,
        "password2": password,
    })
    api_session.put(f"/api/mailboxes/{username}", json={"name": "test"})
    try:
        response = api_session.get(f"/api/mailboxes/{username}")
    finally:
        api_session.delete(f"/api/mailboxes/{username}")
        api_session.delete(f"/api/domains/{domain}")

    assert_that(response.json(), has_entries(username=username, name="test"))


def test_api_aliases(api_session, unique):
    """The API should expose an aliases API."""
    domain = unique("domain")
    address = unique("email", domain=domain)
    api_session.post("/api/domains", json={
        "domain": domain,
        "restart_sogo": False,
    })
    response = api_session.post("/api/aliases", json={
        "address": address,
        "goto_null": True,
    })
    api_session.put(f"/api/aliases/{address}", json={"private_comment": "test"})
    try:
        response = api_session.get(f"/api/aliases/{address}")
    finally:
        api_session.delete(f"/api/aliases/{address}")
        api_session.delete(f"/api/domains/{domain}")

    assert_that(response.json(), has_entries(address=address, private_comment="test"))


def test_api_dkim(api_session, unique):
    """The API should expose a DKIM API."""
    unique("text")
    domain = unique("domain")
    api_session.post("/api/dkim", json={
        "domain": domain,
    })
    try:
        response = api_session.get(f"/api/dkim/{domain}")
    finally:
        api_session.delete(f"/api/dkim/{domain}")

    assert_that(response.json(), has_entries(dkim_selector="dkim", dkim_txt=starts_with("v=DKIM")))


def test_rspamd_settings(api_session):
    """The API should expose rspamd settings."""
    response = api_session.get("/rspamd/settings")
    assert_that(response.text, contains_string("monit"))

"""Unit tests for the api module."""

from hamcrest import (
    assert_that,
    equal_to,
    greater_than,
    has_entries,
    has_item,
    has_key,
    has_length,
    not_,
    starts_with,
)

from taramail.models import (
    AliasModel,
    DomainModel,
    MailboxModel,
)


def test_api_domains_get(db_model, api_app):
    """Getting domains should return the list of domains."""
    domain_model = db_model(DomainModel)
    response = api_app.get("/api/domains")
    assert_that(response.json(), has_item(domain_model.domain))


def test_api_domains_post(api_app, unique):
    """Posting a domain should create the domain in the api."""
    domain = unique("domain")
    api_app.post("/api/domains", json={
        "domain": domain,
        "restart_sogo": False,
    })
    response = api_app.get(f"/api/domains/{domain}")
    assert response.status_code == 200

    response = api_app.get(f"/api/dkim/{domain}")
    assert response.status_code == 200


def test_api_domains_put(db_model, api_app, unique):
    """Putting a domain should update it from the attributes."""
    domain = unique("domain")
    domain_model = db_model(DomainModel, domain=domain, description="old")
    api_app.put(f"/api/domains/{domain_model.domain}", json={"description": "new"})
    response = api_app.get(f"/api/domains/{domain_model.domain}")
    assert_that(response.json(), has_entries(description="new"))


def test_api_domains_delete(api_app, unique):
    """Deleting a domain should delete it from the list of domains."""
    domain = unique("domain")
    api_app.post("/api/domains", json={
        "domain": domain,
        "restart_sogo": False,
    })
    api_app.delete(f"/api/domains/{domain}")
    response = api_app.get(f"/api/domains/{domain}")
    assert response.status_code == 404


def test_api_mailboxes_get(db_model, api_app):
    """Getting mailboxes should return the list of mailboxes."""
    mailbox_model = db_model(MailboxModel)
    response = api_app.get("/api/mailboxes")
    assert_that(response.json(), has_item(mailbox_model.username))


def test_api_mailboxes_post(api_app, unique):
    """Posting a mailbox should create the mailbox in the api."""
    local_part = unique("text")
    domain = unique("domain")
    password = unique("password")
    username = f"{local_part}@{domain}"
    api_app.post("/api/domains", json={
        "domain": domain,
        "restart_sogo": False,
    })
    api_app.post("/api/mailboxes", json={
        "local_part": local_part,
        "domain": domain,
        "password": password,
        "password2": password,
    })
    response = api_app.get(f"/api/mailboxes/{username}")
    assert response.status_code == 200


def test_api_aliases_get(db_model, api_app, unique):
    """Getting aliases should return the list of aliases for a domain."""
    domain = unique("domain")
    alias_model = db_model(AliasModel, domain=domain)
    response = api_app.get(f"/api/aliases?domain={domain}")
    assert_that(response.json(), has_item(alias_model.address))


def test_api_aliases_post(api_app, unique):
    """Posting an alias should create the alias in the api."""
    domain = unique("domain")
    address, goto = unique("email", domain=domain), unique("email")
    api_app.post("/api/domains", json={
        "domain": domain,
        "restart_sogo": False,
    })
    response = api_app.post("/api/aliases", json={
        "address": address,
        "goto": goto,
    })
    response = api_app.get(f"/api/aliases/{address}")
    assert response.status_code == 200


def test_api_aliases_put(api_app, unique):
    """Putting an alias should update it from the attributes."""
    domain = unique("domain")
    address, goto = unique("email", domain=domain), unique("email")
    api_app.post("/api/domains", json={
        "domain": domain,
        "restart_sogo": False,
    })
    api_app.post("/api/aliases", json={
        "address": address,
        "goto": goto,
    })
    api_app.put(f"/api/aliases/{address}", json={
        "internal": True,
        "active": False,
        "sogo_visible": False,
        "private_comment": "private",
        "public_comment": "public",
    })
    response = api_app.get(f"/api/aliases/{address}")
    assert_that(response.json(), has_entries(
        internal=True,
        active=False,
        sogo_visible=False,
        private_comment="private",
        public_comment="public",
    ))


def test_api_aliases_delete(api_app, unique):
    """Deleting an alias should delete it from the list of aliases."""
    domain = unique("domain")
    address, goto = unique("email", domain=domain), unique("email")
    api_app.post("/api/domains", json={
        "domain": domain,
        "restart_sogo": False,
    })
    api_app.post("/api/aliases", json={
        "address": address,
        "goto": goto,
    })
    api_app.delete(f"/api/aliases/{address}")
    response = api_app.get(f"/api/aliases/{address}")
    assert response.status_code == 404


def test_api_get_dkim_keys(api_app, unique):
    """Getting DKIM keys should return a dict of domains and public keys."""
    domain = unique("domain")
    api_app.post("/api/dkim", json={
        "domain": domain,
    })
    response = api_app.get("/api/dkim")
    assert_that(response.json(), has_key(domain))


def test_api_get_dkim_details(api_app, unique):
    """Getting DKIM details should return a dict with the public key."""
    domain = unique("domain")
    api_app.post("/api/dkim", json={
        "domain": domain,
    })
    response = api_app.get(f"/api/dkim/{domain}")
    assert_that(response.json(), has_entries(
        pubkey=has_length(greater_than(0)),
        privkey="",
        length="2048",
        dkim_selector="dkim",
        dkim_txt=starts_with("v=DKIM1"),
    ))


def test_api_post_dkim_key(api_app, unique):
    """Posting a DKIM key should create different public keys."""
    domain1, domain2 = unique("domain"), unique("domain")
    response1 = api_app.post("/api/dkim", json={
        "domain": domain1,
    })
    response2 = api_app.post("/api/dkim", json={
        "domain": domain2,
    })
    assert_that(response1.json()["pubkey"], not_(equal_to(response2.json()["pubkey"])))


def test_api_duplicate_dkim_key(api_app, unique):
    """Duplicating a DKIM key should update the public key."""
    domain1, domain2 = unique("domain"), unique("domain")
    response1 = api_app.post("/api/dkim", json={
        "domain": domain1,
    })
    api_app.post("/api/dkim", json={
        "domain": domain2,
    })
    response2 = api_app.post("/api/dkim/duplicate", json={
        "from_domain": domain1,
        "to_domain": domain2,
    })
    assert_that(response1.json()["pubkey"], equal_to(response2.json()["pubkey"]))


def test_api_delete_dkim_key(api_app, unique):
    """Deleting a DKIM key should delete it from the list of keys."""
    domain = unique("domain")
    api_app.post("/api/dkim", json={
        "domain": domain,
    })
    api_app.delete(f"/api/dkim/{domain}")
    response = api_app.get(f"/api/dkim/{domain}")
    assert response.status_code == 404


def test_api_get_password_policy(api_app):
    """Getting the password policy should return a dict with the policy."""
    response = api_app.get("/api/password_policy")

    assert_that(response.json(), has_entries(
        length=8,
        chars=True,
        special_chars=True,
        numbers=True,
        lowerupper=True,
    ))


def test_api_put_password_policy(api_app):
    """Updating the password policy should return a dict with the updated policy."""
    api_app.get("/api/password_policy")
    response = api_app.put("/api/password_policy", json={"length": 1})

    assert_that(response.json(), has_entries(length=1))


def test_api_delete_password_policy(api_app):
    """Deleting the password policy should return a dict with the original policy."""
    api_app.put("/api/password_policy", json={"length": 1})
    api_app.delete("/api/password_policy")
    response = api_app.get("/api/password_policy")

    assert_that(response.json(), has_entries(length=8))


def test_sogo_auth_empty(api_app, unique):
    """Getting sogo auth with empty credentials should return X-headers."""
    response = api_app.get("/sogo-auth")
    assert_that(response.headers, has_entries({
        "X-User": "",
        "X-Auth": "",
        "X-Auth-Type": "",
    }))


def test_sogo_auth_valid(api_app, unique):
    """Getting sogo auth with valid credentials should return basic X-headers."""
    local_part = unique("text")
    domain = unique("domain")
    password = unique("password")
    username = f"{local_part}@{domain}"
    api_app.post("/api/domains", json={
        "domain": domain,
        "restart_sogo": False,
    })
    api_app.post("/api/mailboxes", json={
        "local_part": local_part,
        "domain": domain,
        "password": password,
        "password2": password,
    })
    response = api_app.get("/sogo-auth", auth=(username, password))
    assert_that(response.headers, has_entries({
        "X-User": username,
        "X-Auth": starts_with("Basic "),
        "X-Auth-Type": "Basic",
    }))


def test_sogo_auth_invalid(api_app, unique):
    """Getting sogo auth with invalid credentials should return 401."""
    username, password = unique("email"), unique("password")
    response = api_app.get("/sogo-auth", auth=(username, password))
    assert response.status_code == 401

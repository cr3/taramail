"""Integration tests for the backend service."""

import requests
from hamcrest import (
    assert_that,
    has_entries,
)


def test_backend_domains(backend_client, unique):
    """The backend should expose a domains API."""
    domain = unique("domain")
    requests.post(f"http://{backend_client.ip}/domains", json={"domain": domain}, timeout=10).raise_for_status()
    requests.put(
        f"http://{backend_client.ip}/domains/{domain}", json={"description": "test"}, timeout=10
    ).raise_for_status()
    response = requests.get(f"http://{backend_client.ip}/domains/{domain}", timeout=10)
    assert_that(response.json(), has_entries(domain=domain, description="test"))
    requests.delete(f"http://{backend_client.ip}/domains/{domain}", timeout=10).raise_for_status()

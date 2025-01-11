"""Integration tests for the unbound service."""


def test_unbound_resolve(unbound_client):
    """The unbound clien should resolve domain names."""
    answer = unbound_client.resolve("github.com")
    assert str(answer.canonical_name()) == "github.com."

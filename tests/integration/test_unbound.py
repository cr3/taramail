"""Integration tests for the unbound service."""


def test_unbound_resolve(unbound):
    """The unbound server should resolve domain names."""
    answer = unbound.resolve("github.com")
    assert str(answer.canonical_name()) == "github.com."

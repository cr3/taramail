"""Unit tests for the spf module."""

import pytest

from taramail.spf import (
    FakeResolver,
    SPFResolver,
)


@pytest.fixture
def resolver():
    return FakeResolver()


@pytest.fixture
def spf(resolver):
    return SPFResolver(resolver)


class TestGetAHosts:

    def test_returns_ipv4(self, resolver, spf):
        """Resolving A records should return IPv4 addresses."""
        resolver.a_records["example.com"] = ["1.2.3.4"]
        result = spf.get_a_hosts("example.com")
        assert result == ["1.2.3.4"]

    def test_returns_ipv6(self, resolver, spf):
        """Resolving AAAA records should return IPv6 addresses."""
        resolver.a_records["example.com"] = ["2001:db8::1"]
        result = spf.get_a_hosts("example.com")
        assert result == ["2001:db8::1"]

    def test_returns_both(self, resolver, spf):
        """Resolving should return both IPv4 and IPv6 addresses."""
        resolver.a_records["example.com"] = ["1.2.3.4", "2001:db8::1"]
        result = spf.get_a_hosts("example.com")
        assert result == ["1.2.3.4", "2001:db8::1"]

    def test_returns_empty_for_unknown(self, spf):
        """Unknown domains should return an empty list."""
        result = spf.get_a_hosts("nonexistent.example.com")
        assert result == []


class TestGetMxHosts:

    def test_returns_resolved_mx(self, resolver, spf):
        """MX records should be resolved to their A/AAAA addresses."""
        resolver.mx_records["example.com"] = ["mail.example.com"]
        resolver.a_records["mail.example.com"] = ["10.0.0.1"]
        result = spf.get_mx_hosts("example.com")
        assert result == ["10.0.0.1"]

    def test_returns_empty_for_unknown(self, spf):
        """Unknown domains should return an empty list."""
        result = spf.get_mx_hosts("nonexistent.example.com")
        assert result == []

    def test_resolves_multiple_mx(self, resolver, spf):
        """Multiple MX records should all be resolved."""
        resolver.mx_records["example.com"] = ["mx1.example.com", "mx2.example.com"]
        resolver.a_records["mx1.example.com"] = ["10.0.0.1"]
        resolver.a_records["mx2.example.com"] = ["10.0.0.2"]
        result = spf.get_mx_hosts("example.com")
        assert result == ["10.0.0.1", "10.0.0.2"]


class TestGetSpfAllowedHosts:

    def test_ip4_mechanism(self, resolver, spf):
        """SPF ip4 mechanism should return the IP address."""
        resolver.txt_records["example.com"] = ["v=spf1 ip4:1.2.3.4 -all"]
        result = spf.get_spf_allowed_hosts("example.com")
        assert result == ["1.2.3.4"]

    def test_ip6_mechanism(self, resolver, spf):
        """SPF ip6 mechanism should return the IPv6 address."""
        resolver.txt_records["example.com"] = ["v=spf1 ip6:2001:db8::1 -all"]
        result = spf.get_spf_allowed_hosts("example.com")
        assert result == ["2001:db8::1"]

    def test_ip4_with_cidr(self, resolver, spf):
        """SPF ip4 with CIDR should include the network notation."""
        resolver.txt_records["example.com"] = ["v=spf1 ip4:10.0.0.0/24 -all"]
        result = spf.get_spf_allowed_hosts("example.com")
        assert result == ["10.0.0.0/24"]

    def test_a_mechanism(self, resolver, spf):
        """SPF a mechanism should resolve A/AAAA records."""
        resolver.txt_records["example.com"] = ["v=spf1 a -all"]
        resolver.a_records["example.com"] = ["5.6.7.8"]
        result = spf.get_spf_allowed_hosts("example.com")
        assert result == ["5.6.7.8"]

    def test_a_mechanism_with_domain(self, resolver, spf):
        """SPF a mechanism with explicit domain should resolve that domain."""
        resolver.txt_records["example.com"] = ["v=spf1 a:other.com -all"]
        resolver.a_records["other.com"] = ["9.8.7.6"]
        result = spf.get_spf_allowed_hosts("example.com")
        assert result == ["9.8.7.6"]

    def test_mx_mechanism(self, resolver, spf):
        """SPF mx mechanism should resolve MX records."""
        resolver.txt_records["example.com"] = ["v=spf1 mx -all"]
        resolver.mx_records["example.com"] = ["mail.example.com"]
        resolver.a_records["mail.example.com"] = ["10.0.0.1"]
        result = spf.get_spf_allowed_hosts("example.com")
        assert result == ["10.0.0.1"]

    def test_include_mechanism(self, resolver, spf):
        """SPF include mechanism should recursively resolve the included domain."""
        resolver.txt_records["example.com"] = ["v=spf1 include:other.com -all"]
        resolver.txt_records["other.com"] = ["v=spf1 ip4:1.1.1.1 -all"]
        result = spf.get_spf_allowed_hosts("example.com")
        assert result == ["1.1.1.1"]

    def test_redirect_modifier(self, resolver, spf):
        """SPF redirect modifier should follow the redirect."""
        resolver.txt_records["example.com"] = ["v=spf1 redirect=other.com"]
        resolver.txt_records["other.com"] = ["v=spf1 ip4:1.1.1.1 -all"]
        result = spf.get_spf_allowed_hosts("example.com")
        assert result == ["1.1.1.1"]

    def test_stops_on_fail_qualifier(self, resolver, spf):
        """SPF should stop processing on -all (fail qualifier)."""
        resolver.txt_records["example.com"] = ["v=spf1 ip4:1.2.3.4 -all ip4:5.6.7.8"]
        result = spf.get_spf_allowed_hosts("example.com")
        assert result == ["1.2.3.4"]

    def test_stops_on_softfail_qualifier(self, resolver, spf):
        """SPF should stop processing on ~all (softfail qualifier)."""
        resolver.txt_records["example.com"] = ["v=spf1 ip4:1.2.3.4 ~all ip4:5.6.7.8"]
        result = spf.get_spf_allowed_hosts("example.com")
        assert result == ["1.2.3.4"]

    def test_handles_plus_qualifier(self, resolver, spf):
        """SPF should handle explicit pass (+) qualifier."""
        resolver.txt_records["example.com"] = ["v=spf1 +ip4:1.2.3.4 -all"]
        result = spf.get_spf_allowed_hosts("example.com")
        assert result == ["1.2.3.4"]

    def test_handles_neutral_qualifier(self, resolver, spf):
        """SPF should handle neutral (?) qualifier."""
        resolver.txt_records["example.com"] = ["v=spf1 ?ip4:1.2.3.4 -all"]
        result = spf.get_spf_allowed_hosts("example.com")
        assert result == ["1.2.3.4"]

    def test_deduplicates_hosts(self, resolver, spf):
        """SPF should deduplicate repeated hosts."""
        resolver.txt_records["example.com"] = ["v=spf1 ip4:1.2.3.4 ip4:1.2.3.4 -all"]
        result = spf.get_spf_allowed_hosts("example.com")
        assert result == ["1.2.3.4"]

    def test_returns_empty_for_no_spf(self, spf):
        """Domains without SPF records should return an empty list."""
        result = spf.get_spf_allowed_hosts("example.com")
        assert result == []

    def test_ignores_non_spf_txt(self, resolver, spf):
        """Non-SPF TXT records should be ignored."""
        resolver.txt_records["example.com"] = ["google-site-verification=abc123"]
        result = spf.get_spf_allowed_hosts("example.com")
        assert result == []


class TestGetOutgoingHostsBestGuess:

    def test_prefers_spf(self, resolver, spf):
        """Should prefer SPF records over MX and A."""
        resolver.txt_records["example.com"] = ["v=spf1 ip4:1.2.3.4 -all"]
        resolver.mx_records["example.com"] = ["mail.example.com"]
        resolver.a_records["mail.example.com"] = ["5.6.7.8"]
        result = spf.get_outgoing_hosts_best_guess("example.com")
        assert result == ["1.2.3.4"]

    def test_falls_back_to_mx(self, resolver, spf):
        """Should fall back to MX records when SPF is empty."""
        resolver.mx_records["example.com"] = ["mail.example.com"]
        resolver.a_records["mail.example.com"] = ["5.6.7.8"]
        result = spf.get_outgoing_hosts_best_guess("example.com")
        assert result == ["5.6.7.8"]

    def test_falls_back_to_a(self, resolver, spf):
        """Should fall back to A records when both SPF and MX are empty."""
        resolver.a_records["example.com"] = ["9.8.7.6"]
        result = spf.get_outgoing_hosts_best_guess("example.com")
        assert result == ["9.8.7.6"]

    def test_returns_empty_when_nothing_resolves(self, spf):
        """Should return empty when no records can be resolved."""
        result = spf.get_outgoing_hosts_best_guess("example.com")
        assert result == []

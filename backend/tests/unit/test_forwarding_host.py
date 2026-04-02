"""Unit tests for the forwarding_host module."""

import pytest

from taramail.forwarding_host import (
    ForwardingHostCreate,
    ForwardingHostNotFoundError,
    ForwardingHostUpdate,
    ForwardingHostValidationError,
)


def test_get_forwarding_hosts_empty(forwarding_host_manager):
    """Getting forwarding hosts when none exist should return an empty list."""
    result = forwarding_host_manager.get_forwarding_hosts()
    assert result == []


def test_add_forwarding_host_ipv4(forwarding_host_manager):
    """Adding an IPv4 forwarding host should store it directly."""
    create = ForwardingHostCreate(hostname="10.0.0.1")
    result = forwarding_host_manager.add_forwarding_host(create)
    assert result == ["10.0.0.1"]


def test_add_forwarding_host_ipv4_cidr(forwarding_host_manager):
    """Adding an IPv4 CIDR forwarding host should store it directly."""
    create = ForwardingHostCreate(hostname="192.168.1.0/24")
    result = forwarding_host_manager.add_forwarding_host(create)
    assert result == ["192.168.1.0/24"]


def test_add_forwarding_host_ipv6(forwarding_host_manager):
    """Adding an IPv6 forwarding host should store it directly."""
    create = ForwardingHostCreate(hostname="2001:db8::1")
    result = forwarding_host_manager.add_forwarding_host(create)
    assert result == ["2001:db8::1"]


def test_add_forwarding_host_ipv6_cidr(forwarding_host_manager):
    """Adding an IPv6 CIDR forwarding host should store it directly."""
    create = ForwardingHostCreate(hostname="2001:db8::/32")
    result = forwarding_host_manager.add_forwarding_host(create)
    assert result == ["2001:db8::/32"]


def test_add_forwarding_host_hostname(forwarding_host_manager, fake_resolver):
    """Adding a hostname should resolve it via SPF/MX/A."""
    fake_resolver.a_records["mail.example.com"] = ["1.2.3.4", "5.6.7.8"]
    create = ForwardingHostCreate(hostname="mail.example.com")
    result = forwarding_host_manager.add_forwarding_host(create)
    assert result == ["1.2.3.4", "5.6.7.8"]


def test_add_forwarding_host_hostname_via_spf(forwarding_host_manager, fake_resolver):
    """Adding a hostname with SPF records should use SPF resolution."""
    fake_resolver.txt_records["example.com"] = ["v=spf1 ip4:9.9.9.9 -all"]
    create = ForwardingHostCreate(hostname="example.com")
    result = forwarding_host_manager.add_forwarding_host(create)
    assert result == ["9.9.9.9"]


def test_add_forwarding_host_hostname_unresolvable(forwarding_host_manager):
    """Adding an unresolvable hostname should raise a validation error."""
    create = ForwardingHostCreate(hostname="nonexistent.example.com")
    with pytest.raises(ForwardingHostValidationError):
        forwarding_host_manager.add_forwarding_host(create)


def test_add_forwarding_host_stores_source(forwarding_host_manager, fake_resolver):
    """Adding a forwarding host should store the original hostname as source."""
    fake_resolver.a_records["mail.example.com"] = ["1.2.3.4"]
    create = ForwardingHostCreate(hostname="mail.example.com")
    forwarding_host_manager.add_forwarding_host(create)

    details = forwarding_host_manager.get_forwarding_host_details("1.2.3.4")
    assert details.source == "mail.example.com"


def test_add_forwarding_host_filter_spam(forwarding_host_manager):
    """Adding with filter_spam=True should not set KEEP_SPAM."""
    create = ForwardingHostCreate(hostname="10.0.0.1", filter_spam=True)
    forwarding_host_manager.add_forwarding_host(create)

    details = forwarding_host_manager.get_forwarding_host_details("10.0.0.1")
    assert details.keep_spam == "no"


def test_add_forwarding_host_keep_spam(forwarding_host_manager):
    """Adding with filter_spam=False should set KEEP_SPAM."""
    create = ForwardingHostCreate(hostname="10.0.0.1", filter_spam=False)
    forwarding_host_manager.add_forwarding_host(create)

    details = forwarding_host_manager.get_forwarding_host_details("10.0.0.1")
    assert details.keep_spam == "yes"


def test_get_forwarding_hosts(forwarding_host_manager):
    """Getting forwarding hosts should return all added hosts."""
    create1 = ForwardingHostCreate(hostname="10.0.0.1")
    create2 = ForwardingHostCreate(hostname="10.0.0.2")
    forwarding_host_manager.add_forwarding_host(create1)
    forwarding_host_manager.add_forwarding_host(create2)

    result = forwarding_host_manager.get_forwarding_hosts()
    hosts = {r.host for r in result}
    assert hosts == {"10.0.0.1", "10.0.0.2"}


def test_get_forwarding_host_details(forwarding_host_manager):
    """Getting host details should return host, source, and keep_spam."""
    create = ForwardingHostCreate(hostname="10.0.0.1", filter_spam=False)
    forwarding_host_manager.add_forwarding_host(create)

    result = forwarding_host_manager.get_forwarding_host_details("10.0.0.1")
    assert result.host == "10.0.0.1"
    assert result.source == "10.0.0.1"
    assert result.keep_spam == "yes"


def test_get_forwarding_host_details_not_found(forwarding_host_manager):
    """Getting details for a nonexistent host should raise."""
    with pytest.raises(ForwardingHostNotFoundError):
        forwarding_host_manager.get_forwarding_host_details("10.0.0.99")


def test_update_forwarding_host_enable_keep_spam(forwarding_host_manager):
    """Updating keep_spam to True should set KEEP_SPAM."""
    create = ForwardingHostCreate(hostname="10.0.0.1", filter_spam=True)
    forwarding_host_manager.add_forwarding_host(create)

    update = ForwardingHostUpdate(keep_spam=True)
    forwarding_host_manager.update_forwarding_host("10.0.0.1", update)

    details = forwarding_host_manager.get_forwarding_host_details("10.0.0.1")
    assert details.keep_spam == "yes"


def test_update_forwarding_host_disable_keep_spam(forwarding_host_manager):
    """Updating keep_spam to False should remove KEEP_SPAM."""
    create = ForwardingHostCreate(hostname="10.0.0.1", filter_spam=False)
    forwarding_host_manager.add_forwarding_host(create)

    update = ForwardingHostUpdate(keep_spam=False)
    forwarding_host_manager.update_forwarding_host("10.0.0.1", update)

    details = forwarding_host_manager.get_forwarding_host_details("10.0.0.1")
    assert details.keep_spam == "no"


def test_update_forwarding_host_not_found(forwarding_host_manager):
    """Updating a nonexistent host should raise."""
    update = ForwardingHostUpdate(keep_spam=True)
    with pytest.raises(ForwardingHostNotFoundError):
        forwarding_host_manager.update_forwarding_host("10.0.0.99", update)


def test_delete_forwarding_host(forwarding_host_manager):
    """Deleting a forwarding host should remove it from both hashes."""
    create = ForwardingHostCreate(hostname="10.0.0.1", filter_spam=False)
    forwarding_host_manager.add_forwarding_host(create)

    forwarding_host_manager.delete_forwarding_host("10.0.0.1")

    with pytest.raises(ForwardingHostNotFoundError):
        forwarding_host_manager.get_forwarding_host_details("10.0.0.1")


def test_delete_forwarding_host_cleans_keep_spam(forwarding_host_manager):
    """Deleting should also clean up the KEEP_SPAM entry."""
    create = ForwardingHostCreate(hostname="10.0.0.1", filter_spam=False)
    forwarding_host_manager.add_forwarding_host(create)

    forwarding_host_manager.delete_forwarding_host("10.0.0.1")

    # Re-add without keep_spam and verify it's clean
    create2 = ForwardingHostCreate(hostname="10.0.0.1", filter_spam=True)
    forwarding_host_manager.add_forwarding_host(create2)
    details = forwarding_host_manager.get_forwarding_host_details("10.0.0.1")
    assert details.keep_spam == "no"

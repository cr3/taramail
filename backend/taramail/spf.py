"""SPF record resolution for determining outgoing mail hosts."""

import ipaddress
import logging
import socket
from abc import ABC, abstractmethod
from contextlib import suppress

from attrs import define

logger = logging.getLogger(__name__)


class Resolver(ABC):
    """Abstract DNS resolver interface."""

    @abstractmethod
    def resolve_a(self, domain: str) -> list[str]:
        """Resolve A and AAAA records, returning IP addresses."""

    @abstractmethod
    def resolve_mx(self, domain: str) -> list[str]:
        """Resolve MX records, returning mail server hostnames."""

    @abstractmethod
    def resolve_txt(self, domain: str) -> list[str]:
        """Resolve TXT records, returning record strings."""


class DNSResolver(Resolver):
    """Real DNS resolver using socket and dnspython."""

    def resolve_a(self, domain: str) -> list[str]:
        hosts = []
        for family in (socket.AF_INET, socket.AF_INET6):
            with suppress(socket.gaierror):
                results = socket.getaddrinfo(domain, None, family, socket.SOCK_STREAM)
                hosts.extend(addr[4][0] for addr in results)
        return list(dict.fromkeys(hosts))

    def resolve_mx(self, domain: str) -> list[str]:
        try:
            import dns.resolver
            answers = dns.resolver.resolve(domain, "MX")
            return [str(rdata.exchange).rstrip(".") for rdata in answers]
        except Exception:
            logger.debug("Failed to resolve MX records for %s", domain)
            return []

    def resolve_txt(self, domain: str) -> list[str]:
        try:
            import dns.resolver
            answers = dns.resolver.resolve(domain, "TXT")
            return [str(rdata).strip('"') for rdata in answers]
        except Exception:
            return []


def _parse_mechanism(mech: str, domain: str, spf: "SPFResolver") -> list[str]:
    """Parse a single SPF mechanism and return resolved hosts."""
    cidr = None
    target_domain = domain

    if ":" in mech:
        split = mech.split(":", 1)
        mech = split[0]
        target_domain = split[1]
        if "/" in target_domain:
            target_domain, cidr = target_domain.rsplit("/", 1)

    new_hosts: list[str] = []
    if mech == "include" and target_domain != domain:
        new_hosts = spf.get_spf_allowed_hosts(target_domain)
    elif mech == "a":
        new_hosts = spf.resolver.resolve_a(target_domain)
    elif mech == "mx":
        new_hosts = spf.get_mx_hosts(target_domain)
    elif mech in ("ip4", "ip6"):
        new_hosts = [target_domain]

    if cidr:
        new_hosts = [f"{h}/{cidr}" for h in new_hosts]

    return new_hosts


def _deduplicate_hosts(hosts: list[str], expand_ipv6: bool) -> list[str]:
    """Deduplicate hosts and optionally expand IPv6 addresses."""
    result: list[str] = []
    seen: set[str] = set()
    for host in hosts:
        if host in seen:
            continue
        seen.add(host)

        if expand_ipv6 and "/" not in host:
            with suppress(ValueError):
                addr = ipaddress.IPv6Address(host)
                host = addr.exploded
        result.append(host)

    return result


@define(frozen=True)
class SPFResolver:
    """SPF record resolver with DNS dependency injection."""

    resolver: Resolver

    def get_a_hosts(self, domain: str) -> list[str]:
        """Resolve A and AAAA records for a domain."""
        return self.resolver.resolve_a(domain)

    def get_mx_hosts(self, domain: str) -> list[str]:
        """Resolve MX records to their A/AAAA addresses."""
        hosts = []
        for mx_host in self.resolver.resolve_mx(domain):
            hosts.extend(self.resolver.resolve_a(mx_host))
        return list(dict.fromkeys(hosts))

    def get_spf_allowed_hosts(self, domain: str, expand_ipv6: bool = False) -> list[str]:
        """Parse SPF records and return allowed hosts.

        Handles include, a, mx, ip4, ip6 mechanisms and redirect modifier.
        Only processes pass (+) and neutral (?) qualifiers.
        """
        hosts: list[str] = []

        for txt in self.resolver.resolve_txt(domain):
            parts = txt.split()
            if not parts or parts[0] != "v=spf1":
                continue

            for mech in parts[1:]:
                qual = mech[0]
                if qual in ("-", "~"):
                    break

                if qual in ("+", "?"):
                    mech = mech[1:]

                if "=" in mech:
                    key, value = mech.split("=", 1)
                    if key == "redirect":
                        return self.get_spf_allowed_hosts(value, expand_ipv6=True)
                else:
                    hosts.extend(_parse_mechanism(mech, domain, self))

        return _deduplicate_hosts(hosts, expand_ipv6)

    def get_outgoing_hosts_best_guess(self, domain: str) -> list[str]:
        """Determine outgoing mail hosts for a domain.

        Tries SPF records first, then MX records, then A/AAAA records.
        """
        if hosts := self.get_spf_allowed_hosts(domain):
            return hosts

        if hosts := self.get_mx_hosts(domain):
            return hosts

        return self.get_a_hosts(domain)


class FakeResolver(Resolver):
    """In-memory DNS resolver for testing."""

    def __init__(self):
        self.a_records: dict[str, list[str]] = {}
        self.mx_records: dict[str, list[str]] = {}
        self.txt_records: dict[str, list[str]] = {}

    def resolve_a(self, domain: str) -> list[str]:
        return list(self.a_records.get(domain, []))

    def resolve_mx(self, domain: str) -> list[str]:
        return list(self.mx_records.get(domain, []))

    def resolve_txt(self, domain: str) -> list[str]:
        return list(self.txt_records.get(domain, []))


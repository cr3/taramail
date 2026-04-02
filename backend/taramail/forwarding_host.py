import ipaddress
import logging
import re
from typing import Literal

from attrs import define
from pydantic import BaseModel, Field

from taramail.spf import SPFResolver
from taramail.store import Store

logger = logging.getLogger(__name__)


class ForwardingHostError(Exception):
    """Base exception for forwarding host errors."""


class ForwardingHostNotFoundError(ForwardingHostError):
    """Raised when a forwarding host is not found."""


class ForwardingHostValidationError(ForwardingHostError):
    """Raised when a forwarding host is invalid."""


class ForwardingHostCreate(BaseModel):
    hostname: str = Field(..., min_length=1)
    filter_spam: bool = True


class ForwardingHostDetails(BaseModel):
    host: str
    source: str
    keep_spam: Literal["yes", "no"]


class ForwardingHostUpdate(BaseModel):
    keep_spam: bool


@define(frozen=True)
class ForwardingHostManager:

    store: Store
    spf: SPFResolver

    def get_forwarding_hosts(self) -> list[ForwardingHostDetails]:
        """Get all forwarding hosts from Redis."""
        fwd_hosts = self.store.hgetall("WHITELISTED_FWD_HOST")
        if not fwd_hosts:
            return []

        result = []
        for host, source in fwd_hosts.items():
            keep_spam = "yes" if self.store.hget("KEEP_SPAM", host) else "no"
            result.append(ForwardingHostDetails(
                host=host,
                source=source,
                keep_spam=keep_spam,
            ))

        return result

    def get_forwarding_host_details(self, host: str) -> ForwardingHostDetails:
        """Get details for a specific forwarding host."""
        source = self.store.hget("WHITELISTED_FWD_HOST", host)
        if not source:
            raise ForwardingHostNotFoundError(f"Forwarding host {host} not found")

        keep_spam = "yes" if self.store.hget("KEEP_SPAM", host) else "no"
        return ForwardingHostDetails(
            host=host,
            source=source,
            keep_spam=keep_spam,
        )

    def add_forwarding_host(self, forwarding_host_create: ForwardingHostCreate) -> list[str]:
        """Add a forwarding host to the whitelist."""
        host = forwarding_host_create.hostname.strip()
        source = forwarding_host_create.hostname

        # Determine if this is an IP address or hostname
        hosts = self._resolve_host(host)

        if not hosts:
            raise ForwardingHostValidationError(f"Invalid host: {host}")

        # Add each resolved host to Redis
        for resolved_host in hosts:
            self.store.hset("WHITELISTED_FWD_HOST", resolved_host, source)

            # Handle spam filtering setting
            if not forwarding_host_create.filter_spam:
                # Keep spam (don't filter)
                self.store.hset("KEEP_SPAM", resolved_host, "1")
            else:
                # Filter spam (remove from KEEP_SPAM if present)
                self.store.hdel("KEEP_SPAM", resolved_host)

        logger.info("Added forwarding host(s): %s", ", ".join(hosts))
        return hosts

    def update_forwarding_host(self, host: str, forwarding_host_update: ForwardingHostUpdate) -> None:
        """Update a forwarding host's settings."""
        # Verify the host exists
        if not self.store.hget("WHITELISTED_FWD_HOST", host):
            raise ForwardingHostNotFoundError(f"Forwarding host {host} not found")

        # Update spam filtering setting
        if forwarding_host_update.keep_spam:
            self.store.hset("KEEP_SPAM", host, "1")
        else:
            self.store.hdel("KEEP_SPAM", host)

        logger.info("Updated forwarding host: %s", host)

    def delete_forwarding_host(self, host: str) -> None:
        """Delete a forwarding host from the whitelist.

        Args:
            host: The host identifier to delete
        """
        self.store.hdel("WHITELISTED_FWD_HOST", host)
        self.store.hdel("KEEP_SPAM", host)
        logger.info("Deleted forwarding host: %s", host)

    def _resolve_host(self, host: str) -> list[str]:
        """Resolve a host to a list of IP addresses or return as-is if already an IP."""
        # Check if it's an IPv6 address or network
        if re.match(r'^[0-9a-fA-F:\/]+$', host):
            try:
                if '/' in host:
                    ipaddress.IPv6Network(host, strict=False)
                else:
                    ipaddress.IPv6Address(host)
            except ValueError:
                pass
            else:
                return [host]

        # Check if it's an IPv4 address or network
        if re.match(r'^[0-9\.\/]+$', host):
            try:
                if '/' in host:
                    ipaddress.IPv4Network(host, strict=False)
                else:
                    ipaddress.IPv4Address(host)
            except ValueError:
                pass
            else:
                return [host]

        # Hostname: resolve via SPF, MX, or A records
        return self.spf.get_outgoing_hosts_best_guess(host)

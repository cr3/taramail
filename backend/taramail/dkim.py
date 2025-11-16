import base64
from typing import Annotated

from attrs import define
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import (
    BaseModel,
    Field,
)

from taramail.schemas import DomainStr
from taramail.store import Store
from taramail.units import kebi


class DKIMError(Exception):
    """Base exception for DKIM errors."""


class DKIMAlreadyExistsError(DKIMError):
    """Raised when a DKIM domain already exists."""


class DKIMNotFoundError(DKIMError):
    """Raised when a DKIM domain is not found."""


class DKIMCreate(BaseModel):

    domain: DomainStr
    dkim_selector: Annotated[str, Field("dkim", pattern=r"^[a-zA-Z0-9\-_\.]+$")]
    key_size: int = 2 * kebi


class DKIMDuplicate(BaseModel):

    from_domain: DomainStr
    to_domain: DomainStr


class DKIMDetails(BaseModel):

    pubkey: str
    privkey: str
    length: str
    dkim_selector: str
    dkim_txt: str


@define
class DKIMManager:
    """DKIM Manager for handling DKIM keys and operations."""

    store: Store

    def get_keys(self) -> dict[str, str]:
        """Get all DKIM public keys."""
        return self.store.hgetall("DKIM_PUB_KEYS")

    def get_details(self, domain: DomainStr, privkey=False) -> DKIMDetails:
        """Get DKIM details for a domain."""
        pubkey = self.store.hget("DKIM_PUB_KEYS", domain)
        if not pubkey:
            raise DKIMNotFoundError(f"DKIM key not found: {domain}")

        length = self._detect_key_length(pubkey)
        dkim_selector = self.store.hget("DKIM_SELECTORS", domain) or "dkim"
        dkim_txt = f'v=DKIM1;k=rsa;t=s;s=email;p={pubkey}'

        # Include private key if requested
        if privkey:
            privkey_data = self.store.hget("DKIM_PRIV_KEYS", f"{dkim_selector}.{domain}")
            privkey = base64.b64encode(privkey_data.encode()).decode() if privkey_data else ""
        else:
            privkey = ""

        return DKIMDetails(
            pubkey=pubkey,
            privkey=privkey,
            length=length,
            dkim_selector=dkim_selector,
            dkim_txt=dkim_txt,
        )

    def create_key(self, dkim_create: DKIMCreate) -> str:
        if self.store.hget("DKIM_PUB_KEYS", dkim_create.domain):
            raise DKIMAlreadyExistsError(f"DKIM domain already exists: {dkim_create.domain}")

        key_size = dkim_create.key_size
        key_pair = self._generate_dkim_keypair(key_size)
        public_lines = key_pair["public"].splitlines()
        public_key = ''.join(public_lines[1:-1])  # remove header/footer

        self.store.hset("DKIM_PUB_KEYS", dkim_create.domain, public_key)
        self.store.hset("DKIM_SELECTORS", dkim_create.domain, dkim_create.dkim_selector)
        self.store.hset(
            "DKIM_PRIV_KEYS",
            f"{dkim_create.dkim_selector}.{dkim_create.domain}",
            key_pair["private"],
        )

        return public_key

    def duplicate_key(self, dkim_duplicate: DKIMDuplicate) -> None:
        """Duplicate DKIM key from one domain to another."""
        # Get source domain DKIM details
        from_domain_dkim = self.get_details(dkim_duplicate.from_domain, privkey=True)

        try:
            privkey_bytes = base64.b64decode(from_domain_dkim.privkey)
        except (base64.binascii.Error, ValueError) as e:
            raise DKIMError(f"Invalid DKIM private key format: {e}") from e

        # Copy DKIM data
        self.store.hset("DKIM_PUB_KEYS", dkim_duplicate.to_domain, from_domain_dkim.pubkey)
        self.store.hset("DKIM_SELECTORS", dkim_duplicate.to_domain, from_domain_dkim.dkim_selector)
        self.store.hset(
            "DKIM_PRIV_KEYS",
            f"{from_domain_dkim.dkim_selector}.{dkim_duplicate.to_domain}",
            privkey_bytes.decode(),
        )

    def delete_key(self, domain: DomainStr) -> None:
        """Delete DKIM keys for a domain."""
        # Get selector before deleting
        selector = self.store.hget("DKIM_SELECTORS", domain)

        # Delete all DKIM data for domain
        self.store.hdel("DKIM_PUB_KEYS", domain)
        self.store.hdel("DKIM_SELECTORS", domain)
        if selector:
            self.store.hdel("DKIM_PRIV_KEYS", f"{selector}.{domain}")

    def _detect_key_length(self, pubkey: str) -> str:
        """Detect key length from base64-encoded public key size."""
        try:
            key = serialization.load_pem_public_key(
                pubkey.encode(),
                backend=default_backend()
            )
            return str(key.key_size)
        except Exception:
            # Fallback to length estimation
            for threshold, size in [
                (391, "1024"),
                (564, "2048"),
                (736, "3072"),
                (1416, "4096"),
            ]:
                if len(pubkey) < threshold:
                    return size

            return ">= 8192"

    def _generate_dkim_keypair(self, key_size: int) -> dict:
        """Generate a DKIM key pair with the specified key size."""
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return {
            "private": private_pem.decode(),
            "public": public_pem.decode()
        }

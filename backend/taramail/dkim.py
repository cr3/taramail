import base64
import re

from attrs import define
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import BaseModel

from taramail.store import Store
from taramail.units import kebi


class DKIMCreate(BaseModel):

    domain: str
    dkim_selector: str = "dkim"
    key_size: int = 2 * kebi


class DKIMDuplicate(BaseModel):

    from_domain: str
    to_domain: str


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

    def get_details(self, domain: str, privkey=False) -> DKIMDetails:
        """Get DKIM details for a domain."""
        if not self._is_valid_domain_name(domain):
            raise ValueError("DKIM domain invalid")

        pubkey = self.store.hget("DKIM_PUB_KEYS", domain)
        if not pubkey:
            raise KeyError("DKIM domain not found")

        dkim_selector = self.store.hget("DKIM_SELECTORS", domain) or "dkim"

        # Determine key length based on public key size
        if len(pubkey) < 391:
            length = "1024"
        elif len(pubkey) < 564:
            length = "2048"
        elif len(pubkey) < 736:
            length = "3072"
        elif len(pubkey) < 1416:
            length = "4096"
        else:
            length = ">= 8192"

        # Generate DKIM TXT record
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
        dkim_selector = dkim_create.dkim_selector
        if not self._is_valid_selector(dkim_selector):
            raise ValueError("DKIM selector invalid")

        domain = dkim_create.domain
        if not self._is_valid_domain_name(domain):
            raise ValueError("DKIM domain invalid")

        if self.store.hget("DKIM_PUB_KEYS", domain):
            raise ValueError("DKIM domain already exists")

        key_size = dkim_create.key_size
        key_pair = self._generate_dkim_keypair(key_size)
        public_lines = key_pair["public"].splitlines()
        public_key = ''.join(public_lines[1:-1])  # remove header/footer

        self.store.hset("DKIM_PUB_KEYS", domain, public_key)
        self.store.hset("DKIM_SELECTORS", domain, dkim_selector)
        self.store.hset(
            "DKIM_PRIV_KEYS",
            f"{dkim_selector}.{domain}",
            key_pair["private"],
        )

        return public_key

    def duplicate_key(self, dkim_duplicate: DKIMDuplicate) -> None:
        """Duplicate DKIM key from one domain to another."""
        # Get source domain DKIM details
        from_domain_dkim = self.get_details(dkim_duplicate.from_domain, privkey=True)
        to_domain = dkim_duplicate.to_domain
        if not self._is_valid_domain_name(to_domain):
            raise ValueError("DKIM target domain invalid")

        # Copy DKIM data
        self.store.hset("DKIM_PUB_KEYS", to_domain, from_domain_dkim.pubkey)
        self.store.hset("DKIM_SELECTORS", to_domain, from_domain_dkim.dkim_selector)
        self.store.hset("DKIM_PRIV_KEYS", f"{from_domain_dkim.dkim_selector}.{to_domain}",
                        base64.b64decode(from_domain_dkim.privkey))

    def delete_key(self, domain: str) -> None:
        """Delete DKIM keys for a domain."""
        if not self._is_valid_domain_name(domain):
            raise ValueError("DKIM domain invalid")

        # Get selector before deleting
        selector = self.store.hget("DKIM_SELECTORS", domain)

        # Delete all DKIM data for domain
        self.store.hdel("DKIM_PUB_KEYS", domain)
        self.store.hdel("DKIM_SELECTORS", domain)
        if selector:
            self.store.hdel("DKIM_PRIV_KEYS", f"{selector}.{domain}")

    def _is_valid_domain_name(self, domain: str) -> bool:
        """Validate domain name format."""
        pattern = r"^(?!-)([A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,}$"
        return re.match(pattern, domain) is not None

    def _is_valid_selector(self, selector: str) -> bool:
        """Validate DKIM selector format."""
        # Allow alphanumeric characters, hyphens, underscores, and dots
        return bool(re.match(r'^[a-zA-Z0-9\-_\.]+$', selector))

    def _generate_dkim_keypair(self, key_size) -> dict:
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

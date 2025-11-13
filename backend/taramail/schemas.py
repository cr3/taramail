from typing import Annotated, Any

import idna
from pydantic import (
    AfterValidator,
    WithJsonSchema,
)

from taramail.email import is_email


def _validate_alias(v: Any) -> str:
    s = v.strip()

    if not is_email(s):
        if not s.startswith("@"):
            raise ValueError(f"Invalid alias: {v}")

        _validate_domain(s[1:])

    return s

AliasStr = Annotated[
    str,
    AfterValidator(_validate_alias),
    WithJsonSchema({"type": "string", "format": "alias"})
]

def _validate_domain(v: Any) -> str:
    """Validate Unicode (IDN) domains."""
    s = v.strip()
    try:
        ascii_domain = idna.encode(s, uts46=True).decode("ascii")
    except idna.IDNAError as e:
        raise ValueError(f"Invalid internationalized domain: {e}") from e

    labels = ascii_domain.split(".")
    if len(labels) < 2:
        raise ValueError("Domain should include a TLD")

    return s.lower()

DomainStr = Annotated[
    str,
    AfterValidator(_validate_domain),
    WithJsonSchema({"type": "string", "format": "idn-domain"})
]

def _validate_goto(v: Any) -> str:
    gotos = list(filter(None, map(str.strip, v.split(","))))
    if not gotos:
        raise ValueError("Goto should not be empty")

    for goto in gotos:
        if not is_email(goto) and not goto.endswith("@localhost"):
            raise ValueError(f"Goto should be a valid email: {goto}")

    return ",".join(gotos)

GotoStr = Annotated[
    str,
    AfterValidator(_validate_goto),
    WithJsonSchema({"type": "string", "format": "goto"})
]


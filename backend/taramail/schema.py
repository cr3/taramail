from typing import Annotated, Any

import idna
from pydantic import (
    AfterValidator,
    WithJsonSchema,
)


def _validate_domain(v: Any) -> str:
    """Validate Unicode (IDN) domains."""
    s = v.strip()
    try:
        ascii_domain = idna.encode(s, uts46=True).decode("ascii")
    except idna.IDNAError as e:
        raise ValueError(f"invalid internationalized domain: {e}") from e

    labels = ascii_domain.split(".")
    if len(labels) < 2:
        raise ValueError("domain must include a TLD")

    return s.lower()


DomainStr = Annotated[
    str,
    AfterValidator(_validate_domain),
    WithJsonSchema({"type": "string", "format": "idn-domain"})
]

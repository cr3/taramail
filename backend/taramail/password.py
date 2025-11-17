"""Password functions."""

import re

import bcrypt
from attrs import (
    define,
    field,
)
from pydantic import BaseModel

from taramail.store import Store


class PasswordValidationError(Exception):
    """Raised when an invalid password is given."""


class PasswordPolicy(BaseModel):

    length: int = 8
    chars: bool = True
    special_chars: bool = True
    numbers: bool = True
    lowerupper: bool = True

    def validate_passwords(self, password1: str, password2: str) -> None:
        """Validate that two passwords are the same and respect the policy."""
        if password1 != password2:
            raise PasswordValidationError("Passwords do not match")

        if any([
            self.length and len(password1) < self.length,
            self.chars and not re.search(r"[a-zA-Z]", password1),
            self.special_chars and not re.search(r"[^a-zA-Z\d]", password1),
            self.numbers and not re.search(r"\d", password1),
            self.lowerupper and (not re.search(r"[a-z]", password1) or not re.search(r"[A-Z]", password1)),
        ]):
            raise PasswordValidationError("Passwords do not meet policy")


class PasswordPolicyUpdate(BaseModel):

    length: int | None = None
    chars: bool | None = None
    special_chars: bool | None = None
    numbers: bool | None = None
    lowerupper: bool | None = None


@define(frozen=True)
class PasswordPolicyManager:

    store: Store
    default: PasswordPolicy = field(factory=PasswordPolicy)

    def get_policy(self) -> PasswordPolicy:
        if value := self.store.hgetall("PASSWORD_POLICY"):
            return PasswordPolicy(**value)
        else:
            return self.default.copy()

    def update_policy(self, policy_update: PasswordPolicyUpdate) -> PasswordPolicy:
        for policy in PasswordPolicy.__fields__:
            value = getattr(policy_update, policy)
            if value is not None:
                self.store.hset("PASSWORD_POLICY", policy, value)

        return self.get_policy()

    def reset_policy(self) -> PasswordPolicy:
        self.store.delete("PASSWORD_POLICY")

        return self.get_policy()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify whether the plain password matches the hashed password."""
    if m := re.match(r"{(?P<scheme>.*?)}(?P<hashed_password>.*)", hashed_password):
        match m.group("scheme"):
            case "BLF-CRYPT":
                return bcrypt.checkpw(
                    plain_password.encode("utf-8"),
                    m.group("hashed_password").encode("utf-8"),
                )
            case scheme:
                raise ValueError(f"Unsupported scheme: {scheme}")

    raise ValueError(f"Missing scheme: {hashed_password}")


def hash_password(plain_password: str, scheme="BLF-CRYPT") -> str:
    """Return a hashed password from a plain password."""
    match scheme:
        case "BLF-CRYPT":
            hashed_password = bcrypt.hashpw(
                plain_password.encode("utf-8"),
                bcrypt.gensalt(),
            ).decode("utf-8")
        case _:
            raise ValueError(f"Unsupported scheme: {scheme}")

    return f"{{{scheme}}}{hashed_password}"

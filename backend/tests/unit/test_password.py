"""Unit tests for the password module."""

import pytest
from hamcrest import (
    assert_that,
    has_properties,
)

from taramail.password import (
    PasswordPolicy,
    PasswordPolicyUpdate,
    PasswordValidationError,
    hash_password,
    verify_password,
)


def make_policy(length=0, chars=False, special_chars=False, numbers=False, lowerupper=False):
    """Make a password policy with minimal complexity for testing purposes."""
    return PasswordPolicy(
        length=length,
        chars=chars,
        special_chars=special_chars,
        numbers=numbers,
        lowerupper=lowerupper,
    )


def test_password_policy_validate_passwords_not_match():
    """Validating passwords that do not match should raise."""
    password_policy = make_policy()
    with pytest.raises(PasswordValidationError):
        password_policy.validate_passwords("a", "b")


@pytest.mark.parametrize("password_policy, password", [
    (make_policy(), ""),
    (make_policy(chars=True), "a"),
    (make_policy(special_chars=True), "!"),
    (make_policy(numbers=True), "1"),
    (make_policy(lowerupper=True), "aB"),
    (make_policy(lowerupper=True), "Ab"),
])
def test_password_policy_validate_passwords_valid(password_policy, password):
    """Validating a valid password should not raise."""
    password_policy.validate_passwords(password, password)


@pytest.mark.parametrize("password_policy, password", [
    (make_policy(length=1), ""),
    (make_policy(chars=True), "1"),
    (make_policy(chars=True), "!"),
    (make_policy(special_chars=True), "a"),
    (make_policy(special_chars=True), "1"),
    (make_policy(numbers=True), "a"),
    (make_policy(numbers=True), "!"),
    (make_policy(lowerupper=True), "a"),
    (make_policy(lowerupper=True), "B"),
])
def test_password_policy_validate_passwords_invalid(password_policy, password):
    """Validating an invalid password should raise."""
    with pytest.raises(PasswordValidationError):
        password_policy.validate_passwords(password, password)


def test_password_policy_manager_get_policy(password_policy_manager):
    """Getting the policy should return the default policy."""
    policy = password_policy_manager.get_policy()

    assert policy == password_policy_manager.default


def test_password_policy_manager_update_policy(password_policy_manager):
    """Updating the policy should return the new policy."""
    policy_update = PasswordPolicyUpdate(
        length=1,
        chars=False,
        special_chars=False,
        numbers=False,
        lowerupper=False,
    )
    policy = password_policy_manager.update_policy(policy_update)

    assert_that(policy, has_properties(
        length=1,
        chars=False,
        special_chars=False,
        numbers=False,
        lowerupper=False,
    ))


def test_password_policy_manager_reset_policy(password_policy_manager):
    """Updating the policy should return the new policy."""
    policy_update = PasswordPolicyUpdate(length=1)
    password_policy_manager.update_policy(policy_update)
    policy = password_policy_manager.reset_policy()

    assert policy == password_policy_manager.default


def test_verify_hashed_password(unique):
    """Hashing a plain password and verifying it should return true."""
    plain_password = unique("password")
    hashed_password = hash_password(plain_password)
    assert verify_password(plain_password, hashed_password)


def test_verify_wrong_password(unique):
    """Verifying a wrong password should return false."""
    plain_password1, plain_password2 = unique("password"), unique("password")
    hashed_password1 = hash_password(plain_password1)
    assert not verify_password(plain_password2, hashed_password1)

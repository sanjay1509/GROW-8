"""Password hashing and bcrypt's 72-byte limit (ADR 0005)."""

import bcrypt
import pytest

from app.core.security import (
    BCRYPT_MAX_BYTES,
    hash_password,
    password_fits_bcrypt,
    same_password,
    verify_password,
)


def test_round_trip() -> None:
    assert verify_password("Grow8Dev!2026", hash_password("Grow8Dev!2026"))
    assert not verify_password("wrong", hash_password("Grow8Dev!2026"))


def test_limit_counts_utf8_bytes_not_characters() -> None:
    assert password_fits_bcrypt("a" * 72)
    assert not password_fits_bcrypt("a" * 73)
    assert password_fits_bcrypt("é" * 36)  # 36 characters, 72 bytes
    assert not password_fits_bcrypt("é" * 37)  # 37 characters, 74 bytes


def test_hashing_refuses_a_password_bcrypt_would_cut() -> None:
    hash_password("a" * BCRYPT_MAX_BYTES)
    with pytest.raises(ValueError):
        hash_password("a" * (BCRYPT_MAX_BYTES + 1))


def test_hash_of_an_over_long_password_from_before_the_cap_still_verifies() -> None:
    long_password = "x" * 100
    # what bcrypt 4.x stored for it: a hash of the first 72 bytes
    old_hash = bcrypt.hashpw(long_password.encode()[:72], bcrypt.gensalt()).decode()

    assert verify_password(long_password, old_hash)
    assert verify_password(long_password[:72], old_hash)  # bcrypt never saw the rest
    assert not verify_password(long_password[:71], old_hash)


def test_same_password_compares_what_bcrypt_sees() -> None:
    assert same_password("x" * 100, "x" * 72)
    assert not same_password("x" * 72, "x" * 71)

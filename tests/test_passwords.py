"""Password storage. The first place in this project that keeps a secret.

Standard-library scrypt rather than argon2-cffi: it is memory-hard, salted and
slow, which is the requirement, and it is the one part of this system where an
extra dependency is an extra supply chain to trust.
"""
import hashlib

import pytest

from ninanatur.auth.passwords import (
    SCRYPT_N,
    SCRYPT_R,
    hash_password,
    needs_rehash,
    verify_password,
)


def test_a_password_verifies_against_its_own_hash() -> None:
    stored = hash_password("ein gutes Passwort")
    assert verify_password("ein gutes Passwort", stored) is True


def test_a_wrong_password_does_not() -> None:
    stored = hash_password("ein gutes Passwort")
    assert verify_password("ein anderes Passwort", stored) is False


def test_the_same_password_hashes_differently_every_time() -> None:
    """A shared salt turns one cracked password into all of them."""
    a = hash_password("gleiches Passwort")
    b = hash_password("gleiches Passwort")
    assert a != b


def test_the_hash_does_not_contain_the_password() -> None:
    stored = hash_password("Sonnenblume2026")
    assert "Sonnenblume" not in stored


def test_the_parameters_travel_with_the_hash() -> None:
    """So they can be raised later without locking everyone out — the stored
    hash says how it was made."""
    stored = hash_password("x" * 12)
    assert stored.startswith("scrypt$")
    assert str(SCRYPT_N) in stored


def test_it_is_actually_expensive() -> None:
    # Not a benchmark, a floor: a fast hash here is the whole failure mode.
    assert SCRYPT_N >= 2**15
    assert SCRYPT_R >= 8


def test_a_stored_hash_from_weaker_parameters_is_flagged() -> None:
    weak = f"scrypt${2**12}${SCRYPT_R}$1$" + "00" * 16 + "$" + "00" * 32
    assert needs_rehash(weak) is True
    assert needs_rehash(hash_password("x" * 12)) is False


def test_a_malformed_hash_fails_closed() -> None:
    # Never "no parseable hash, so let them in".
    for broken in ("", "scrypt$", "nonsense", "scrypt$a$b$c$d$e"):
        assert verify_password("anything", broken) is False


def test_verification_does_not_raise_on_a_foreign_algorithm() -> None:
    assert verify_password("x", "bcrypt$2b$12$something") is False


def test_it_uses_a_constant_time_comparison() -> None:
    """A byte-by-byte compare leaks the hash one character at a time."""
    import inspect

    from ninanatur.auth import passwords

    assert "compare_digest" in inspect.getsource(passwords)


def test_an_empty_password_is_refused_rather_than_hashed() -> None:
    with pytest.raises(ValueError):
        hash_password("")


def test_the_hash_is_a_recognisable_scrypt_hash() -> None:
    stored = hash_password("x" * 12)
    algorithm, n, r, p, salt, digest = stored.split("$")
    assert algorithm == "scrypt"
    assert int(n) == SCRYPT_N
    assert len(bytes.fromhex(salt)) >= 16
    assert len(bytes.fromhex(digest)) >= 32
    # And it really is scrypt of that salt.
    again = hashlib.scrypt(
        ("x" * 12).encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p),
        maxmem=2 * 128 * int(n) * int(r) * int(p) + 1024, dklen=len(bytes.fromhex(digest)),
    )
    assert again.hex() == digest

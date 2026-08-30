"""Storing a password so that stealing the database does not steal the password.

`hashlib.scrypt` rather than argon2-cffi. Argon2id is the more modern choice and
scrypt is the one the standard library ships: memory-hard, salted and slow,
which is the requirement (RFC 7914). This is the single place in the system
where an added dependency would also be an added supply chain to trust, and the
container gains no build step. Recorded as a trade-off, not as a claim that
scrypt is the better algorithm.

Parameters measured on this project's own hardware: N=2^16, r=8, p=1 is 64 MB
and about 150 ms — expensive enough that a stolen database is not a wordlist
away from every account, cheap enough not to be a denial-of-service lever. The
rate limit in front of it is the other half of that.
"""
from __future__ import annotations

import hashlib
import hmac
import os

SCRYPT_N = 2**16
SCRYPT_R = 8
SCRYPT_P = 1
SALT_BYTES = 16
KEY_BYTES = 32


def _derive(password: str, salt: bytes, n: int, r: int, p: int, length: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n,
        r=r,
        p=p,
        # scrypt refuses to allocate beyond maxmem, and the default is far below
        # what these parameters need, so it has to be stated.
        maxmem=2 * 128 * n * r * p + 1024,
        dklen=length,
    )


def hash_password(password: str) -> str:
    """`scrypt$N$r$p$salt$hash`, all hex.

    The parameters travel with the hash so they can be raised later without
    locking everybody out: a stored hash says how it was made.
    """
    if not password:
        raise ValueError("a password is required")
    salt = os.urandom(SALT_BYTES)
    digest = _derive(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P, KEY_BYTES)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Whether the password matches. Fails closed on anything unparseable."""
    try:
        algorithm, n, r, p, salt_hex, digest_hex = stored.split("$")
        if algorithm != "scrypt":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = _derive(password, salt, int(n), int(r), int(p), len(expected))
    except (ValueError, TypeError, MemoryError):
        # A malformed or foreign hash is never a reason to let somebody in.
        return False
    # Constant time: a byte-by-byte compare leaks the hash one character at a
    # time to anyone who can measure the response.
    return hmac.compare_digest(actual, expected)


def needs_rehash(stored: str) -> bool:
    """Whether this hash was made with weaker parameters than we now use."""
    try:
        algorithm, n, r, p, _, _ = stored.split("$")
    except ValueError:
        return True
    return (
        algorithm != "scrypt"
        or int(n) < SCRYPT_N
        or int(r) < SCRYPT_R
        or int(p) < SCRYPT_P
    )

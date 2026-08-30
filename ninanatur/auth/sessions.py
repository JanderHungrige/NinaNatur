"""Session tokens: made with real entropy, stored only as a hash.

The token in the cookie is the credential. What the database keeps is a SHA-256
of it, so a stolen database is a list of useless strings rather than a drawer
full of working logins. There is no need for the server ever to know the token
it issued — only to recognise one when it comes back.
"""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

COOKIE_NAME = "ninanatur_session"
TOKEN_BYTES = 32
SESSION_DAYS = 30


@dataclass(frozen=True)
class Account:
    account_id: int
    username: str
    email: str | None


def _now() -> datetime:
    return datetime.now(UTC)


def token_hash(token: str) -> str:
    """A plain SHA-256: the token already has 256 bits of entropy, so there is
    nothing for a slow hash to protect against here — unlike a password, this
    is not something a person chose."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue(conn: sqlite3.Connection, account_id: int) -> str:
    """Create a session and return the token. It is never stored as given."""
    token = secrets.token_urlsafe(TOKEN_BYTES)
    now = _now()
    conn.execute(
        "INSERT INTO session (token_hash, account_id, created_at, expires_at)"
        " VALUES (?, ?, ?, ?)",
        (
            token_hash(token),
            account_id,
            now.isoformat(),
            (now + timedelta(days=SESSION_DAYS)).isoformat(),
        ),
    )
    conn.commit()
    return token


def account_for(conn: sqlite3.Connection, token: str | None) -> Account | None:
    """The account a token belongs to, or None. Expired sessions are None."""
    if not token:
        return None
    row = conn.execute(
        "SELECT a.account_id, a.username, a.email, s.expires_at"
        " FROM session s JOIN account a ON a.account_id = s.account_id"
        " WHERE s.token_hash = ?",
        (token_hash(token),),
    ).fetchone()
    if row is None:
        return None
    if datetime.fromisoformat(row["expires_at"]) <= _now():
        return None
    return Account(
        account_id=int(row["account_id"]), username=row["username"], email=row["email"]
    )


def revoke(conn: sqlite3.Connection, token: str | None) -> None:
    if not token:
        return
    conn.execute("DELETE FROM session WHERE token_hash = ?", (token_hash(token),))
    conn.commit()

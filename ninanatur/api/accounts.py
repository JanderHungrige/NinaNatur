"""Registration, login, logout — and the rate limit that has to come with them.

The API has had no rate limiting since Wave 3, which was defensible while the
only credential was a 32-byte share token. It stops being defensible the moment
a person chooses a password.
"""
from __future__ import annotations

import sqlite3
import time
from collections import defaultdict
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from ninanatur.api.deps import get_connection
from ninanatur.api.schemas import (
    AccountOut,
    Credentials,
    OwnedGarden,
    OwnedGardens,
    Registration,
)
from ninanatur.auth.passwords import hash_password, verify_password
from ninanatur.auth.sessions import COOKIE_NAME, Account, account_for, issue, revoke

router = APIRouter(prefix="/api/v1", tags=["accounts"])

# In-process and per-IP. Honest about what it is: one container, and a restart
# forgets everything. A shared store is the answer at more than one process, and
# a slow login is not a substitute for one — it is the floor beneath it.
WINDOW_S = 300.0
MAX_ATTEMPTS = 10
ATTEMPTS: dict[str, list[float]] = defaultdict(list)

# Said where the choice is made, not discovered later.
NO_EMAIL_NOTE = (
    "Ohne E-Mail-Adresse kann dein Passwort nicht zurückgesetzt werden. "
    "Vergisst du es, ist der Zugang verloren."
)
EMAIL_NOTE = "Mit deiner E-Mail-Adresse lässt sich das Passwort zurücksetzen."

# The one answer both a wrong password and an unknown user get, so the login
# form is not a username oracle.
BAD_LOGIN = "Benutzername oder Passwort stimmt nicht."


def _client(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _rate_limit(request: Request, bucket: str) -> None:
    key = f"{bucket}:{_client(request)}"
    now = time.monotonic()
    recent = [t for t in ATTEMPTS[key] if now - t < WINDOW_S]
    if len(recent) >= MAX_ATTEMPTS:
        ATTEMPTS[key] = recent
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Zu viele Versuche. Bitte warte ein paar Minuten.",
        )
    recent.append(now)
    ATTEMPTS[key] = recent


def _set_cookie(response: Response, request: Request, token: str) -> None:
    # Secure follows the scheme the request actually arrived on, including the
    # proxy's header — hardcoding it on breaks local development, hardcoding it
    # off ships a session cookie over plaintext.
    forwarded = request.headers.get("x-forwarded-proto", "")
    https = request.url.scheme == "https" or forwarded.split(",")[0].strip() == "https"
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        secure=https,
        # Lax rather than Strict: a share link followed from someone's message
        # must still find the session, and this is not a state-changing GET.
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        path="/",
    )


def current_account(
    request: Request,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> Account | None:
    """The logged-in account, or None. Never raises — callers decide."""
    return account_for(conn, request.cookies.get(COOKIE_NAME))


def require_account(
    account: Annotated[Account | None, Depends(current_account)],
) -> Account:
    if account is None:
        raise HTTPException(status_code=401, detail="Nicht angemeldet.")
    return account


@router.post("/accounts", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def register(
    payload: Registration,
    request: Request,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> AccountOut:
    """Create an account. Email is optional and the cost of that is returned."""
    _rate_limit(request, "register")
    taken = conn.execute(
        "SELECT 1 FROM account WHERE username = ?", (payload.username,)
    ).fetchone()
    if taken is not None:
        raise HTTPException(status_code=409, detail="Dieser Benutzername ist vergeben.")

    conn.execute(
        "INSERT INTO account (username, email, password_hash, created_at)"
        " VALUES (?, ?, ?, ?)",
        (
            payload.username,
            payload.email,
            hash_password(payload.password),
            datetime.now(UTC).isoformat(),
        ),
    )
    conn.commit()
    return AccountOut(
        username=payload.username,
        email=payload.email,
        recovery_note=EMAIL_NOTE if payload.email else NO_EMAIL_NOTE,
    )


@router.post("/sessions", response_model=AccountOut)
def log_in(
    payload: Credentials,
    request: Request,
    response: Response,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> AccountOut:
    """Log in. A wrong password and an unknown user answer identically."""
    _rate_limit(request, "login")
    row = conn.execute(
        "SELECT account_id, username, email, password_hash FROM account WHERE username = ?",
        (payload.username,),
    ).fetchone()

    if row is None or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail=BAD_LOGIN)

    token = issue(conn, int(row["account_id"]))
    _set_cookie(response, request, token)
    return AccountOut(
        username=row["username"],
        email=row["email"],
        recovery_note=EMAIL_NOTE if row["email"] else NO_EMAIL_NOTE,
    )


@router.delete("/sessions", status_code=status.HTTP_204_NO_CONTENT)
def log_out(
    request: Request,
    response: Response,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> Response:
    revoke(conn, request.cookies.get(COOKIE_NAME))
    response.delete_cookie(COOKIE_NAME, path="/")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/accounts/me", response_model=AccountOut)
def me(account: Annotated[Account, Depends(require_account)]) -> AccountOut:
    return AccountOut(
        username=account.username,
        email=account.email,
        recovery_note=EMAIL_NOTE if account.email else NO_EMAIL_NOTE,
    )


@router.get("/accounts/me/gardens", response_model=OwnedGardens)
def my_gardens(
    account: Annotated[Account, Depends(require_account)],
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> OwnedGardens:
    """The gardens this account has claimed.

    A place to keep the links, not a replacement for them: the share token is
    still what opens a garden, and it comes back here so the list can.
    """
    rows = conn.execute(
        "SELECT name, share_token, updated_at FROM garden WHERE owner_id = ?"
        " ORDER BY updated_at DESC",
        (str(account.account_id),),
    )
    return OwnedGardens(
        gardens=[
            OwnedGarden(
                name=r["name"], share_token=r["share_token"], updated_at=r["updated_at"]
            )
            for r in rows
        ]
    )

"""Registration, login, logout — and the rate limit that has to come with them.

The limit itself lives in `api/ratelimit.py`, on the volume and keyed on the
visitor rather than the proxy.

The API has had no rate limiting since Wave 3, which was defensible while the
only credential was a 32-byte share token. It stops being defensible the moment
a person chooses a password.

Every route here that changes something checks where the request came from
(`api/origin.py`): the cookie's `SameSite=Lax` lets pages on the other w3rth.de
projects through, because to a browser they are the same site.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from ninanatur.api import ratelimit
from ninanatur.api.deps import get_connection
from ninanatur.api.origin import same_origin
from ninanatur.api.schemas import (
    AccountOut,
    Credentials,
    OwnedGarden,
    OwnedGardens,
    Registration,
)
from ninanatur.auth.passwords import hash_password, needs_rehash, verify_password
from ninanatur.auth.sessions import (
    COOKIE_NAME,
    SESSION_DAYS,
    Account,
    account_for,
    issue,
    revoke,
)
from ninanatur.web.logs import network_of, security_event, short_hash

router = APIRouter(prefix="/api/v1", tags=["accounts"])

# Said where the choice is made, not discovered later — and only what exists.
# There is no password reset. The address is stored unverified, and a reset
# mailed to an address nobody confirmed hands the account to whoever typed it:
# verification comes first, whenever a reset is built (Wave 20, feature 9). The
# note used to promise a reset with an e-mail, and there was none.
NO_EMAIL_NOTE = (
    "Ohne E-Mail-Adresse kann dein Passwort nicht zurückgesetzt werden. "
    "Vergisst du es, ist der Zugang verloren."
)
EMAIL_NOTE = (
    "Deine E-Mail-Adresse ist gespeichert, aber noch nicht bestätigt. Zurücksetzen "
    "lässt sich das Passwort damit noch nicht — vergisst du es, ist der Zugang verloren."
)

# The one answer both a wrong password and an unknown user get, so the login
# form is not a username oracle.
BAD_LOGIN = "Benutzername oder Passwort stimmt nicht."


def _set_cookie(response: Response, request: Request, token: str) -> None:
    # Secure follows the scheme the request actually arrived on. Behind the
    # proxy that is the proxy's X-Forwarded-Proto — applied to the URL by the
    # trusted-proxy middleware in `web.app`, and only for a trusted proxy. It
    # used to be read raw here, so anybody talking to the app could decide it.
    # Hardcoding it on breaks local development; off ships a cookie over plaintext.
    https = request.url.scheme == "https"
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        secure=https,
        # Lax rather than Strict: a share link followed from someone's message
        # must still find the session, and this is not a state-changing GET.
        samesite="lax",
        max_age=SESSION_DAYS * 24 * 60 * 60,
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


@router.post("/accounts", response_model=AccountOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(same_origin)])
def register(
    payload: Registration,
    request: Request,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> AccountOut:
    """Create an account. Email is optional and the cost of that is returned."""
    ratelimit.check(conn, request, "register")
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


@router.post("/sessions", response_model=AccountOut, dependencies=[Depends(same_origin)])
def log_in(
    payload: Credentials,
    request: Request,
    response: Response,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> AccountOut:
    """Log in. A wrong password and an unknown user answer identically."""
    ratelimit.check(conn, request, "login")
    row = conn.execute(
        "SELECT account_id, username, email, password_hash FROM account WHERE username = ?",
        (payload.username,),
    ).fetchone()

    if row is None or not verify_password(payload.password, row["password_hash"]):
        # Which account, as a hash: enough to see one being tried again and
        # again, without the log naming anybody.
        security_event("login_failed", client=network_of(ratelimit.client_of(request)),
                       account=short_hash(payload.username))
        raise HTTPException(status_code=401, detail=BAD_LOGIN)

    if needs_rehash(row["password_hash"]):
        # The parameters travel with the hash so that they can be raised; this is
        # where a raised parameter reaches an existing account — the one moment
        # the password itself is in hand. It was never called until Wave 20.
        conn.execute("UPDATE account SET password_hash = ? WHERE account_id = ?",
                     (hash_password(payload.password), row["account_id"]))
        conn.commit()
    token = issue(conn, int(row["account_id"]))
    _set_cookie(response, request, token)
    return AccountOut(
        username=row["username"],
        email=row["email"],
        recovery_note=EMAIL_NOTE if row["email"] else NO_EMAIL_NOTE,
    )


@router.delete("/sessions", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(same_origin)])
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

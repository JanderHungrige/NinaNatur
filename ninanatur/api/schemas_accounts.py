"""Accounts, and the gardens they hold.

Split from `schemas.py` in Wave 21, which re-exports every name here.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class OwnedGarden(BaseModel):
    name: str
    #: Carried so the list can open it. It is still the credential — the account
    #: is a place to keep the links, not a replacement for them.
    share_token: str
    updated_at: str


class OwnedGardens(BaseModel):
    gardens: list[OwnedGarden]


class Registration(BaseModel):
    """What it takes to make an account.

    No composition rules — length and the one obvious mistake, following NIST.
    A rule that demands a digit and a symbol produces `Passwort1!` and a sticky
    note, which is worse than a long phrase.
    """

    username: str = Field(min_length=3, max_length=40, pattern=r"^[\w.-]+$")
    # Eight, not ten. Ten was arbitrary; eight is the floor NIST SP 800-63B
    # sets for a user-chosen secret. The same guidance says not to add
    # composition rules on top, so there are none — what makes a password
    # strong is said in the form as a hint rather than enforced as a gate.
    password: str = Field(min_length=8, max_length=200)
    email: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def not_the_username(self) -> Registration:
        if self.password.strip().lower() == self.username.strip().lower():
            raise ValueError("das Passwort darf nicht der Benutzername sein")
        return self


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=200)


class AccountOut(BaseModel):
    """Never carries the password or the hash — there is no field for either."""

    username: str
    email: str | None
    #: What this account's recovery actually looks like, said here rather than
    #: discovered later.
    recovery_note: str

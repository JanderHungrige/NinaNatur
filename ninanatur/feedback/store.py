"""Feedback as it is kept, before and after it reaches GitHub.

The issue is where a report gets acted on, but filing it can fail — no token
configured, GitHub down, a rate limit — and a bug report lost to any of those is
worse than one that arrives late. So it is written down first, then filed, and
what is still unfiled is a query rather than a guess.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

# One person, one hour. High enough that nobody reporting a real problem in
# earnest will meet it, low enough that a script cannot fill the tracker.
PER_SENDER_HOURLY = 5
# Everybody together. The backstop for what the per-sender count cannot cover,
# because the address it counts by can be forged.
TOTAL_HOURLY = 40

KINDS = ("bug", "idea")


@dataclass(frozen=True)
class Feedback:
    """One submission, as stored."""

    feedback_id: int
    kind: str
    answers: dict[str, str]
    version: str | None
    created_at: str
    issue_url: str | None


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def sender_hash(address: str) -> str:
    """A stable, non-reversible stand-in for a caller's address.

    Keeping the address itself would be holding personal data to answer one
    question — how many reports came from one place in the last hour — that a
    hash answers just as well.
    """
    return hashlib.sha256(f"ninanatur-feedback|{address}".encode()).hexdigest()[:32]


def too_many_recently(conn: sqlite3.Connection, sender: str) -> str | None:
    """Why this submission should be refused, or None if it should not be.

    The reason rather than a bare bool, so the endpoint can say which limit was
    met: "you have sent several already" and "the tracker is busy" are different
    things to be told.
    """
    since = _an_hour_ago()
    mine: int = conn.execute(
        "SELECT count(*) FROM feedback WHERE sender = ? AND created_at >= ?",
        (sender, since),
    ).fetchone()[0]
    if mine >= PER_SENDER_HOURLY:
        return (
            "Du hast gerade schon mehrere Meldungen geschickt. "
            "Bitte in einer Stunde weiter."
        )
    total: int = conn.execute(
        "SELECT count(*) FROM feedback WHERE created_at >= ?", (since,)
    ).fetchone()[0]
    if total >= TOTAL_HOURLY:
        return "Es kommen gerade sehr viele Meldungen an. Bitte später noch einmal."
    return None


def record(
    conn: sqlite3.Connection,
    *,
    kind: str,
    answers: dict[str, str],
    version: str | None,
    sender: str,
) -> int:
    """Write a submission down. Returns its id."""
    if kind not in KINDS:
        raise ValueError(f"unknown kind: {kind!r}; expected one of {KINDS}")
    cursor = conn.execute(
        "INSERT INTO feedback (kind, answers, version, sender, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (kind, json.dumps(answers, ensure_ascii=False), version, sender, now()),
    )
    conn.commit()
    return int(cursor.lastrowid or 0)


def mark_filed(conn: sqlite3.Connection, feedback_id: int, issue_url: str) -> None:
    conn.execute(
        "UPDATE feedback SET issue_url = ?, filed_at = ? WHERE feedback_id = ?",
        (issue_url, now(), feedback_id),
    )
    conn.commit()


def unfiled(conn: sqlite3.Connection) -> list[Feedback]:
    """Everything written down that never reached GitHub.

    The API never calls this. It exists so that "did anything get lost while the
    token was wrong" is a question with an answer.
    """
    rows = conn.execute(
        "SELECT feedback_id, kind, answers, version, created_at, issue_url"
        " FROM feedback WHERE issue_url IS NULL ORDER BY created_at"
    ).fetchall()
    return [
        Feedback(
            feedback_id=row[0],
            kind=row[1],
            answers=json.loads(row[2]),
            version=row[3],
            created_at=row[4],
            issue_url=row[5],
        )
        for row in rows
    ]


def _an_hour_ago() -> str:
    return (datetime.now(UTC) - timedelta(hours=1)).isoformat(timespec="seconds")

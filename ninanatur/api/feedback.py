"""Sending a bug report or a wish from inside the app.

The schemas live here rather than in `schemas.py`: that file is already past the
length limit, and these four are used by nothing else.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ninanatur.api.deps import get_connection
from ninanatur.feedback import issues, store
from ninanatur.version import app_version

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])

# Long enough for a careful description with a pasted error message, short
# enough that the endpoint cannot be used to store somebody's novel.
MAX_ANSWER = 4000


class QuestionOut(BaseModel):
    key: str
    label: str
    hint: str
    required: bool


class QuestionsOut(BaseModel):
    """What to ask, per kind. The form renders this rather than its own copy."""

    bug: list[QuestionOut]
    idea: list[QuestionOut]


class FeedbackIn(BaseModel):
    kind: str = Field(pattern="^(bug|idea)$")
    answers: dict[str, str]


class FeedbackOut(BaseModel):
    """Whether it arrived, and where it went.

    `filed` is false when the report was kept but GitHub would not take it. That
    is not an error for the sender — nothing was lost — so it is said plainly
    rather than raised.
    """

    filed: bool
    issue_url: str | None
    message: str


@router.get("/questions", response_model=QuestionsOut)
def questions() -> QuestionsOut:
    return QuestionsOut(
        bug=[QuestionOut(**vars(q)) for q in issues.BUG],
        idea=[QuestionOut(**vars(q)) for q in issues.IDEA],
    )


@router.post("", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def send(
    submission: FeedbackIn,
    request: Request,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> FeedbackOut | JSONResponse:
    answers = _cleaned(submission.kind, submission.answers)
    if answers is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Bitte beantworte wenigstens die ersten beiden Fragen."},
        )

    sender = store.sender_hash(_caller(request))
    refusal = store.too_many_recently(conn, sender)
    if refusal is not None:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, content={"detail": refusal}
        )

    version = app_version()
    # Written down before it is sent. Filing can fail for reasons that have
    # nothing to do with the sender, and a report lost to one of them is worse
    # than one that arrives late.
    feedback_id = store.record(
        conn,
        kind=submission.kind,
        answers=answers,
        version=version,
        sender=sender,
    )

    try:
        url = issues.file_issue(
            submission.kind, answers, version, request.headers.get("user-agent")
        )
    except Exception:
        logger.exception("feedback %s stored but not filed", feedback_id)
        return FeedbackOut(
            filed=False,
            issue_url=None,
            message="Angekommen und gespeichert. Ins Projekt eingetragen wird sie gleich.",
        )

    store.mark_filed(conn, feedback_id, url)
    return FeedbackOut(filed=True, issue_url=url, message="Danke — ist eingetragen.")


def _cleaned(kind: str, answers: dict[str, str]) -> dict[str, str] | None:
    """The answers to the questions actually asked, or None if too little was
    said to be worth anybody's time.

    Keys the form did not ask about are dropped rather than rejected: a stale
    bundle sending an old key should still deliver the report.
    """
    kept = {
        q.key: answers.get(q.key, "").strip()[:MAX_ANSWER] for q in issues.QUESTIONS[kind]
    }
    if any(not kept[q.key] for q in issues.QUESTIONS[kind] if q.required):
        return None
    return kept


def _caller(request: Request) -> str:
    """Who to count this submission against.

    `X-Forwarded-For` because the app sits behind a proxy and `request.client`
    is otherwise the proxy for everybody. It can be forged, which is why the
    per-sender limit is a speed bump and the global hourly cap is the actual
    backstop.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

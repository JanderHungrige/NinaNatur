"""The questions that get asked, and the GitHub issue they turn into.

The questions live here rather than in the form so there is one copy of them.
The form asks the server what to ask; the issue is then written from the same
list, and a question can be changed in one place without the heading over an
answer quietly disagreeing with the question that produced it.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

import requests

from ninanatur.web.environment import environment, is_production

logger = logging.getLogger(__name__)

TOKEN_ENV = "NINANATUR_GITHUB_TOKEN"
REPO_ENV = "NINANATUR_GITHUB_REPO"
DEFAULT_REPO = "JanderHungrige/NinaNatur"
TIMEOUT_S = 15


@dataclass(frozen=True)
class Question:
    """One thing the form asks."""

    key: str
    label: str
    hint: str
    required: bool


# Guiding rather than open: "was ist kaputt" gets an answer nobody can act on
# about half the time, and the three below are what turns a report into a
# reproduction. The last one is optional on purpose — somebody who cannot
# reproduce it should still be able to send what they saw.
BUG = (
    Question(
        key="doing",
        label="Was wolltest du gerade tun?",
        hint="z. B. „ein Beet einzeichnen“ oder „eine Pflanze eintragen“",
        required=True,
    ),
    Question(
        key="happened",
        label="Was ist stattdessen passiert?",
        hint="Was du gesehen hast — gern wörtlich, wenn eine Meldung kam",
        required=True,
    ),
    Question(
        key="steps",
        label="Wie kommt man dahin?",
        hint="Optional. Die Schritte, wenn du sie wiederholen kannst",
        required=False,
    ),
)

IDEA = (
    Question(
        key="wish",
        label="Was möchtest du tun können?",
        hint="Die Sache selbst, noch nicht die Lösung",
        required=True,
    ),
    Question(
        key="why",
        label="Was wäre damit leichter?",
        hint="Wofür du es brauchst — das entscheidet meist, wie es aussehen muss",
        required=True,
    ),
    Question(
        key="today",
        label="Wie behilfst du dir bisher?",
        hint="Optional. Auch „gar nicht“ ist eine nützliche Antwort",
        required=False,
    ),
)

QUESTIONS = {"bug": BUG, "idea": IDEA}
LABELS = {"bug": "bug", "idea": "enhancement"}
TITLES = {"bug": "Fehlermeldung", "idea": "Wunsch"}

#: Added to anything filed from somewhere that is not the live site.
#:
#: The default arrangement is that a preview cannot file at all — `.env.dev`
#: leaves the token blank, and an unfiled report still lands on the volume with
#: `issue_url IS NULL`. So the box can be exercised on the preview without
#: touching the tracker, which is what somebody testing the button actually
#: wants.
#:
#: This exists for the other case: when the filing path itself is what needs
#: testing, a token can be put in `.env.dev` and every issue it creates is
#: visibly from a preview. Without the label they are indistinguishable from
#: real reports, and a tracker somebody has to sort by hand is a tracker that
#: stops being sorted.
PREVIEW_LABEL = "from-preview"


class NotConfigured(RuntimeError):
    """No GitHub token in the environment, so nothing can be filed."""


def file_issue(
    kind: str, answers: dict[str, str], version: str | None, agent: str | None = None
) -> str:
    """Create the issue and return its URL.

    Raises rather than returning None on failure: the caller has already stored
    the report and needs to know whether to tell the sender it arrived.
    """
    token = os.environ.get(TOKEN_ENV, "").strip()
    if not token:
        raise NotConfigured(f"{TOKEN_ENV} is not set")
    repo = os.environ.get(REPO_ENV, "").strip() or DEFAULT_REPO

    response = requests.post(
        f"https://api.github.com/repos/{repo}/issues",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={
            "title": title_for(kind, answers),
            "body": body_for(kind, answers, version, agent),
            "labels": _labels_for(kind),
        },
        timeout=TIMEOUT_S,
    )
    if response.status_code != 201:
        # Logged with the status and GitHub's own message, because "filing
        # failed" on its own is the report that cannot be acted on.
        logger.error(
            "filing feedback failed: %s %s", response.status_code, response.text[:400]
        )
        response.raise_for_status()
        raise RuntimeError(f"unexpected status {response.status_code}")
    return str(response.json()["html_url"])


def _labels_for(kind: str) -> list[str]:
    """The kind, plus where it came from when that is not the live site."""
    labels = [LABELS[kind]]
    if not is_production():
        labels.append(PREVIEW_LABEL)
    return labels


def title_for(kind: str, answers: dict[str, str]) -> str:
    """The first answer, shortened. A tracker of forty rows called
    "Fehlermeldung" is a tracker nobody reads."""
    first = QUESTIONS[kind][0].key
    said = " ".join(answers.get(first, "").split())
    if not said:
        return TITLES[kind]
    short = said if len(said) <= 70 else said[:67].rstrip() + "…"
    return f"{TITLES[kind]}: {short}"


def body_for(
    kind: str, answers: dict[str, str], version: str | None, agent: str | None = None
) -> str:
    """The issue text: every question that was asked, with what was answered.

    The footer carries the version, the browser, and — when this is not the live
    site — which environment it came from. Nothing else. Not the share token, not
    the garden: a token is the entire access control for somebody's plan, and
    this issue is public.
    """
    parts = []
    for question in QUESTIONS[kind]:
        said = answers.get(question.key, "").strip()
        parts.append(f"### {question.label}\n\n{defused(said) if said else '_(leer)_'}")
    footer = ["Über den Rückmeldeknopf in der App gemeldet"]
    if not is_production():
        # In the body as well as in a label. A label can be removed while
        # triaging and the sentence stays, which matters for the one thing this
        # is protecting against: acting on a report about a bug that only ever
        # existed on a preview.
        footer.append(f"aus der Umgebung `{defused(environment())}`")
    if version:
        footer.append(f"Version {defused(version)}")
    if agent:
        footer.append(f"Browser `{defused(agent[:200])}`")
    parts.append("---\n\n" + " · ".join(footer) + ".")
    return "\n\n".join(parts)


def defused(text: str) -> str:
    """Text safe to put in an issue body.

    `@name` in a GitHub issue notifies that person and `#12` links another
    issue. Neither is something a stranger's form submission should be able to
    do, so the zero-width joiner goes after the sigil: it reads identically and
    GitHub stops matching.
    """
    return re.sub(r"([@#])(?=\w)", "\\1\u200d", text)

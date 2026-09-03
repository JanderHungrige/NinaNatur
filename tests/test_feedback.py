"""The feedback box: what is kept, what is filed, and what is refused."""
import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.feedback import issues, store
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app

BUG = {
    "kind": "bug",
    "answers": {
        "doing": "Ein Beet einzeichnen",
        "happened": "Der Plan ist weiß geblieben",
        "steps": "",
    },
}


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    connection: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(connection)
    yield connection


@pytest.fixture()
def client(conn: sqlite3.Connection) -> Iterator[TestClient]:
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def filed(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict[str, str]]]:
    """Nothing in this suite may reach GitHub. The list is what would have."""
    sent: list[tuple[str, dict[str, str]]] = []

    def fake(
        kind: str, answers: dict[str, str], version: str | None, agent: str | None = None
    ) -> str:
        sent.append((kind, answers))
        return "https://github.com/JanderHungrige/NinaNatur/issues/7"

    monkeypatch.setattr("ninanatur.api.feedback.issues.file_issue", fake)
    return sent


# --- the questions --------------------------------------------------------

def test_the_form_is_told_what_to_ask(client: TestClient) -> None:
    """One copy of the questions. A form with its own list drifts from the
    headings the issue is written with."""
    body = client.get("/api/v1/feedback/questions").json()
    assert [q["key"] for q in body["bug"]] == ["doing", "happened", "steps"]
    assert [q["key"] for q in body["idea"]] == ["wish", "why", "today"]
    assert body["bug"][2]["required"] is False


# --- sending --------------------------------------------------------------

def test_a_report_is_stored_and_filed(
    client: TestClient, conn: sqlite3.Connection, filed: list[tuple[str, dict[str, str]]]
) -> None:
    response = client.post("/api/v1/feedback", json=BUG)

    assert response.status_code == 201
    assert response.json()["filed"] is True
    assert response.json()["issue_url"].endswith("/issues/7")
    assert filed[0][0] == "bug"
    row = conn.execute("SELECT kind, issue_url FROM feedback").fetchone()
    assert (row["kind"], row["issue_url"]) == (
        "bug",
        "https://github.com/JanderHungrige/NinaNatur/issues/7",
    )


def test_github_failing_does_not_lose_the_report(
    client: TestClient, conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole reason it is written down before it is sent. A missing token or
    a GitHub outage must not swallow somebody's bug report."""

    def broken(*_args: object, **_kwargs: object) -> str:
        raise issues.NotConfigured("no token here")

    monkeypatch.setattr("ninanatur.api.feedback.issues.file_issue", broken)

    response = client.post("/api/v1/feedback", json=BUG)

    assert response.status_code == 201
    assert response.json()["filed"] is False
    assert "gespeichert" in response.json()["message"]
    assert [f.kind for f in store.unfiled(conn)] == ["bug"]


def test_too_little_said_is_refused_and_not_stored(
    client: TestClient, conn: sqlite3.Connection
) -> None:
    """An empty report costs the sender nothing and the reader everything."""
    response = client.post(
        "/api/v1/feedback",
        json={"kind": "bug", "answers": {"doing": "  ", "happened": ""}},
    )

    assert response.status_code == 400
    assert conn.execute("SELECT count(*) FROM feedback").fetchone()[0] == 0


def test_an_optional_answer_may_be_left_out(client: TestClient) -> None:
    response = client.post(
        "/api/v1/feedback",
        json={"kind": "idea", "answers": {"wish": "Beete kopieren", "why": "Spart Zeit"}},
    )
    assert response.status_code == 201


def test_a_kind_nobody_offers_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/feedback", json={"kind": "praise", "answers": {"doing": "x"}}
    )
    assert response.status_code == 422


# --- limits ---------------------------------------------------------------

def test_one_sender_cannot_fill_the_tracker(client: TestClient) -> None:
    for _ in range(store.PER_SENDER_HOURLY):
        assert client.post("/api/v1/feedback", json=BUG).status_code == 201

    refused = client.post("/api/v1/feedback", json=BUG)
    assert refused.status_code == 429
    assert "Stunde" in refused.json()["detail"]


def test_the_hourly_cap_holds_when_the_address_is_forged(
    client: TestClient, conn: sqlite3.Connection
) -> None:
    """`X-Forwarded-For` can say anything, so the per-sender count alone is a
    speed bump. The global cap is what a script actually meets."""
    for i in range(store.TOTAL_HOURLY):
        response = client.post(
            "/api/v1/feedback", json=BUG, headers={"x-forwarded-for": f"10.0.0.{i}"}
        )
        assert response.status_code == 201

    refused = client.post(
        "/api/v1/feedback", json=BUG, headers={"x-forwarded-for": "10.9.9.9"}
    )
    assert refused.status_code == 429
    assert conn.execute("SELECT count(*) FROM feedback").fetchone()[0] == (
        store.TOTAL_HOURLY
    )


def test_the_address_itself_is_never_stored(
    client: TestClient, conn: sqlite3.Connection
) -> None:
    client.post("/api/v1/feedback", json=BUG, headers={"x-forwarded-for": "203.0.113.9"})

    stored = conn.execute("SELECT sender FROM feedback").fetchone()[0]
    assert "203.0.113.9" not in stored
    assert stored == store.sender_hash("203.0.113.9")


# --- what the issue says --------------------------------------------------

def test_the_title_carries_the_first_answer(client: TestClient) -> None:
    """Forty rows all called "Fehlermeldung" is a tracker nobody opens."""
    assert issues.title_for("bug", BUG["answers"]) == (  # type: ignore[arg-type]
        "Fehlermeldung: Ein Beet einzeichnen"
    )


def test_a_long_first_answer_is_shortened() -> None:
    title = issues.title_for("idea", {"wish": "x" * 200})
    assert len(title) <= 80 and title.endswith("…")


def test_a_submission_cannot_notify_people_or_link_issues() -> None:
    """`@name` pings that person and `#12` cross-links. Neither is something a
    stranger's form should be able to do from a public issue."""
    body = issues.body_for("bug", {"doing": "@torvalds sieh dir #1 an"}, None)

    assert "@torvalds" not in body
    assert "#1 " not in body
    assert "torvalds" in body, "the text must still be readable"


def test_the_body_carries_the_questions_that_were_asked() -> None:
    body = issues.body_for("bug", BUG["answers"], "V0.14.39")  # type: ignore[arg-type]

    for question in issues.BUG:
        assert question.label in body
    assert "V0.14.39" in body
    assert "_(leer)_" in body, "an unanswered optional question should say so"


def test_nothing_the_client_sends_beyond_the_answers_reaches_the_issue(
    client: TestClient, filed: list[tuple[str, dict[str, str]]]
) -> None:
    """A share token is the entire access control for somebody's garden and the
    issue is public. Extra fields are dropped, not forwarded."""
    payload = dict(BUG, share_token="SECRET-TOKEN-DO-NOT-PUBLISH")
    client.post("/api/v1/feedback", json=payload)

    _kind, answers = filed[0]
    assert "SECRET-TOKEN-DO-NOT-PUBLISH" not in str(answers)
    assert set(answers) == {"doing", "happened", "steps"}

"""The Wave 1 shell: health probe and branded page.

/healthz must answer without touching the database — a deploy failing and a
database failing must not look the same to the cron.
"""
from fastapi.testclient import TestClient

from ninanatur.web.app import app

client = TestClient(app)


def test_healthz_reports_ok_with_service_identity() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "ninanatur"
    assert body["version"]


def test_index_serves_the_branded_page() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "NinaNatur" in response.text


def test_page_declares_german_and_a_viewport() -> None:
    """Without lang, screen readers pronounce German text as English."""
    text = client.get("/").text
    assert 'lang="de"' in text
    assert 'name="viewport"' in text


def test_logo_carries_an_accessible_name() -> None:
    text = client.get("/").text
    assert 'role="img"' in text
    assert 'aria-label="NinaNatur Logo"' in text


def test_stylesheet_is_external_not_inlined() -> None:
    text = client.get("/").text
    assert '<link rel="stylesheet" href="/static/styles.css">' in text
    assert "<style" not in text, "styles belong in the stylesheet, not the document"


def test_static_assets_are_served() -> None:
    for path in ("/static/styles.css", "/static/logo.svg"):
        assert client.get(path).status_code == 200


def test_stylesheet_defines_both_themes() -> None:
    css = client.get("/static/styles.css").text
    assert "prefers-color-scheme: dark" in css
    assert "--bg:" in css

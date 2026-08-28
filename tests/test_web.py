"""The Wave 1 shell: health probe, static assets, and the development fallback page.

Since Wave 3, `/` serves the built React bundle when one exists and the Wave 1
page only when it does not. Testing the landing page *through the route* would
therefore pass or fail depending on whether someone had run `npm run build` in
this checkout — so the fallback page is asserted against its file, and the route
tests are limited to what holds either way.

/healthz must answer without touching the database — a deploy failing and a
database failing must not look the same to the cron.
"""
from pathlib import Path

from fastapi.testclient import TestClient

from ninanatur.web.app import STATIC_DIR, app

client = TestClient(app)


def _fallback_page() -> str:
    return (Path(STATIC_DIR) / "index.html").read_text()


def test_healthz_reports_ok_with_service_identity() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "ninanatur"
    assert body["version"]


def test_the_root_serves_something_branded_either_way() -> None:
    """Holds for both the built bundle and the fallback."""
    response = client.get("/")
    assert response.status_code == 200
    assert "NinaNatur" in response.text


def test_whatever_is_served_declares_german_and_a_viewport() -> None:
    """Without lang, screen readers pronounce German text as English."""
    text = client.get("/").text
    assert 'lang="de"' in text
    assert 'name="viewport"' in text


def test_the_fallback_logo_carries_an_accessible_name() -> None:
    text = _fallback_page()
    assert 'role="img"' in text
    assert 'aria-label="NinaNatur Logo"' in text


def test_the_fallback_stylesheet_is_external_not_inlined() -> None:
    text = _fallback_page()
    assert '<link rel="stylesheet" href="/static/styles.css">' in text
    assert "<style" not in text, "styles belong in the stylesheet, not the document"


def test_static_assets_are_served() -> None:
    for path in ("/static/styles.css", "/static/logo.svg"):
        assert client.get(path).status_code == 200


def test_stylesheet_defines_both_themes() -> None:
    css = client.get("/static/styles.css").text
    assert "prefers-color-scheme: dark" in css
    assert "--bg:" in css

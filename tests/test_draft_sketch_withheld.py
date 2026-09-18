"""Draft Sketch's files are handed out by the preview only (doc 97).

Nothing of Warren Davison's is served in public before he has seen his style
in the plan. The theme is a chunk of its own that production never asks for;
this makes sure production would not hand it to somebody who asked by name —
after a release that carried it, before his look.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ninanatur.web.delivery import PREVIEW_ONLY, serve_bundle
from ninanatur.web.environment import ENV_VAR

HIS = f"/{PREVIEW_ONLY}ds-6c7f0598-DwCWq3hY.png"
OURS = "/assets/index-Ab12Cd34.js"


@pytest.fixture()
def site(tmp_path: Path) -> TestClient:
    """A built front end as Vite leaves it, his folder included."""
    (tmp_path / PREVIEW_ONLY).mkdir(parents=True)
    (tmp_path / "index.html").write_text("<!doctype html>")
    (tmp_path / HIS.lstrip("/")).write_bytes(b"\x89PNG his paper")
    (tmp_path / OURS.lstrip("/")).write_text("console.log('ours');")
    app = FastAPI()
    assert serve_bundle(app, tmp_path)
    return TestClient(app)


@pytest.mark.parametrize("deployment", ["prod", "", "staging"])
def test_outside_the_preview_his_files_are_not_there(
    site: TestClient, monkeypatch: pytest.MonkeyPatch, deployment: str,
) -> None:
    monkeypatch.setenv(ENV_VAR, deployment)
    assert site.get(HIS).status_code == 404
    # However it is spelt: a filesystem that ignores case would find it.
    shouted = HIS.replace("assets/draft-sketch", "Assets/Draft-Sketch")
    round_about = HIS.replace("draft-sketch/", "draft-sketch/../draft-sketch/")
    assert site.get(shouted).status_code == 404
    assert site.get(round_about).status_code == 404
    assert site.get(OURS).status_code == 200


def test_the_preview_hands_them_out(site: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_VAR, "dev")
    answer = site.get(HIS)
    assert answer.status_code == 200
    assert answer.content == b"\x89PNG his paper"

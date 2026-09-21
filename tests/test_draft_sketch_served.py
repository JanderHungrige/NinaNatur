"""Draft Sketch's own files are served, wherever the app runs (docs 97, 100).

They were handed out by the preview alone while Warren Davison had not seen his
style in the plan. He gave his permission on 2026-09-10 and the owner lifted the
gate on 2026-09-20, so this is now the opposite test: his chunk and his images
must arrive, or the style the gardener picked draws nothing.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ninanatur.web.delivery import serve_bundle
from ninanatur.web.environment import ENV_VAR

HIS_FOLDER = "assets/draft-sketch/"
HIS = f"/{HIS_FOLDER}ds-6c7f0598-DwCWq3hY.png"
OURS = "/assets/index-Ab12Cd34.js"


@pytest.fixture()
def site(tmp_path: Path) -> TestClient:
    """A built front end as Vite leaves it, his folder included."""
    (tmp_path / HIS_FOLDER).mkdir(parents=True)
    (tmp_path / "index.html").write_text("<!doctype html>")
    (tmp_path / HIS.lstrip("/")).write_bytes(b"\x89PNG his paper")
    (tmp_path / OURS.lstrip("/")).write_text("console.log('ours');")
    app = FastAPI()
    assert serve_bundle(app, tmp_path)
    return TestClient(app)


@pytest.mark.parametrize("deployment", ["prod", "", "dev", "staging"])
def test_his_files_arrive_wherever_the_app_runs(
    site: TestClient, monkeypatch: pytest.MonkeyPatch, deployment: str,
) -> None:
    monkeypatch.setenv(ENV_VAR, deployment)
    answer = site.get(HIS)
    assert answer.status_code == 200
    assert answer.content == b"\x89PNG his paper"
    assert site.get(OURS).status_code == 200


def test_they_are_kept_as_long_as_everything_else_vite_hashed(
    site: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """His folder is under assets/ and its names carry a hash, so it gets the
    same immutable caching as the rest of the bundle — not the revalidation an
    unhashed file gets."""
    monkeypatch.setenv(ENV_VAR, "prod")
    assert site.get(HIS).headers["Cache-Control"] == site.get(OURS).headers["Cache-Control"]
    assert "immutable" in site.get(HIS).headers["Cache-Control"]

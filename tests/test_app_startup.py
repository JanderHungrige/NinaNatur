"""The app must stand up its own schema.

Regression: only the ingest CLI created tables, so a freshly deployed container
started against an empty database file and returned 500 to every write. Every
other API test overrides the connection with an already-initialised one, which is
exactly why none of them caught it.
"""
from pathlib import Path

from fastapi.testclient import TestClient

from ninanatur.ingest.db import DB_PATH_ENV
from ninanatur.web.app import app


def test_a_fresh_database_file_serves_requests(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(DB_PATH_ENV, str(tmp_path / "brand-new.sqlite"))
    with TestClient(app) as client:  # `with` runs the lifespan
        created = client.post(
            "/api/v1/gardens",
            json={"name": "Erster Garten", "latitude": 52.5, "longitude": 13.4},
        )
        assert created.status_code == 201, created.text
        token = created.json()["share_token"]
        assert client.get(f"/api/v1/gardens/{token}").status_code == 200


def test_startup_creates_the_database_file_it_was_pointed_at(
    tmp_path: Path, monkeypatch
) -> None:
    target = tmp_path / "nested" / "created.sqlite"
    monkeypatch.setenv(DB_PATH_ENV, str(target))
    with TestClient(app):
        pass
    assert target.exists(), "the directory and file must be created, not assumed"


def test_healthz_answers_before_any_database_work(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(DB_PATH_ENV, str(tmp_path / "x.sqlite"))
    with TestClient(app) as client:
        assert client.get("/healthz").json()["status"] == "ok"


def test_the_spa_mount_never_shadows_the_api_or_the_health_probe() -> None:
    """Route order is the invariant, so assert on route order.

    A StaticFiles mount at "/" with html=True answers *anything* unmatched with
    the SPA shell and a 200. If it were registered before the routers, the deploy
    cron's /healthz probe would start passing on a completely broken app — far
    worse than a 404, and invisible until someone opened the site.
    """
    from starlette.routing import Mount

    routes = list(app.routes)
    root_mounts = [
        index
        for index, route in enumerate(routes)
        if isinstance(route, Mount) and getattr(route, "path", "") == ""
    ]
    if not root_mounts:
        # No bundle built in this checkout — nothing can shadow anything.
        return

    first_mount = min(root_mounts)
    assert first_mount == len(routes) - 1, "the catch-all mount must be the last route"

    # Included routers appear as opaque entries without a `.path`, so identify
    # /healthz by its own path and require everything else to precede the mount.
    healthz = next(
        index for index, route in enumerate(routes)
        if getattr(route, "path", None) == "/healthz"
    )
    assert healthz < first_mount, "/healthz must be matched before the SPA mount"


def test_a_fresh_volume_comes_up_with_a_plant_catalogue(
    tmp_path: Path, monkeypatch
) -> None:
    """Regression: the deployed app answered "0 matching species" to everything.

    The schema was created at startup but the catalogue was not, so a fresh volume
    served a structurally perfect and entirely empty product.
    """
    import sqlite3

    from ninanatur.ingest.catalogue import CATALOGUE_TABLES, seed_catalogue
    from ninanatur.ingest.db import connect, init_schema

    shipped = tmp_path / "catalogue.sqlite"
    builder = connect(shipped, same_thread=False)
    init_schema(builder)
    builder.execute(
        "INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (5, 'Testus', 1)"
    )
    builder.commit()
    builder.close()

    target = tmp_path / "fresh.sqlite"
    conn = connect(target, same_thread=False)
    init_schema(conn)
    assert conn.execute("SELECT COUNT(*) AS n FROM taxon").fetchone()["n"] == 0

    seeded = seed_catalogue(conn, shipped)
    assert conn.execute("SELECT COUNT(*) AS n FROM taxon").fetchone()["n"] == 1
    assert set(seeded) <= set(CATALOGUE_TABLES)
    assert isinstance(conn, sqlite3.Connection)


def test_seeding_never_runs_over_existing_plants(tmp_path: Path) -> None:
    """Seeding over a newer local ingest would silently discard it."""
    from ninanatur.ingest.catalogue import catalogue_is_empty
    from ninanatur.ingest.db import connect, init_schema

    conn = connect(tmp_path / "has-data.sqlite", same_thread=False)
    init_schema(conn)
    conn.execute("INSERT INTO taxon (taxon_id, canonical_name) VALUES (1, 'Vorhanden')")
    conn.commit()
    assert catalogue_is_empty(conn) is False

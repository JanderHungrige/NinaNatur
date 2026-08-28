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

    from ninanatur.ingest.catalogue import CATALOGUE_TABLES, sync_catalogue
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

    seeded = sync_catalogue(conn, shipped)
    assert conn.execute("SELECT COUNT(*) AS n FROM taxon").fetchone()["n"] == 1
    assert set(seeded) <= set(CATALOGUE_TABLES)
    assert isinstance(conn, sqlite3.Connection)


def _shipped(tmp_path: Path, name: str, taxa: list[tuple[int, str]]):
    """A catalogue file as `export-catalogue` would write it, with a build stamp."""
    from ninanatur.ingest.catalogue import VERSION_KEY, export_catalogue
    from ninanatur.ingest.db import connect, init_schema

    builder = connect(tmp_path / f"build-{name}.sqlite", same_thread=False)
    init_schema(builder)
    for taxon_id, canonical in taxa:
        builder.execute(
            "INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (?, ?, 1)",
            (taxon_id, canonical),
        )
    builder.commit()
    dest = tmp_path / f"{name}.sqlite"
    export_catalogue(builder, dest)
    # Make the stamp distinct so two builds are distinguishable within one second.
    out = connect(dest, same_thread=False)
    out.execute("INSERT OR REPLACE INTO catalogue_meta (key, value) VALUES (?, ?)",
                (VERSION_KEY, name))
    out.commit()
    out.close()
    return dest


def test_a_newer_catalogue_reaches_a_database_that_already_has_plants(
    tmp_path: Path,
) -> None:
    """Regression: sync ran only on an empty database, so the insect group
    breakdown shipped in the image and stayed invisible in production."""
    from ninanatur.ingest.catalogue import sync_catalogue
    from ninanatur.ingest.db import connect, init_schema

    first = _shipped(tmp_path, "v1", [(1, "Alte Art")])
    second = _shipped(tmp_path, "v2", [(1, "Alte Art"), (2, "Neue Art")])

    conn = connect(tmp_path / "live.sqlite", same_thread=False)
    init_schema(conn)
    sync_catalogue(conn, first)
    assert conn.execute("SELECT COUNT(*) AS n FROM taxon").fetchone()["n"] == 1

    synced = sync_catalogue(conn, second)
    assert synced, "a different build must be applied"
    assert conn.execute("SELECT COUNT(*) AS n FROM taxon").fetchone()["n"] == 2


def test_the_same_catalogue_is_not_reapplied(tmp_path: Path) -> None:
    """Re-copying 13 MB on every boot would be waste, not safety."""
    from ninanatur.ingest.catalogue import sync_catalogue
    from ninanatur.ingest.db import connect, init_schema

    shipped = _shipped(tmp_path, "v1", [(1, "Art")])
    conn = connect(tmp_path / "live.sqlite", same_thread=False)
    init_schema(conn)
    assert sync_catalogue(conn, shipped)
    assert sync_catalogue(conn, shipped) == {}, "a second sync of the same build is a no-op"


def test_syncing_never_touches_gardens(tmp_path: Path) -> None:
    """The catalogue is the shipped truth; a garden belongs to whoever made it."""
    from ninanatur.garden.store import create_garden, load_garden
    from ninanatur.ingest.catalogue import sync_catalogue
    from ninanatur.ingest.db import connect, init_schema

    conn = connect(tmp_path / "live.sqlite", same_thread=False)
    init_schema(conn)
    garden_id = create_garden(conn, name="Meiner", latitude=52.5, longitude=13.4)

    sync_catalogue(conn, _shipped(tmp_path, "v1", [(1, "Art")]))
    sync_catalogue(conn, _shipped(tmp_path, "v2", [(1, "Art"), (2, "Noch eine")]))

    assert load_garden(conn, garden_id).name == "Meiner"

"""Command-line entry point for the ingest pipeline.

    dbnatura-ingest init
    dbnatura-ingest run gbif|eive|gift|globi|all
    dbnatura-ingest coverage
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from dbnatura.ingest.coverage import compute_coverage, format_report
from dbnatura.ingest.db import DEFAULT_DB_PATH, connect, init_schema
from dbnatura.ingest.sources.eive import EiveSource
from dbnatura.ingest.sources.gbif import GbifSource
from dbnatura.ingest.sources.gift import GiftSource
from dbnatura.ingest.sources.globi import GlobiSource

# GBIF defines the candidate set, so it must run before anything joins against it.
RUN_ORDER = ("gbif", "eive", "gift", "globi")


def run_source(conn: sqlite3.Connection, name: str, limit: int | None) -> int:
    """Dispatch to one adapter. Explicit rather than table-driven: GloBI takes a
    `limit` the others do not, and a shared signature would hide that."""
    if name == "gbif":
        return GbifSource().run(conn)
    if name == "eive":
        return EiveSource().run(conn)
    if name == "gift":
        return GiftSource().run(conn)
    if name == "globi":
        return GlobiSource().run(conn, limit=limit)
    raise ValueError(f"unknown source: {name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dbnatura-ingest", description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite path")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create the schema")

    run = sub.add_parser("run", help="ingest one source or all of them")
    run.add_argument("source", choices=[*RUN_ORDER, "all"])
    run.add_argument("--limit", type=int, default=None, help="cap taxa (GloBI only)")

    sub.add_parser("coverage", help="print the coverage report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    conn = connect(args.db)
    init_schema(conn)

    if args.command == "init":
        print(f"Schema ready at {args.db}")
        return 0

    if args.command == "run":
        names = RUN_ORDER if args.source == "all" else (args.source,)
        for name in names:
            print(f"→ {name}", flush=True)
            rows = run_source(conn, name, args.limit)
            print(f"  {name}: {rows} rows written", flush=True)
        return 0

    if args.command == "coverage":
        print(format_report(compute_coverage(conn)))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())

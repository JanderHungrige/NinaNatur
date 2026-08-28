"""Command-line entry point for the ingest pipeline.

    ninanatur-ingest init
    ninanatur-ingest run gbif|eive|gift|globi|all
    ninanatur-ingest coverage
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from ninanatur.ingest.catalogue import DEFAULT_CATALOGUE, export_catalogue
from ninanatur.ingest.coverage import compute_coverage, format_report
from ninanatur.ingest.db import DEFAULT_DB_PATH, connect, init_schema
from ninanatur.ingest.sources.birds_de import BirdsDeSource
from ninanatur.ingest.sources.eive import EiveSource
from ninanatur.ingest.sources.gbif import GbifSource
from ninanatur.ingest.sources.gift import GiftSource
from ninanatur.ingest.sources.globi import GlobiSource
from ninanatur.ingest.sources.insect_groups import InsectGroupsSource
from ninanatur.ingest.sources.insects_de import InsectsDeSource
from ninanatur.ingest.sources.nativeness import NativenessSource
from ninanatur.ingest.sources.vernacular import VernacularSource
from ninanatur.ingest.summarise import summarise_interactions

# GBIF defines the candidate set, so it must run before anything joins against it.
# insects-de must precede any use of the interaction counts; globi supplies the
# raw relations, insects-de supplies what makes them mean anything here.
RUN_ORDER = (
    "gbif", "eive", "gift", "nativeness", "vernacular",
    "globi", "insects-de", "insect-groups", "birds-de",
)


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
    if name == "birds-de":
        return BirdsDeSource().run(conn, limit=limit)
    if name == "insects-de":
        return InsectsDeSource().run(conn, limit=limit)
    if name == "nativeness":
        return NativenessSource().run(conn, limit=limit)
    if name == "insect-groups":
        return InsectGroupsSource().run(conn, limit=limit)
    if name == "vernacular":
        return VernacularSource().run(conn, limit=limit)
    raise ValueError(f"unknown source: {name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ninanatur-ingest", description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite path")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create the schema")

    run = sub.add_parser("run", help="ingest one source or all of them")
    run.add_argument("source", choices=[*RUN_ORDER, "all"])
    run.add_argument("--limit", type=int, default=None, help="cap taxa (globi, insects-de)")

    sub.add_parser("coverage", help="print the coverage report")
    sub.add_parser("summarise", help="rebuild the partner aggregates")

    export = sub.add_parser("export-catalogue", help="write the runtime catalogue")
    export.add_argument("--out", type=Path, default=DEFAULT_CATALOGUE)
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
        if args.source == "all":
            # The aggregates are the intersection of globi and insects-de, so they
            # are only meaningful once both have run.
            print(f"→ summarise: {summarise_interactions(conn)} plants", flush=True)
        return 0

    if args.command == "summarise":
        print(f"summarised {summarise_interactions(conn)} plants")
        return 0

    if args.command == "export-catalogue":
        counts = export_catalogue(conn, args.out)
        size_mb = args.out.stat().st_size / 1048576
        for table, n in counts.items():
            print(f"  {table:<18} {n:>7}")
        print(f"wrote {args.out} ({size_mb:.1f} MB)")
        return 0

    if args.command == "coverage":
        print(format_report(compute_coverage(conn)))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())

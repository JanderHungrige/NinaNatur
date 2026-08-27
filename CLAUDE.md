# CLAUDE.md — NinaNatur

Garden planning on open plant-trait data: lay out a garden as beds, get native
plant suggestions that fit the site, simulate the bloom year, find bloom gaps,
score the planting for insects, and consolidate the order across as few
nurseries as possible.

## Stack

- **Backend/ML → Python 3.11+**, full type hints, `ruff` + `mypy --strict`
- **Data store:** SQLite (one schema module, `ninanatur/ingest/db.py`)
- **API (planned):** FastAPI under `/api/v1/`
- **Frontend (planned):** React + TypeScript, strict mode, no `any`

## Data sourcing — the rule that shapes this project

Every trait value in the database carries `source`, `license`, `confidence` and
`retrieved_at`. There is exactly one write path (`provenance.upsert_trait`) and
it raises on missing provenance. This is not bookkeeping: it is what lets the UI
cite any number it shows, and what keeps the licence position defensible.

- **Only openly licensed sources.** Currently EIVE 1.0 (CC-BY-4.0), GBIF
  (CC-BY-4.0), GIFT (CC-BY-4.0), GloBI (CC0).
- **Never scrape NaturaDB or any comparable curated database.** German database
  rights (§§ 87a-e UrhG) protect the compiled dataset independently of
  `robots.txt`, and their `robots.txt` blocks AI agents outright. Licensed
  access via agreement is the only route to that data.
- **Sources never overwrite each other.** The `trait` primary key includes
  `source`, so disagreement persists and is resolved at read time, visibly.

## Ingest rules

- Adapters implement `Source.run(conn) -> int` and write only through
  `upsert_trait` / `record_interaction`.
- All HTTP goes through `ingest/http.py`: disk cache, delay, retry with backoff.
  A rerun of the pipeline must cost zero API calls.
- **Check every API for silent truncation.** GIFT caps responses at 10,000 rows
  and returns a short page rather than an error — paging is correctness, not
  performance. Assume any undocumented list endpoint does the same.
- Name resolution is the join key. Resolve in cost order: per-source cache →
  local `canonical_name` → GBIF match API. A match below confidence 90, of type
  `NONE`/`HIGHERRANK`, or above species rank must not carry traits.

## Quality gates

- No file > 300 lines, no function > 50 lines.
- `ruff check`, `mypy --strict`, `pytest` all clean before a commit.
- Tests assert behaviour, not execution. "It runs" is not a criterion.
- Never swallow errors: log with context before re-raising.

## Never

- Never commit `data/raw/`, `data/cache/`, `*.sqlite`, or `.env`.
- Never scrape a source without checking `robots.txt` **and** its licence.
- Never write a trait value without provenance.

## Workflow

- MDD: `/mdd <feature>` — doc first, then tests, then code.
- Branch per feature; never commit directly to `main`.

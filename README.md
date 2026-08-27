# NinaNatur

Garden planning on openly licensed plant data — native species matched to the
site, a bloom calendar for the year, and a measurable insect score.

**Live:** https://ninanatur.w3rth.de

## Run locally

```bash
python -m uvicorn ninanatur.web.app:app --reload --port 4000
```

## Deployment

Push to `main` → GitHub Actions builds and pushes `ghcr.io/janderhungrige/ninanatur:main`
→ the host's cron `deploy/auto-deploy.sh` pulls and rolls the container.
CI never SSHes into the host. See [deploy/SERVER-SETUP.md](deploy/SERVER-SETUP.md).

| Branch | Image tag | Host port |
|---|---|---|
| `main` | `:main` | 4000 (prod) |
| `dev-deployment` | `:dev` | 4001 (dev) |


## Ingest pipeline

```bash
python -m ninanatur.ingest.cli run all
python -m ninanatur.ingest.cli coverage
```

Sources, in run order:

| Source | Supplies | Licence |
|---|---|---|
| GBIF | taxonomy backbone, German candidate set | CC-BY-4.0 |
| EIVE 1.0 | light, moisture, nutrients, pH, temperature (0–10) | CC-BY-4.0 |
| GIFT | height, flowering window, colour, growth/life form | CC-BY-4.0 |
| GloBI | pollinators, flower visitors, herbivores | CC0-1.0 |

Every value stored carries its source, licence and retrieval date.

## Development

```bash
python3.13 -m venv .venv && .venv/bin/pip install -e . pytest ruff mypy
.venv/bin/python -m pytest -q && .venv/bin/ruff check . && .venv/bin/mypy ninanatur
```

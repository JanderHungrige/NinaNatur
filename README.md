# NinaNatur

Open-data plant trait database for insect-friendly garden planning.

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

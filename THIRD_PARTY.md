# Third-party material

## Draft Sketch, by Warren Davison

The garden plan's Draft Sketch theme is derived from **Draft Sketch**, an
ArcGIS Pro style by Warren Davison, created with assistance from Louis Hill
(@NKYmapLAB).

**Permission.** Warren Davison's written permission of **2026-09-10**: to use
and adapt Draft Sketch in NinaNatur, including this public repository and
commercial use.

**Credit**, shown beneath the plan whenever it is drawn in his style:

> Zeichenstil nach Draft Sketch von Warren Davison, verwendet und angepasst mit
> seiner Erlaubnis · with assistance from Louis Hill (@NKYmapLAB)

**Source.** ArcGIS Online item `3215e720f62d42008d125ca1a3219b14` (owner
WarrenDz, last changed 2021-01-13), the file `Draft_Sketch.stylx`: 17,096,704
bytes, SHA-256 `4ef38ef87e9e6d6c7bb4f2c3ef94988456599b88ac1a3d7959ae861787668ac6`,
pinned in `assets/draft-sketch/source.json`. The file itself is not in this
repository; `python -m scripts.stylx_to_theme --fetch` downloads it and refuses
any other.

**What is his, what is adapted, and what is ours.** Every file of marks says
so in its first comment, in one of four agreed forms, and a test refuses one
that does not (`tests/test_theme_provenance.py`):

| Where | What | Provenance |
|---|---|---|
| `frontend/src/themes/draft-sketch/generated/images/` | his images, unchanged | Warren Davison (Draft Sketch) |
| `frontend/src/themes/draft-sketch/generated/symbols.ts` | his symbols' fills, as SVG patterns | Warren Davison (Draft Sketch) |
| `frontend/src/themes/draft-sketch/generated/rules.ts` | what his symbols draw along a shape, adapted to SVG | adapted from Draft Sketch |
| `frontend/src/themes/draft-sketch/ours/` | roof lines, raised beds' edges, a hedge's hatch, north arrow, scale bar and title block — ours, in his manner | NinaNatur, in the style of Draft Sketch |

The generated files are derived from his file by `scripts/stylx_to_theme.py`
and never edited by hand; `--check` proves they still are (doc 97).

# geokachel

**Official German open elevation, surface, building and point-cloud data — one
interface, all sixteen Bundesländer, with the credit each licence requires.**

Germany publishes superb elevation data and publishes it sixteen different
ways. Every state runs its own surveying office, and they agree about almost
nothing: where the UTM zone goes in a filename, whether a tile is one kilometre
or two, whether a grid starts on an even easting or an odd one, whether you get
a GeoTIFF or a million lines of text, whether there is a tile to address at all
or only a twelve-gigabyte regional archive.

This is one interface over all of it, plus a record of which requests were
actually answered, and when.

```bash
pip install geokachel
```

```python
from geokachel import ground_tiles_for, read_raster, net

source = ground_tiles_for("BY")
print(source.attribution)
# Datenquelle: Bayerische Vermessungsverwaltung – www.geodaten.bayern.de

url = source.url_for(690, 5334)          # UTM32 kilometres, Munich
raster = read_raster(net.get_bytes(url))  # 1000 x 1000 metres of ground
```

## What is in it

| | states | what you get |
|---|---|---|
| **Ground** (DGM1) | **16 — all of them** | 1 m terrain, ±10–30 cm |
| **Surface** (DOM / nDOM / bDOM) | 15 | what stands on it, 0.2–1 m |
| **Buildings** (LoD2 CityGML) | 13 | measured height *and* surveyed roof shape |
| **Point clouds** (LAZ) | 7 | the returns themselves, 4–20 pts/m² |

Plus Copernicus GLO-30 as a worldwide fallback, and the sixteen state coverage
services (WCS) where a state runs one.

## Three rules it keeps

**An entry is a request that was answered**, dated — never a portal page that
says a thing exists. Every entry records the tile it was verified at and the
bytes that came back, which is what makes `geokachel check` possible.

**A credit is a licence obligation, not a caption.** `dl-de/by-2-0` and
`CC BY 4.0` both require a named credit. A height displayed without it is a
height used outside its licence, so `attribution` is a required field on every
source and carries the publisher's exact wording. A source whose licence
forbids this kind of use is not in the registry at all. See [NOTICE](NOTICE).

**A gap is a gap.** No state borrows its neighbour's ground, and nothing
unsurveyed is guessed at: it is `NaN`, and it says so.

## Three ways a tile has an address

Handled behind one function, because a caller should not have to care:

- **computed** — the name is arithmetic on two UTM kilometre numbers. Most
  states. A tile's address is a template and two integers, never a lookup.
- **listed** — the name carries a survey year (2005 in one tile, 2025 in its
  neighbour), so the state's own index is read once. What is taken out of it is
  a *file name*; the scheme, the host and the shape of the address stay ours,
  so a compromised index cannot redirect a fetch.
- **archived** — the state publishes no tile at all, only 0.5–12.5 GB regional
  archives. A zip keeps its index at its **end**, so one member comes out over
  HTTP range requests: **0.38 % of a 559 MB file**, measured.

## Checking that it is all still there

States move their files. In the two days this registry was built, four of them
changed underneath it — one moved host entirely, one still lists tiles that
404, one carries dead share tokens, and one answers a stale row with **HTTP 200
and an HTML apology**. A checker that read status codes would have called all
four healthy.

```bash
geokachel check              # every source, a few kB each, ~2 minutes
geokachel check sn- rp-      # just these
geokachel check --quiet      # only what is wrong; exit 1 if anything is
geokachel credits BY TH      # the exact credit those states require
```

A source passes only when the bytes are what it claims — `II*` for a TIFF,
`LASF` for a cloud, a root element for CityGML, numbers for a text grid, a
directory that still holds the square kilometre it held before.

It is deliberately **not** a test suite: one that needs sixteen state portals
to be up fails on their maintenance window and teaches people to ignore red.
It is a command with an exit code, meant for a scheduled job.

## What it deliberately does not do

**It does not choose your coordinate frame.** You get a north-up raster in the
source's own UTM with `NaN` for unknown. Putting that on your own axes is
yours, because the right answer differs for a shadow model, a flood model and a
map — and because UTM grid north is up to 2.3° off true north in Germany, which
some callers must correct for and others must not.

**It does not geocode.** `state=` is a required argument. A library that
reverse-geocoded every call would rate-limit whoever looped over ten thousand
plots, and that is not a failure to inflict from inside a dependency.

**It does not fetch anything itself.** Every function that needs bytes takes a
callable. `geokachel.net` is a polite default — a pause between requests, a
size cap, a User-Agent — and you should set `geokachel.net.USER_AGENT` to
something with your own contact in it before pulling anything in anger. These
are public offices publishing at their own expense.

## Installing

Requires Python 3.11+. Depends on `numpy`, `defusedxml` and `requests` — no
GDAL, no rasterio, no pyproj. The GeoTIFF reader and the UTM projection are
both here, because a hundred-megabyte wheel to read a single-band raster is a
poor trade.

## Licence

MIT, for the software. The *data* is somebody else's and carries its own terms
— read [NOTICE](NOTICE) before you publish anything derived from it.

Not affiliated with any Landesvermessungsamt, the AdV, the BKG, ESA or
Copernicus. Their names appear only inside the credits their licences require.

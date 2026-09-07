---
id: ninanatur-wave-20
title: "Wave 20: Nothing here is worse than it looks"
initiative: ninanatur
initiative_version: 20
status: planned
depends_on: ninanatur-wave-19
demo_state: "Ein geschriebener Prüfbericht über Web- und Anwendungssicherheit, jede Feststellung mit dem Ort im Code und einem Reproduktionsweg; die Befunde behoben und durch Tests festgehalten, die den Angriff selbst versuchen. Die Abhängigkeiten sind auf bekannte Schwachstellen geprüft, und CI bricht ab, wenn eine neue dazukommt."
created: 2026-09-07
hash: 41b76d01
---

# Wave 20: Nothing here is worse than it looks

## Demo-State

Ein geschriebener Prüfbericht über Web- und Anwendungssicherheit, jede
Feststellung mit dem Ort im Code und einem Reproduktionsweg; die Befunde behoben
und durch Tests festgehalten, die den Angriff selbst versuchen. Die
Abhängigkeiten sind auf bekannte Schwachstellen geprüft, und CI bricht ab, wenn
eine neue dazukommt.

*(This wave is not complete until this can be manually demonstrated.)*

## Why now

Nineteen waves have added surface. There is a public site with accounts and
sessions, a share token that *is* the access-control model, an API that takes
polygons and addresses from anyone who asks, a container that deploys itself
from a cron line every minute, and outbound calls to half a dozen state survey
services. None of that has ever been looked at as a whole with the question
"what can somebody do to this that they should not be able to do".

That is the wave. Not a feature — a review, and then the fixes it names.

**The one thing to say plainly before it starts:** this is an audit of *this*
application, by the people who own it, on their own infrastructure. Nothing in
it is a technique for use against anything else.

## Scope, provisionally

Detailed planning comes next; this is the shape of it, so that the scope is
agreed before the work rather than discovered during it.

- **The share token as the whole access model.** Anyone holding it can edit the
  garden. That was a deliberate decision (`docs/08-garden-model.md`) and it has
  never been examined against how the token is generated, transported, logged
  and leaked — a `Referer` header, a browser history, a screenshot.
- **Accounts and sessions.** Cookie flags, session lifetime, fixation, what a
  sign-out actually ends, and what an account owns after it.
- **Input, everywhere it is taken.** Polygons with five hundred points, coordinates
  outside the planet, a garden name the length of a novel, JSON that parses and
  then means something else. The API validates a lot of this already; the
  question is where it does not.
- **Injection, in both directions.** Every query in this project is
  parameterised and polygon JSON is parsed rather than evaluated — worth
  *verifying* rather than restating. And the other direction: what reaches the
  browser as markup, and what reaches an SVG.
- **The outbound half.** This app fetches from Nominatim, Overpass, eight state
  WCS services and NRW's LoD2 store, and parses what comes back — XML, GML,
  GeoTIFF. A hostile response to any of those is a live parser question, and
  `geo/tiff.py` is a hand-written binary reader.
- **Dependencies.** A lockfile audit, in both ecosystems, and a CI gate so the
  answer stays true.
- **The deployment path.** A cron that pulls and rolls a container every minute,
  a registry that is public, `.env` files that are not in git, and the
  `SERVER-SETUP.md` steps nobody has been able to run yet.
- **What the app tells the world about itself.** Headers, error bodies, the
  version badge, `/healthz`, and whether a 404 and a 403 are distinguishable
  where they should not be.

## What is deliberately not in it

- Anything aimed outward. No scanning, no probing of hosts this project does not
  own, no third-party services.
- A rewrite of the share-token model. If the review says it should change, that
  is a wave of its own with a migration; this one names it.
- Penetration testing of the host by a third party. Worth doing, not doable from
  here.

## Open questions for planning

- Is the review a document that lives in `.mdd/docs/`, or an audit report under
  `.mdd/audits/` — which is gitignored and therefore ephemeral?
- Does a finding get a failing test first, the way a bug does?
- How much of this can be a CI gate that keeps holding afterwards, rather than a
  one-off reading?

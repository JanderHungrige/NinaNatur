---
id: ninanatur-wave-18
title: "Wave 18: A place to look before it is live"
initiative: ninanatur
initiative_version: 20
status: planned
depends_on: ninanatur-wave-17
demo_state: "Ein Merge auf dev-deployment erscheint binnen einer Minute unter einer eigenen Adresse auf Port 4001, mit eigener Datenbank und sichtbar als Vorschau gekennzeichnet. Erst was dort in Ordnung ist, geht auf main — und main deployt weiter wie bisher."
created: 2026-09-04
hash: d2ab7efe
---

# Wave 18: A place to look before it is live

## Demo-State

Ein Merge auf `dev-deployment` erscheint binnen einer Minute unter einer eigenen
Adresse auf Port 4001, mit eigener Datenbank und sichtbar als Vorschau
gekennzeichnet. Erst was dort in Ordnung ist, geht auf `main` — und `main`
deployt weiter wie bisher.

*(This wave is not complete until this can be manually demonstrated.)*

## Why now

Everything built so far went from a feature branch straight to production. That
has been survivable because the suite is thorough and the deploy is a minute —
but three things this month were found only by looking at the running site, and
one of them (a colour that never committed) was found in production, by writing
into it.

The half of this that already exists is the trap. `deploy.yml` names
`dev-deployment`, tags the image `:dev` and comments a stack on 4001;
`.env.dev.example` sets `COMPOSE_PROJECT_NAME=ninanatur-dev` and `APP_PORT=4001`.
None of it is real: there is no `dev-deployment` branch, no dev domain, no
second stack. A workflow that names an environment nobody has is worse than one
that does not, because it reads as though the environment is there.

## What it is

- **The branch.** `dev-deployment` exists and is where a wave goes first. Merging
  it into `main` is what makes something live. The CI already builds and tags
  from it.
- **The stack.** A second compose stack on the host with `--env-file
  deploy/.env.dev`, its own port and — the part that matters — **its own named
  volume**. `COMPOSE_PROJECT_NAME` already scopes it; the wave has to prove that
  rather than assume it, because sharing the volume would mean testing a
  migration against real gardens.
- **The cron.** `auto-deploy.sh` runs once per environment. Today's crontab has
  one line; it needs the second, and the lock has to be per environment or a
  slow prod pull will starve dev forever.
- **The address.** A subdomain through Nginx Proxy Manager, the way production
  already goes.
- **Saying which is which.** The two pages are identical. A preview that looks
  exactly like the live site is a way to enter a garden on the wrong one and
  lose it. The header must say so, unmistakably, from `NINANATUR_ENV` — which
  already exists and is already passed in and is currently used for nothing.

## Open Research

- **What the feedback box does on dev.** It files GitHub issues. From a preview
  it should either not file at all or file with a label saying where it came
  from — otherwise every test of the button is a real issue in the tracker.
- **Whether dev gets its own catalogue.** It runs the same image, so it has the
  same shipped catalogue — which is right. But hand-entered colours are shared
  catalogue rows now, and a preview writing them means a test entry answers for
  everybody. This is the first feature where the two environments are not
  independent, and it needs deciding rather than discovering.
- **Whether the cron should pull dev at all**, or whether a preview is better
  rolled by hand. Automatic is more useful and one more thing to go wrong at
  three in the morning.

## Deliberately not in this wave

A staging copy of production data. Dev starts empty and stays empty, which is
also the state a migration is least tested against — `sync_catalogue` seeding a
fresh volume is exactly the case CLAUDE.md says to check by hand against an
empty volume, and that check stays manual.

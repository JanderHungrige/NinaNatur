---
id: 30-landing-and-garden-id
title: A Front Door, and a Way Back In
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-7
wave_status: queued
depends_on: [26-drawing-canvas]
relates: [13-garden-api]
source_files:
  - frontend/src/App.tsx
  - frontend/src/components/Landing.tsx
  - frontend/src/components/GardenId.tsx
routes: []
models: []
test_files:
  - frontend/src/components/Landing.test.tsx
  - frontend/src/components/GardenId.test.tsx
data_flow: reads-existing
last_synced: 2026-08-28
status: planned
phase: "1"
mdd_version: 11
tags: [landing, entry, share-token, garden-id, onboarding]
path: UI/Entry
integration_contracts:
  - function: garden.share_token
    when: a user needs to return to a garden without an account
    note: the token is the credential, not a lookup key — it goes in the URL fragment and nowhere else
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 30 — A Front Door, and a Way Back In

**Queued: to be built after Wave 7's four features are merged.** Requested during
Wave 7 planning; recorded here so it is not carried in someone's head.

## Purpose

The app currently opens straight into a garden form. Wave 1 had a landing page —
the hero, the three data figures, the sources line — and it was liked. It comes
back, and it becomes the place where a user chooses **which** garden they are
working on.

## What it shows

The Wave 1 elements, unchanged in spirit: *"Ein Garten, der etwas ernährt."*, the
lede, the three figures, and the licence footer. The figures are read from the
API rather than hardcoded, since they were already stale — Wave 1 wrote 3.087
species into the HTML by hand.

Below them, two ways in:

1. **Neuen Garten anlegen** — the existing form.
2. **Garten mit ID laden** — paste an ID, land in that garden.

## When it appears

- On a fresh load with no garden in the URL.
- On clicking the NinaNatur logo, from anywhere. The logo becomes the way home,
  which is what people already try.

Leaving a garden must not lose it: clicking the logo goes to the landing page,
and the garden is still reachable by its ID, which is exactly why the ID has to
be visible *before* someone clicks.

## The ID, until there are accounts

While designing a garden, the ID sits at the top with a copy button and one
sentence: this is how you get back to this garden — keep it.

Wave 9 brings accounts. Until then this is the only way back, so it cannot be
something a user has to know to look for in the address bar.

## Security: this is a credential, not a lookup key

`share_token` is `secrets.token_urlsafe` and it is the **only** thing standing
between a stranger and someone's garden. Whoever holds it can edit and delete.
That has consequences the UI must respect:

- **It stays in the URL fragment.** Never a query parameter, never a path
  segment — a fragment is not sent to the server, so it stays out of access
  logs, and it is not sent as a referrer to any third party. This is already how
  the app carries it; the "load by ID" field must not quietly change that by
  submitting a form.
- **The wording says what it means.** "Wer diese ID hat, kann deinen Garten
  ändern" — calling it an ID is right for the user, but it must not read like a
  harmless row number.
- **Never logged, never sent anywhere else**, including analytics or error
  reports.

## Business Rules

- **An unknown or malformed ID says so plainly** and returns to the landing page
  with the field still filled. It must not look like an empty garden.
- **The copy button degrades.** `navigator.clipboard` needs a secure context and
  permission; when it fails the ID stays selectable text and the UI says copying
  did not work rather than silently doing nothing.
- **The figures come from the API.** A landing page that states a species count
  is making a claim, and a hardcoded one is wrong the first time the catalogue
  is rebuilt.

## Known Issues

(none yet)

## Bugs

(none yet)

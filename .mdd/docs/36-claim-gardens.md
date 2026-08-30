---
id: 36-claim-gardens
title: Keeping the Gardens You Already Made
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-9
wave_status: complete
depends_on: [35-accounts]
relates: [09-garden-api, 30-landing-and-garden-id]
source_files:
  - ninanatur/api/gardens.py
  - ninanatur/api/accounts.py
  - frontend/src/App.tsx
routes:
  - POST /api/v1/gardens/{token}/claim
  - GET /api/v1/accounts/me/gardens
models:
  - garden
test_files:
  - tests/test_claim_gardens.py
data_flow: writes-existing
last_synced: 2026-08-30
status: complete
phase: all
mdd_version: 11
tags: [ownership, share-token, accounts, migration]
path: Auth/Ownership
integration_contracts:
  - function: garden.owner_id
    when: a logged-in user claims a garden from its share link
    note: share links keep working afterwards — the account keeps the links, it does not replace them
satisfies_contracts:
  - from: 09-garden-api
    function: garden.owner_id
    when: accounts exist
    status: done
    verified_at: "ninanatur/api/gardens.py::claim"
security_read_sites:
  - ninanatur/api/gardens.py::claim
known_issues: []
sister_projects: []
---

# 36 — Keeping the Gardens You Already Made

## Purpose

Wave 3 chose share links and put a nullable `owner_id` on `garden` in the very
first migration, so that when accounts arrived this would cost one column rather
than a migration of live plans. This is where that decision pays.

A logged-in user opening a share link can claim that garden, and the account
lists what it holds.

## Share links keep working

Removing them to push registration would be a downgrade dressed as a feature.
After a claim:

- the link still opens the garden,
- a stranger holding it can still edit — that was Wave 3's bargain and it stands,
- **and it can still delete the garden.**

The last one is deliberate and follows from the optional email: account loss is
expected here, not exceptional. A garden that could only be deleted by an account
nobody can reach is a garden nobody can delete.

What the link does *not* do is take a garden from whoever claimed it.

## Business Rules

- **Claiming an already-claimed garden is a 409**, not a takeover.
- **Claiming your own garden twice is fine** — it is the same state, and an error
  there would be pedantry.
- **The list carries the share token**, because that is still what opens a
  garden. The account is a place to keep the links, not a replacement for them.
- **One account never sees another's gardens.**

## Known Issues

- **No un-claiming.** Giving a garden away, or letting it go, has no route yet.
- **The list is not paginated.** Fine for the number of gardens a person makes;
  worth revisiting if that assumption ever stops holding.

## Bugs

(none)

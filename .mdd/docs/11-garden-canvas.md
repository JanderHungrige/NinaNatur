---
id: 11-garden-canvas
title: Garden Canvas Editor
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-3
wave_status: complete
depends_on: [10-web-client]
relates: [09-garden-api, 02-web-shell]
source_files:
  - frontend/index.html
  - frontend/src/plural.ts
  - frontend/vite.config.ts
  - frontend/src/main.tsx
  - frontend/src/App.tsx
  - frontend/src/components/GardenCanvas.tsx
  - frontend/src/components/BedPanel.tsx
  - frontend/src/components/NewGardenForm.tsx
  - frontend/src/styles.css
  - Dockerfile
  - ninanatur/web/app.py
routes:
  - GET /
test_files:
  - frontend/src/components/GardenCanvas.test.tsx
data_flow: reads-existing
last_synced: 2026-08-28
status: complete
phase: all
mdd_version: 11
tags: [react, canvas, svg, accessibility, editor]
path: Frontend/Canvas
integration_contracts: []
satisfies_contracts:
  - from: 10-web-client
    function: NinaNaturClient
    when: any call to the backend from the UI
    status: done
    verified_at: "frontend/src/App.tsx:9"
security_read_sites: []
known_issues: []
sister_projects: []
---

# 11 — Garden Canvas Editor

## Purpose

Draw a garden: beds as polygons, obstacles as circles with heights, soil per bed.
Every change that affects light goes back to the server, which recomputes it.

## Why SVG rather than `<canvas>`

Each bed and obstacle is a real DOM element. That means it can carry a title, be
reached by tab, be styled by CSS and be found by a test — none of which a
`<canvas>` bitmap offers without rebuilding all of it by hand. The scene here is
tens of shapes, not thousands, so the performance argument for `<canvas>` does
not apply.

## Accessibility

Drawing is where keyboard access usually gets dropped, so it is decided here
rather than retrofitted:

- **Every action has a non-pointer path.** Beds and obstacles can be added by
  typing coordinates into a form, not only by clicking. The form is the primary
  interface; the canvas is a faster way to reach the same thing.
- **Each shape is a focusable element with an accessible name** — "Bed
  Südbeet, 4 by 2 metres, 6.4 sun hours" rather than an anonymous `<path>`.
- **The canvas is not the only place state is visible.** A bed list mirrors
  everything, so nothing is only knowable by looking at the picture.
- **Focus is never removed**, and status changes are announced through a live
  region rather than only by a shape changing colour.

## Deployment change

The Dockerfile gains a Node stage that builds `frontend/dist`, which FastAPI then
serves. **This is the first change to a deployment path that currently works, and
there is no Docker on the dev machine to verify it** — CI is the first real test,
so the risk is stated rather than assumed away.

The API keeps its `/api/v1` prefix and `/healthz` stays untouched, so the deploy
cron's health probe is unaffected by the frontend either way.

## Business Rules

- **Unknown light renders as "not yet computed", never as 0 h.** Same rule as
  every layer beneath it.
- **The share token lives in the URL fragment**, so it is not sent to the server
  in a Referer header when the user follows an outbound link.
- **Adding an obstacle re-renders from the server's response**, not from local
  optimism — the light values only the server can compute must not be guessed at
  in the client.

## Known Issues

- Beds are added as rectangles from a coordinate form. Free-hand polygon drawing
  on the canvas is not implemented — the shapes render and are selectable, but
  cannot yet be reshaped by dragging.
- Beds and obstacles cannot be edited or deleted, only added. Needs the `PATCH`
  and `DELETE` endpoints noted in `09-garden-api`.
- The plant suggestions from Wave 2 are not wired into a selected bed yet; the
  client method exists and is typed, but nothing calls it.

## Verified in the running app

Garden created, bed added showing "noch nicht berechnet", obstacle added, server
recomputed to 5.8 h/day (L 6), page reloaded from the share fragment with
everything intact. The production serving shape was checked separately by copying
the built bundle in: `/healthz` still returns JSON rather than the SPA shell.

## Bugs

(none yet)

---
id: ninanatur-wave-13
title: "Wave 13: A front door that looks like one"
initiative: ninanatur
initiative_version: 17
status: complete
depends_on: ninanatur-wave-12
demo_state: "Somebody arriving at ninanatur.w3rth.de finds sign-in where every site puts it, one obvious way in, a note saying an account is optional but worth having — and a page that breathes"
created: 2026-08-31
hash: 7fd640aa
---

# Wave 13 — A front door that looks like one

## Demo-State

Somebody arriving at ninanatur.w3rth.de finds sign-in where every site puts it,
one obvious way in, a note saying an account is optional but worth having — and
a page that breathes.

*(This wave is not complete until this can be manually demonstrated.)*

## Why this wave exists

The landing page has not been looked at since Wave 7 put it back. Since then it
has grown a third way in, an account panel in the middle of the page, and a
layout bug that only showed on a wide window.

## What was already fixed, before planning

**The landing page was rendered inside the garden's two-column grid.** Above the
breakpoint it was handed the 22rem sidebar column: 352 px of landing page on a
1600 px window, and correct again only when the window was made *smaller*.

The same shape as the bug fixed in V0.12.20, in the one place that fix did not
look. It is out of the grid now — 992 px at 1600, 846 at 900 — and the guard is
on the markup rather than the CSS, because whichever way it is solved one
element must not be both. That is why it is not a feature below.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | account-in-header | .mdd/docs/53-account-in-header.md | complete | — |
| 2 | one-way-in | .mdd/docs/54-one-way-in.md | complete | 53 |
| 3 | living-background | .mdd/docs/55-living-background.md | complete | — |

### 1 — account-in-header

Sign-in and sign-up move to the top right, where every site puts them and where
people look without being told. The account panel comes out of the middle of the
page.

**A curved arrow to the sign-up button**, with a line saying an account is not
needed but is the better way to keep a garden. That is the truth of it: the
share token already works, and it is a link somebody has to not lose.

The arrow is drawn, not an emoji — the plan is already a watercolour and a
hand-drawn arrow belongs to it. It is decoration, so it is `aria-hidden`, and the
sentence beside it carries the whole meaning on its own.

### 2 — one-way-in

Three equal boxes suggest three equal choices. There is one: start from the map.

*Garten öffnen* stays beside it, because it is not a way of making a garden but
of coming back to one. **"Ohne Karte anfangen" becomes a quiet link underneath**
— decided with the user over removing it. Nominatim and Overpass are free
services with no SLA, and without that link a bad afternoon at either one leaves
nobody able to start at all.

### 3 — living-background

Slowly drifting leaves and seed heads in the palette the plan already uses.

**CSS transforms only, no animation loop.** A `requestAnimationFrame` loop on a
landing page runs until the tab is closed; transforms are composited and cost
nothing measurable.

**`prefers-reduced-motion: reduce` stops it entirely** — not slows it. That was
promised in feature 41 and this is the first thing on the site that actually
moves, so it is the first time the promise costs anything.

It sits behind the content at low contrast and is `aria-hidden`. A background
that competes with the words in front of it is a background that failed.

## Risks

- **A moving background is the easiest thing to overdo.** The measure is whether
  the page is still readable with it — and the honest check is looking at it,
  not asserting on it.
- Moving sign-in to the header means it is no longer explained by the text
  around it. The arrow and its sentence are what replace that explanation, so
  they are part of feature 1 rather than a nicety.

## Open Research

- [x] Does the arrow survive a narrow window, where the header wraps and the
      button it points at moves? A drawn arrow pointing at nothing is worse than
      no arrow.

## Definition of done

Sign-in is top right, one way in is obvious with the others still reachable, and
the background moves — and stops when the system asks for less motion.


## What this wave cost the site

Almost nothing to run, and one promise finally came due.

Feature 41 said `prefers-reduced-motion` would be respected. Nothing on the site
moved, so the promise had been free for three waves. The drifting leaves are the
first thing that does, and the rule that stops them is guarded by a test rather
than by the memory of having meant it.

The open research question is answered in feature 53: the arrow travels inside
the sentence, immediately before the button, rather than pointing across the
header at a fixed spot — which is what would have failed the moment the header
wrapped.

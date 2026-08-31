---
id: 53-account-in-header
title: Signing In, Where Sites Put It
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-13
wave_status: complete
depends_on: [36-accounts]
relates: [54-one-way-in, 30-landing-and-garden-id]
source_files:
  - frontend/src/components/AccountBar.tsx
  - frontend/src/App.tsx
  - frontend/src/components/Landing.tsx
routes: []
models: []
test_files:
  - frontend/src/components/AccountBar.test.tsx
data_flow: reads-existing
last_synced: 2026-08-31
status: complete
phase: all
mdd_version: 11
tags: [accounts, header, landing, accessibility]
path: Landing/Account
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
---

# Signing in, where sites put it

## What this is

*Anmelden* and *Konto anlegen* in the top right. The account forms open from
there instead of sitting in the middle of the landing page between two ways of
making a garden.

## Decisions

### The invitation is a sentence, and the arrow is decoration

*"Ein Konto ist nicht nötig — aber es hält deine Gärten zusammen, auch wenn du
den Link verlierst."* That is the truth of it: the share token already works,
and it is a link somebody has to not lose.

The arrow is drawn rather than an emoji, because the plan is already a
watercolour. It is `aria-hidden`, and the sentence carries the whole meaning —
so the invitation is not something only sighted users receive. `aria-describedby`
ties the sentence to the button it is about, which is what the arrow does
visually.

### The arrow points from beside, not across

The wave's open research question. A drawn arrow aimed at a fixed spot points at
nothing the moment the header wraps on a narrow window, so it sits inside the
note, immediately before the button. **Answered: it travels with the sentence.**

### The invitation only appears on the front door

Inside a garden the bar is a way out, not a pitch, and somebody already signed
in is not invited to sign up.

## Definition of done

Sign-in is top right on every page, the note and arrow appear only to a signed-out
visitor on the landing page, and the account panel is gone from the page body.

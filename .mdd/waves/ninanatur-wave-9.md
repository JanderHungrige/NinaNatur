---
id: ninanatur-wave-9
title: "Wave 9: Standing in the garden, and keeping it"
initiative: ninanatur
initiative_version: 10
status: planned
depends_on: ninanatur-wave-8
demo_state: "A user places themselves on the plan and sees what is actually visible from there, and can keep their gardens under an account without giving an email address"
created: 2026-08-28
hash: 251a4530
---

# Wave 9 — Standing in the garden, and keeping it

## Demo-State

A user places themselves on the plan and sees what is actually visible from
there, and can keep their gardens under an account without giving an email
address.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | sightlines | 34-sightlines | planned | — |
| 2 | accounts | 35-accounts | planned | — |
| 3 | claim-gardens | 36-claim-gardens | planned | 34 |

### 1 — sightlines (#8a)

Place a viewpoint on the plan and compute what is visible from it, using bed
height above ground and plant height: a ground cover behind a shrub is hidden, a
raised bed in front of a border is not.

The same geometry the sun uses, from a different origin — eye height instead of
solar altitude. Wave 7's *height above ground* per bed exists for this, and
Wave 8's object heights carry their confidence into it: **a sightline computed
from an estimated building height must not be drawn as though it were surveyed.**

Design value beyond the novelty: it turns "will I actually see this plant" from a
guess into an answer, which is the question that decides where things go.

### 2 — accounts (#3)

Registration with a username and password. **Email is optional**, and the
consequence is stated at the point of choosing, not buried:

> Ohne E-Mail-Adresse kann dein Passwort nicht zurückgesetzt werden. Vergisst du
> es, ist der Zugang verloren.

That warning is the feature. An optional-email account whose recovery limits are
discovered later is a support burden and a broken promise.

Non-negotiables, because this is the first feature here that stores a secret:

- Passwords hashed with a slow, salted, memory-hard function. Never anything
  else, never a fast hash, never rolled by hand.
- Sessions in a `HttpOnly`, `Secure`, `SameSite` cookie.
- Registration and login rate-limited — the API has none today, noted since
  Wave 3, and it stops being acceptable the moment credentials exist.
- No password, hash or token in any log line.

### 3 — claim-gardens

Wave 3 chose share links and put a nullable `owner_id` on `garden` from the very
first migration so this would cost one column rather than a migration of live
plans. This is where that pays: a logged-in user opening a share link can claim
that garden.

Share links keep working. They are how people show a plan to someone who has no
account, and removing them to push registration would be a downgrade dressed as a
feature.

## Risks

- Authentication is the one area here where a mistake is other people's problem.
  It warrants a security review of its own rather than the usual gates.
- Optional email means account loss is expected, not exceptional. Deleting a
  garden must stay possible from the share link alone.

## Open Research

None blocking.

## Definition of done

A viewpoint on the plan shows what is visible from it; a user registers without
an email, having been told what that costs, and claims a garden they made
earlier from its share link.

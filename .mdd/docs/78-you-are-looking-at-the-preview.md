---
id: 78-you-are-looking-at-the-preview
title: You Are Looking at the Preview
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-18
wave_status: active
depends_on: [76-a-second-stack]
relates: [76-a-second-stack]
source_files:
  - ninanatur/web/environment.py
  - ninanatur/web/app.py
  - frontend/src/components/PreviewBand.tsx
  - frontend/src/api/client.ts
  - frontend/src/styles.css
routes:
  - GET /healthz
models: []
test_files:
  - tests/test_web.py
  - frontend/src/components/PreviewBand.test.tsx
data_flow: greenfield
last_synced: 2026-09-06
status: complete
phase: all
mdd_version: 11
tags: [deployment, preview, healthz, environment, safety]
path: Ops/Deployment
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "The band names the environment but has no way to know whether that deployment's volume is ever actually cleared; it states the intention rather than a fact about the host."
---

# You Are Looking at the Preview

Feature 4 of Wave 18. `NINANATUR_ENV` has been passed into the container since
Wave 8 and read by **nothing**. It matters now.

## Why a band and not a label

The preview and the live site are the same application, byte for byte. That is
the point of a preview and it is also the danger: somebody who draws a garden on
the wrong one loses it the next time that volume is cleared, and until now there
was nothing on the page to tell them apart.

So it is a band across the top, above the header, pushing the page down. A
discreet corner marker is exactly what somebody stops seeing on the second day —
which is the day they start trusting the page.

Warm rather than red. The preview working correctly is the normal case; this is
a signpost, not a failure.

## The default is the important half

**Nothing is shown on production, and nothing is shown when the server does not
say.** Both matter, and the second is the one worth being deliberate about: an
older image, or a proxy serving a cached health response, must not put
"Vorschau" across the live site. A band that is missing on the preview is a
smaller failure than a band that appears on production.

That default lives in three places and each one has to agree: `environment()`
returns `prod` for an unset variable, the client returns `'prod'` when the field
is absent, and the component renders nothing for `null`. Three tests, one per
layer.

## Read from the server, like the version

`/healthz` grew one field and the frontend asks for it, rather than the value
being compiled into the bundle. Same reasoning as the version badge: only the
server knows which build is actually running, and a baked-in value keeps
claiming the old one after a partial rollout.

The environment is lower-cased and trimmed on the way out, so `Dev`, `DEV` and
`dev` are one deployment and the frontend can compare against a literal.

## Verified in a browser, both ways

With `NINANATUR_ENV=dev`: the band renders at the top of the page, `role="status"`,
`--warn` as its ground, linking to the live site so somebody can move.

Without it: no band, and the header sits exactly where the band was — nothing
shifted, no gap left behind. That is the case worth checking by hand, because it
is the one that would be embarrassing.

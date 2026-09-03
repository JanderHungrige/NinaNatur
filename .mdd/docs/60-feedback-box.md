---
id: 60-feedback-box
title: A Box to Say Something Is Wrong
edition: MDD
initiative: ninanatur
depends_on: []
relates: [55-living-background]
source_files:
  - ninanatur/feedback/store.py
  - ninanatur/feedback/issues.py
  - ninanatur/api/feedback.py
  - ninanatur/ingest/schema_user.py
  - frontend/src/components/FeedbackBox.tsx
routes:
  - GET /api/v1/feedback/questions
  - POST /api/v1/feedback
models: [feedback]
test_files:
  - tests/test_feedback.py
  - frontend/src/components/FeedbackBox.test.tsx
data_flow: greenfield
last_synced: 2026-09-03
status: complete
phase: all
mdd_version: 11
tags: [feedback, github, issues, rate-limiting, privacy]
path: Support/Feedback
integration_contracts: []
satisfies_contracts: []
security_read_sites:
  - ninanatur/api/feedback.py::_caller
known_issues:
  - "Filing needs NINANATUR_GITHUB_TOKEN in the deployment's env-file; without it reports are stored but not filed."
---

# A box to say something is wrong

## What this is

A quiet button in the header. It opens a form with three guiding questions, and
the answers become a GitHub issue. No link out to GitHub — nobody should need an
account there to report that a button does not work.

## Decisions

### Guiding questions, not one empty box

"Was ist kaputt" is answered with "geht nicht" about half the time. Three
questions — what you were doing, what happened instead, how to get there — are
what turn a report into something reproducible, and the third is optional
because somebody who cannot reproduce it should still be able to send what they
saw.

The questions live on the server and the form asks for them. Two copies is how
the heading in a filed issue ends up disagreeing with the question that produced
the answer under it.

### Stored first, filed second

The issue is where a report gets acted on, but filing can fail: no token, a rate
limit, GitHub down. A bug report lost to any of those is worse than one that
arrives late, so it is written to the volume first. `issue_url IS NULL` is then
the list of what has not been filed, rather than a thing to guess at.

The sender is told which of the two happened, honestly: "ist eingetragen" or
"angekommen und gespeichert". Claiming success for a report that went nowhere is
the same mistake the colour note made when it announced itself before the
request had been sent.

### What never leaves the browser

The share token is the entire access control for a garden, and the tracker is
public. Nothing beyond the answers is forwarded — the endpoint reads the answer
keys it asked about and ignores everything else in the payload, which is
asserted by a test that posts a token-shaped extra field.

The form says the tracker is public *before* the send button, not after. That is
too late for somebody who has just pasted a password.

`@name` and `#12` are defused with a zero-width joiner: they read identically
and GitHub stops matching, so a stranger's submission cannot notify a person or
cross-link an issue from a public repository.

### Two limits, for two different attackers

Five per sender per hour, forty in total. The per-sender count is keyed on a
salted hash of the caller's address — the address answers exactly one question,
"how many in the last hour", and a hash answers it just as well without keeping
anybody's IP.

That address comes from `X-Forwarded-For`, because the app sits behind a proxy
and `request.client` is otherwise the proxy for everybody. It can be forged,
which is why the per-sender limit is a speed bump and the global hourly cap is
the actual backstop. Both are tested, the global one specifically with forged
addresses.

### The schema split that came with it

`schema.py` was at exactly 300 lines, so the `feedback` table did not fit. The
split is by lifecycle rather than by size: `schema_user.py` holds what people
make and what lives on the volume, `schema.py` holds what is derived from open
sources and ships in the image. That is the distinction the whole project turns
on, and it was worth having in the file layout rather than only in prose.

## Operating it

`NINANATUR_GITHUB_TOKEN` in the deployment's env-file — a fine-grained token
with *Issues: read and write* on this repository and nothing else. Absent is a
supported state, not a crash: reports are collected and simply not filed.

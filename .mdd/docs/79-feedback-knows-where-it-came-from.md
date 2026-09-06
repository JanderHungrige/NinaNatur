---
id: 79-feedback-knows-where-it-came-from
title: Feedback Knows Where It Came From
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-18
wave_status: active
depends_on: [78-you-are-looking-at-the-preview]
relates: [78-you-are-looking-at-the-preview, 60-feedback-box]
source_files:
  - ninanatur/feedback/issues.py
  - deploy/.env.dev.example
routes: []
models: [feedback]
test_files:
  - tests/test_feedback.py
data_flow: writes-existing
last_synced: 2026-09-06
status: complete
phase: all
mdd_version: 11
tags: [feedback, github, preview, deployment, labels]
path: Ops/Deployment
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "The label is only reachable if somebody deliberately puts a token in .env.dev; the default is that a preview cannot file at all."
---

# Feedback Knows Where It Came From

Feature 5 of Wave 18. The feedback box files GitHub issues. From a preview,
every test of the button would be a real issue in the tracker.

## The default answers it, and it was already there

`.env.dev.example` leaves `NINANATUR_GITHUB_TOKEN` blank, and an absent token is
already a supported state: the report is stored on the volume and
`feedback.issue_url IS NULL` is the list of what was not filed. So the box can be
exercised on the preview without touching the tracker at all — which is what
somebody testing the button actually wants.

Nothing needed building for that. It is the arrangement Wave 14 chose for a
different reason, working here for free.

## The escape hatch, for when filing is the thing being tested

Sometimes the filing path itself is what needs checking — a rotated token, a
changed API, a new label. Then a token goes into `.env.dev` deliberately, and
every issue it creates must be tellable apart from a real report. A tracker
somebody has to sort by hand is a tracker that stops being sorted.

So anything filed from an environment that is not production carries:

- the label **`from-preview`**, alongside the kind
- a line in the body naming the environment

**Both, and not only the label.** A label can be removed while triaging and the
sentence stays — which matters for the one thing this protects against: acting
on a report about a bug that only ever existed on a preview.

Production files exactly what it always did. A label saying "this is real" on
every real report is noise.

## Not a second repository

The obvious alternative is to point the preview at a test repo. Rejected: two
repositories are two sets of labels, two sets of milestones, and two things to
keep in step — for a case that arises when somebody is deliberately testing the
filing path, which is rare.

## One small thing

The environment name goes through `defused` like every other string in the body.
It comes from a host environment variable rather than from a user, so this is
belt and braces — but `@name` in a GitHub issue notifies that person and `#12`
links another issue, and the one string in the body that skipped that treatment
would be the one somebody eventually set from something less trustworthy.

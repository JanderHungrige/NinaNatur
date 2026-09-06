---
id: 75-the-branch-that-goes-first
title: The Branch That Goes First
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-18
wave_status: active
depends_on: []
relates: []
source_files:
  - CLAUDE.md
  - deploy/SERVER-SETUP.md
  - .github/workflows/deploy.yml
routes: []
models: []
test_files:
  - tests/test_deploy_config.py
data_flow: greenfield
last_synced: 2026-09-06
status: complete
phase: all
mdd_version: 11
tags: [deployment, branching, ci, preview, conventions]
path: Ops/Deployment
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Nothing enforces the merge order; it is a convention with a written rule and a consistency test, not a branch protection rule."
---

# The Branch That Goes First

Feature 0 of Wave 18. Everything built so far went from a feature branch
straight to production.

## The order is the point

```
feat/<something>  →  dev-deployment  →  main
                     :dev on 4001       :main on 4000
                     preview            live
```

- A wave stage merges into `dev-deployment` first, and is looked at on
  `ninanatur-dev.w3rth.de`.
- `main` is merged **from `dev-deployment`**, not from the feature branch. That
  distinction is the whole feature: it means what goes live is what was actually
  looked at, rather than something that merely passed the same tests.
- After a release `dev-deployment` is reset to `main`, so it never becomes a
  third history that nobody deploys.

Written in two places because two different questions lead there.
`CLAUDE.md` gets the flow, next to the "branch per feature" rule it modifies.
`deploy/SERVER-SETUP.md` gets the branch → tag → port → address table, because
that is the file somebody opens when the host is misbehaving.

## The test is the interesting part

A branch convention is not obviously testable. What *is* testable is that the
four files encoding it still agree: the workflow decides which branch produces
which tag, the env templates decide which tag each stack pulls and on which
port, and the compose file wires them together.

They are edited at different times for different reasons, and a disagreement
between them does not fail — **it deploys the wrong image, or nothing at all,
silently.** A stack pulling a tag nothing builds simply sits on whatever it
started with for as long as nobody looks.

`tests/test_deploy_config.py` asserts self-consistency rather than fixed values,
the way CLAUDE.md asks: it survives somebody renaming a tag and fails if they
rename it in one place only. Six checks:

| | |
|---|---|
| CI builds from both branches | a stack whose tag is never built is a stack that never updates |
| Every tag a stack pulls is a tag CI pushes | the join between CI and the host, expressed nowhere else |
| The two stacks differ in project name, port, tag and env | **sharing the project name means sharing the volume** — testing a migration against real gardens |
| They agree on registry, owner and image | a preview built from another repository would look right and prove nothing |
| Compose reads every variable the templates set | a setting nothing reads is a setting somebody believes is working |
| No template carries a token | templates are tracked; the real env files are not |

Verified by breaking it twice: pointing dev at a tag CI does not build, and
putting dev on production's port. Each fails one check and only that one.

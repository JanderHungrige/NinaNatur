---
id: 77-one-cron-two-environments
title: One Cron, Two Environments
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-18
wave_status: active
depends_on: [76-a-second-stack]
relates: [76-a-second-stack]
source_files:
  - deploy/roll-all.sh
  - deploy/install-cron.sh
  - deploy/crontab.example
  - deploy/SERVER-SETUP.md
routes: []
models: []
test_files:
  - tests/test_roll_all.py
data_flow: greenfield
last_synced: 2026-09-06
status: complete
phase: all
mdd_version: 11
tags: [cron, deployment, locking, shell, ordering]
path: Ops/Deployment
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "roll-all.sh takes environment names as arguments, which nothing currently uses; the cron line relies on the default order."
---

# One Cron, Two Environments

Feature 2 of Wave 18. The wave plan said the lock needed changing. It did not —
the lock is right and the reasoning next to it is right. The defect was one line
above.

## What was actually wrong

`crontab.example` and `install-cron.sh` emitted **one line per environment**, and
both lines carried the same `sleep 15`. So both fired in the same second, both
raced the single global lock in `auto-deploy.sh`, and `flock -n` makes the loser
**exit rather than wait**.

Every minute was a coin flip. Nothing guaranteed fairness, so dev could go
unrolled for an arbitrarily long time while looking perfectly configured — which
is the worst kind of broken, because the crontab reads correctly.

**The lock stays global.** Two overlapping runs racing the same image pull
corrupt the containerd content store, and the comment saying so is correct. What
was wrong was asking two processes to share one lock when one process can do
both jobs in order.

## A script, not a longer cron line

The obvious fix is to chain the two commands in the crontab. Two reasons not to:

- **`A && B >> log 2>&1` redirects only B.** The plan's own proposed line had
  that bug in it. Production's output would have gone to cron's mail, which
  nobody reads, while dev's went to the log everybody does.
- A crontab line containing a `for` loop is not something anybody wants to read
  at three in the morning, and **it cannot be tested.**

`deploy/roll-all.sh` does production first, then dev, in one process, and stops
if production fails — if the registry or the daemon is broken, trying the next
environment against the same broken thing only fills the log.

It also **skips an environment whose env file is absent**, which means the cron
line does not name the environments: a host that gains a `.env.dev` starts
rolling it on the next tick with no reinstall. That is the normal path here,
since the host runs production today.

## Tested by running it

`tests/test_roll_all.py` runs the script against a recording stand-in for
`auto-deploy.sh` — a bug that was invisible in the file and visible only in the
behaviour is an argument for testing the behaviour.

Five checks: nothing is rolled that is not configured, production goes first, a
failed production roll stops the rest, adding dev later needs no reinstall, and
the installer emits exactly **one** line for this project.

Verified by reversing the order and by removing the stop-on-failure — three
tests fail for the first, one for the second.

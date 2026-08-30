---
id: 35-accounts
title: An Account, and What It Honestly Offers
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-9
wave_status: complete
depends_on: []
relates: [36-claim-gardens, 30-landing-and-garden-id]
source_files:
  - ninanatur/auth/passwords.py
  - ninanatur/auth/sessions.py
  - ninanatur/api/accounts.py
  - ninanatur/ingest/db.py
  - frontend/src/components/AccountPanel.tsx
  - frontend/src/api/client.ts
routes:
  - POST /api/v1/accounts
  - POST /api/v1/sessions
  - DELETE /api/v1/sessions
  - GET /api/v1/accounts/me
models:
  - account
  - session
test_files:
  - tests/test_passwords.py
  - tests/test_accounts.py
  - frontend/src/components/AccountPanel.test.tsx
  - frontend/src/api/client.test.ts
data_flow: greenfield
last_synced: 2026-08-30
status: complete
phase: all
mdd_version: 11
tags: [accounts, passwords, scrypt, sessions, cookies, rate-limit, security]
path: Auth/Accounts
integration_contracts:
  - function: require_account
    when: any route that must know who is asking
    note: a session is a hashed token in an HttpOnly cookie; the raw token is never stored
satisfies_contracts: []
security_read_sites:
  - ninanatur/api/accounts.py::log_in
  - ninanatur/auth/sessions.py::account_for
known_issues: []
sister_projects: []
---

# 35 — An Account, and What It Honestly Offers

## Purpose

Registration with a username and password, so gardens can be kept in one place.
**Email is optional**, as asked for — and the consequence is stated where the
choice is made:

> Ohne E-Mail-Adresse kann dein Passwort nicht zurückgesetzt werden. Vergisst du
> es, ist der Zugang verloren.

That warning is the feature. An optional-email account whose recovery limits are
discovered later is a support burden and a broken promise. It is shown at
registration, returned by the API with every account response, and repeated on
screen while logged in — because it stays true and it is the thing people forget.

## The first secret this project stores

### Passwords

`hashlib.scrypt`, N=2^16, r=8, p=1 — 64 MB and about 150 ms, measured on this
project's own hardware. Memory-hard, salted, and slow enough that a stolen
database is not a wordlist away from every account.

**Standard library rather than argon2-cffi**, and that is a trade-off rather than
a claim: Argon2id is the more modern choice. This is the one place in the system
where an added dependency is also an added supply chain to trust, the container
gains no build step, and scrypt (RFC 7914) meets the stated requirement.

The parameters travel with the hash — `scrypt$N$r$p$salt$hash` — so they can be
raised later without locking anybody out, and `needs_rehash` says when a stored
hash is behind.

Verification is `hmac.compare_digest`: a byte-by-byte compare leaks the hash one
character at a time to anyone who can measure the response. Anything unparseable
**fails closed** — a malformed hash is never a reason to let somebody in.

### Sessions

The cookie carries a 32-byte token. The database stores only a SHA-256 of it, so
a stolen database is a list of useless strings rather than a drawer full of
working logins. A plain hash is right here and wrong for a password: this is 256
bits of entropy nobody chose.

Cookie flags: `HttpOnly`, `SameSite=Lax`, and `Secure` **derived from the scheme
the request actually arrived on**, including `X-Forwarded-Proto` — the deployment
sits behind Nginx Proxy Manager. Hardcoding Secure on breaks local development;
hardcoding it off ships a session cookie over plaintext. Lax rather than Strict,
because a share link followed from somebody's message must still find the
session.

### Rate limiting

The API has had none since Wave 3, which was defensible while the only credential
was a 32-byte share token and stops being defensible the moment a person chooses
a password. Ten attempts per five minutes per IP, on registration and login.

### Not leaking who exists

A wrong password and an unknown username return the same status and the same
body. Otherwise the login form is a username oracle.

## Business Rules

- **No composition rules.** Ten characters minimum, and the password may not be
  the username. A rule demanding a digit and a symbol produces `Passwort1!` and
  a sticky note.
- **No password, hash or session token in any log line** — asserted by a test,
  not promised.
- **The account response has no field for a password or a hash**, so neither can
  be returned by accident.

## Known Issues

- **The rate limit is in-process and per-IP.** One container, and a restart
  forgets it. A shared store is the answer at more than one process; a slow hash
  is the floor beneath it, not a substitute.
- **No password reset at all yet**, with or without an email. The warning is
  therefore currently true for everybody, which is why it is worded as it is.
- **No account deletion.** Wave 10 or a follow-up; the share link still deletes a
  garden, which is the part that matters for data the user regrets.

## Bugs

(none. One test asserted `SameSite=Lax` by capitalisation, which tests the
framework's formatting rather than the protection — the attribute is
case-insensitive per RFC 6265bis.)

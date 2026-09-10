# NinaNatur — host setup

One-time steps on the host. After this, every push to `main` is live within
about a minute with no manual action.

## 0. Prerequisite: docker without sudo

Put the operator account in the `docker` group so the manual steps below work:

```bash
sudo usermod -aG docker "$USER" && newgrp docker
docker ps        # must work with no sudo
```

`newgrp` opens a new shell, usually back in your home directory — `cd` again
before continuing.

This is for working on the host by hand. The cron itself runs as root (step 4),
so it is unaffected either way. Being in the `docker` group is effectively
root-equivalent access; that is the accepted trade for convenient manual ops.

## 1. Clone and configure

```bash
sudo git clone https://github.com/JanderHungrige/NinaNatur.git /opt/ninanatur
sudo chown -R "$USER":"$(id -gn)" /opt/ninanatur
cd /opt/ninanatur
cp deploy/.env.prod.example deploy/.env.prod
cp deploy/.env.dev.example  deploy/.env.dev
```

The `chown` is not cosmetic. `sudo git clone` leaves the tree owned by root, so
every following step fails with `Permission denied` — and more importantly the
cron in step 4 runs from **your** crontab, not root's, so it needs to read the
env files and write the lock as your user.

If you would rather keep the tree root-owned, install the cron lines in
`sudo crontab -e` instead, and run every command below with `sudo`. Do not mix
the two — a root-owned tree with a user crontab is the configuration that fails
silently once a minute.

`.env.prod` publishes on **4000**, `.env.dev` on **4001**. The real env files are
gitignored; only the `.example` templates are tracked.

## 2. GHCR access — nothing to do

Verified against the registry on 2026-08-27: an anonymous token pulls the
manifest for `ghcr.io/janderhungrige/ninanatur:main` successfully, so the package
is public and **the host needs no docker login**.

Re-check with:

```bash
docker logout ghcr.io
docker pull ghcr.io/janderhungrige/ninanatur:main
```

If this ever starts failing with `denied` / `unauthorized`, the package turned
private — set it back under
`github.com/users/JanderHungrige/packages/container/ninanatur/settings`, or log
the host in once. A private package with no login makes the cron fail **silently
every minute** while the site simply never updates.

## 2b. Which branch feeds which stack

| Branch | Image tag | Env file | Port | Reached at |
|---|---|---|---|---|
| `dev-deployment` | `:dev` | `deploy/.env.dev` | 4001 | `ninanatur-dev.w3rth.de` |
| `main` | `:main` | `deploy/.env.prod` | 4000 | `ninanatur.w3rth.de` |

Work goes to `dev-deployment` first and is looked at on the preview; `main` is
merged from `dev-deployment` rather than from the feature branch, so what goes
live is what was actually looked at. Nothing on the host distinguishes the two
stacks except the env file — same image name, same compose file, different tag,
port and project name.

## 3. First start

```bash
cd /opt/ninanatur
docker compose --env-file deploy/.env.prod -f deploy/compose.app.yml up -d
curl -i --max-time 5 http://localhost:4000/healthz

docker compose --env-file deploy/.env.dev -f deploy/compose.app.yml up -d
curl -i --max-time 5 http://localhost:4001/healthz
```

The two stacks share nothing. `COMPOSE_PROJECT_NAME` scopes the named volume, so
`ninanatur-prod_ninanatur-data` and `ninanatur-dev_ninanatur-data` are two
databases. **Verified rather than assumed** — locally on 2026-09-06, both stacks
from the same image: a garden created on one answered 200 there and **404** on
the other, and `docker volume ls` showed two volumes. Worth repeating on the
host once, because a shared volume means testing a migration against real
gardens:

```bash
docker volume ls | grep ninanatur     # two entries, prod_ and dev_
T=$(curl -s -X POST localhost:4001/api/v1/gardens \
      -H 'content-type: application/json' \
      -d '{"name":"nur dev","latitude":52.5,"longitude":13.4}' \
      | python3 -c 'import sys,json;print(json.load(sys.stdin)["share_token"])')
curl -s -o /dev/null -w "dev  %{http_code}\n" localhost:4001/api/v1/gardens/$T
curl -s -o /dev/null -w "prod %{http_code}\n" localhost:4000/api/v1/gardens/$T   # must be 404
```

The dev stack comes up against a **fresh empty volume** and seeds itself, which
is the state CLAUDE.md asks to be checked by hand and the one a test double never
reproduces. Its log says so:

```
catalogue synced: {'taxon': 8939, 'trait': 84217, 'partner_summary': 6382, ...}
```

## 4. Cron

The other deploys on this host (battlefuel, funding-tender-tracker, 3dmap2) all
live in **root's** crontab. Match them:

```bash
sudo deploy/install-cron.sh          # or paste the one line from deploy/crontab.example
```

**One line, not one per environment.** Two lines both carrying `sleep 15` fire in
the same second and race NinaNatur's own global lock; `flock -n` makes the loser
exit rather than wait, so every minute is a coin flip and dev can stay unrolled
indefinitely while looking configured. `deploy/roll-all.sh` does production
first, then dev, in one process — and it skips an environment whose env file is
absent, so adding `.env.dev` later needs no reinstall.

Because cron runs as root, the tree's ownership does not matter for the deploy —
root reads it either way. Step 0's docker group membership is still worth having
for working on the host by hand.

Note the `sleep 15`: every project's `auto-deploy.sh` holds its own lock, which
only guards against itself. The staggered offsets are what stop four deploys
pulling from GHCR simultaneously. `:00`, `:30` and `:45` are taken.

The global lock inside `auto-deploy.sh` stays as it is and stays global — two
overlapping runs racing the same image pull corrupt the containerd content
store. What was wrong was asking two cron processes to share one lock when one
process can do both jobs in order.

Check that it is actually running:

```bash
tail -f /var/log/ninanatur-deploy.log
```

## Backups

There was no backup at all until 2026-09-10. Now there are three layers, and
each protects against something the others do not:

| Where | Protects against | Kept |
|---|---|---|
| `/data/backups/` inside the volume | a bad migration, a deleted row | 14 nightly + 5 taken before each migration |
| `~/backups/ninanatur/prod/` on the host | the volume itself being removed or recreated | 30 |
| off the host | losing the machine | see below |

**Nightly**, from jan's crontab (docker works without sudo for jan):

```bash
( crontab -l 2>/dev/null; echo '17 3 * * * /opt/ninanatur/deploy/backup.sh >> $HOME/backups/ninanatur/backup.log 2>&1' ) | crontab -
```

03:17 is clear of every project's deploy minute (:00, :15, :30, :45). The copy
is taken with SQLite's online backup API inside the running container, so the
app keeps serving, and it is checked with `PRAGMA integrity_check` before it is
kept — a copy that fails is deleted, never left under a good-looking name.

**Before every migration** the app copies an existing database into
`/data/backups/` itself, at startup. A fresh volume has nothing to copy and gets
nothing.

**Restoring** — rehearsed, not assumed. Always restore into a *new* file first
and look at it; `restore` refuses to overwrite a live database unless told to.

```bash
# 1. Check a copy is sound, and what is in it
docker exec ninanatur-prod-app-1 python -m ninanatur.ops.backup verify /data/backups/<file>.sqlite.gz

# 2. Stop the app, restore over the live file, start it again
cd /opt/ninanatur
docker compose --env-file deploy/.env.prod -f deploy/compose.app.yml stop app
docker compose --env-file deploy/.env.prod -f deploy/compose.app.yml run --rm --no-deps app \
  python -m ninanatur.ops.backup restore /data/backups/<file>.sqlite.gz /data/ninanatur.sqlite --replace
docker compose --env-file deploy/.env.prod -f deploy/compose.app.yml start app
```

A copy that exists only on the host is put back into the volume with
`docker cp ~/backups/ninanatur/prod/<file>.sqlite.gz ninanatur-prod-app-1:/data/backups/`
first.

## 5. Nginx Proxy Manager

| Field | Value |
|---|---|
| Domain | `ninanatur.w3rth.de` |
| Scheme | `http` |
| Forward host | `172.17.0.1` |
| Forward port | `4000` |
| Websockets | on |
| SSL | request a Let's Encrypt cert, force SSL |

`172.17.0.1` is the docker bridge gateway, so NPM reaches the port the container
publishes on the host without sharing a network. `compose.app.yml` publishes on
**that interface only** — `172.17.0.1:${APP_PORT}:4000` — so the app is not
reachable from outside except through NPM and its TLS.

Check it from any machine that is not the host; both lines must fail:

```bash
curl -m 5 http://159.195.148.193:4000/healthz
curl -m 5 http://159.195.148.193:4001/healthz
```

and the domains must still answer over 443.

A compose change does **not** reach the host by itself: `roll-all.sh` and
`auto-deploy.sh` pull images, never git. After merging a change under
`deploy/`, run `cd /opt/ninanatur && git pull` on the host; the next cron tick's
`up -d` then recreates the container with the new binding.

**Whom the app believes.** NPM's requests reach the container from the Docker
network's gateway (172.27.0.1 for production, 172.30.0.1 for the preview — not
172.17.0.1), and the app trusts `X-Forwarded-For` / `-Proto` only from
`NINANATUR_TRUSTED_PROXIES`, default `127.0.0.1,172.16.0.0/12`. If Docker ever
hands out a network outside that range, set the variable in the env file; the
symptom otherwise is every visitor sharing one rate-limit bucket. Check:

```bash
docker exec ninanatur-prod-app-1 python -c "import sqlite3;print(sqlite3.connect('/data/ninanatur.sqlite').execute('SELECT DISTINCT client FROM rate_limit').fetchall())"
```

— real visitor addresses, never `172.x.0.1`.

**Which names the app answers to.** Any Host other than those in
`NINANATUR_ALLOWED_HOSTS` is refused with a 400 — default
`ninanatur.w3rth.de,ninanatur-dev.w3rth.de,localhost,127.0.0.1`. **A new domain
in NPM needs its name added here too**, in the env file, or it will answer 400
and look broken.

**HSTS** is sent by the app itself, only when the proxy reports https. NPM's own
HSTS switch can stay off; turning it on as well is harmless.

**Second layer (needs sudo):** a host firewall that drops 4000 and 4001 from
outside. Not a substitute for the binding — Docker's published ports bypass
ufw's INPUT rules — but it holds if the binding is ever loosened again.

## The plant catalogue

It ships inside the image and seeds itself into an empty volume at first start —
nothing to do on the host. The startup log says so:

```
seeded catalogue: {'taxon': 8939, 'trait': 75278, ...}
```

Plant data and garden data have different lifecycles, which is why they are
sourced differently: the catalogue is derived from static open sources and
travels with the code built against it, while gardens belong to the person who
made them and stay on the volume. Seeding only ever runs when there are no taxa
at all, so it can never overwrite a newer ingest.

To refresh the catalogue, re-run the ingest locally, `export-catalogue`, commit,
and push — the next image carries it, and the next container start applies it.
`export-catalogue` stamps a build time; startup compares that stamp and syncs only
when it differs, so a restart costs nothing when nothing changed. The log says
which:

```
catalogue synced: {'taxon': 8939, 'trait': 84217, ...}
```

Gardens on the volume are never touched by a sync.

## Data

The database lives on a named Docker volume, not in the image and not in the
repo checkout:

```bash
docker volume ls | grep ninanatur
docker compose --env-file deploy/.env.prod -f deploy/compose.app.yml \
  exec app python -c "import os; print(os.environ['NINANATUR_DB'])"
```

The app creates its schema at startup, so a fresh volume is a working deployment
rather than an error. Backing up is a file copy out of the volume.

**Do not remove the volume when rolling containers.** `docker compose down -v`
deletes it; plain `down` or `up -d` does not.

## Verify the whole chain

```bash
curl -i --max-time 5 https://ninanatur.w3rth.de/healthz
```

Then push a trivial change to `main` and watch the log — the container should
roll within a minute or two.

## Troubleshooting

Never diagnose with `curl -s`. On a refused connection it prints **nothing at
all**, which is indistinguishable from an empty 200 — use `curl -i` and check
the exit code (`7` = could not connect).

```bash
cd /opt/ninanatur
docker compose --env-file deploy/.env.prod -f deploy/compose.app.yml ps -a
docker compose --env-file deploy/.env.prod -f deploy/compose.app.yml logs --tail=50 app
docker compose --env-file deploy/.env.prod -f deploy/compose.app.yml port app 4000
```


| Symptom | Likely cause |
|---|---|
| Site never updates, cron log empty | crontab not installed, or absolute paths wrong |
| `denied` / `unauthorized` in the log | GHCR package is private and the host is not logged in (step 2) |
| `skipping this tick` repeatedly | a previous run is stuck holding `/tmp/ninanatur-auto-deploy.lock` |
| 502 from NPM | container down, or forwarding to the wrong port |
| Port already allocated | something else on the host publishes 4000 |
| Gardens vanish after a deploy | the named volume is not mounted — check `volumes:` in deploy/compose.app.yml |
| `Permission denied` on an env file, or cron log shows `couldn't find env file` | tree still owned by root after `sudo git clone` — see step 1 |
| `permission denied ... /var/run/docker.sock` | operator not in the `docker` group — see step 0 |

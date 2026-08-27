# NinaNatur — host setup

One-time steps on the host. After this, every push to `main` is live within
about a minute with no manual action.

## 1. Clone and configure

```bash
sudo git clone https://github.com/JanderHungrige/NinaNatur.git /opt/ninanatur
cd /opt/ninanatur
cp deploy/.env.prod.example deploy/.env.prod
cp deploy/.env.dev.example  deploy/.env.dev
```

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

## 3. First start

```bash
cd /opt/ninanatur
docker compose --env-file deploy/.env.prod -f deploy/compose.app.yml up -d
curl -s localhost:4000/healthz
```

## 4. Cron

```bash
crontab -e     # paste the two lines from deploy/crontab.example
```

Check that it is actually running:

```bash
tail -f /var/log/ninanatur-deploy.log
```

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
publishes on the host without sharing a network.

## Verify the whole chain

```bash
curl -s https://ninanatur.w3rth.de/healthz
```

Then push a trivial change to `main` and watch the log — the container should
roll within a minute or two.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Site never updates, cron log empty | crontab not installed, or absolute paths wrong |
| `denied` / `unauthorized` in the log | GHCR package is private and the host is not logged in (step 2) |
| `skipping this tick` repeatedly | a previous run is stuck holding `/tmp/ninanatur-auto-deploy.lock` |
| 502 from NPM | container down, or forwarding to the wrong port |
| Port already allocated | something else on the host publishes 4000 |

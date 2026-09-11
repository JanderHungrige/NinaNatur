# NinaNatur production image.
#
# Three stages: the frontend bundle, the Python install, and a runtime carrying
# neither toolchain. Build tooling never reaches the layer that runs.
#
# Base images by digest, not by tag: a tag is a pointer its owner can move, and
# the build should be the same build tomorrow. Dependabot proposes new digests.

# --- frontend -----------------------------------------------------------------
FROM node:26-slim@sha256:14bf3eac4bf209d906d3c41256597d3ab1f926b2e93a79e9bdfe1efd32454239 AS frontend

WORKDIR /build
# Manifests first, so a source-only change reuses the install layer.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# --- python deps --------------------------------------------------------------
FROM python:3.13-slim@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285 AS build

WORKDIR /build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1

COPY pyproject.toml requirements.txt ./
COPY ninanatur ./ninanatur
# Exactly the lock CI tested against, every file checked against its hash — then
# the project itself, which must not pull a dependency of its own.
RUN pip install --prefix=/install --require-hashes -r requirements.txt \
 && pip install --prefix=/install --no-deps .


# --- runtime ------------------------------------------------------------------
FROM python:3.13-slim@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285 AS runtime

# Baked at build time: the container carries neither git nor .mdd, so the
# version cannot be derived at runtime — an unset value would show "dev" on a
# real deployment, which is worse than wrong because it looks deliberate.
ARG NINANATUR_VERSION=dev

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_PORT=4000 \
    NINANATUR_DB=/data/ninanatur.sqlite \
    NINANATUR_CACHE_DIR=/data/cache \
    NINANATUR_VERSION=${NINANATUR_VERSION}
WORKDIR /app

COPY --from=build /install /usr/local
COPY ninanatur ./ninanatur
COPY --from=frontend /build/dist ./ninanatur/web/dist

# The database lives on a mounted volume, not in the image. The app creates its
# schema at startup, so a fresh volume is a working deployment rather than a 500.
RUN mkdir -p /data && useradd --create-home --uid 10001 nina && chown -R nina /data /app
USER nina
VOLUME ["/data"]

EXPOSE 4000

# Dependency-free on purpose (see ninanatur/web/app.py): a failing container must
# stay distinguishable from a failing database.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:4000/healthz', timeout=4).status==200 else 1)"

# --no-proxy-headers: the app decides whom to believe about forwarded headers
# (web/app.py, TRUSTED_PROXIES), so the tests exercise the same decision the
# deployment makes. Two places deciding it is how they come to disagree.
# --log-config: JSON lines through `web/logs.py`, which masks the share token.
# --no-access-log: the app writes its own access line, naming the route; uvicorn
# can only write the raw path, and on a garden route the path is the token.
CMD ["uvicorn", "ninanatur.web.app:app", "--host", "0.0.0.0", "--port", "4000", "--no-proxy-headers", \
     "--log-config", "ninanatur/web/log_config.json", "--no-access-log"]

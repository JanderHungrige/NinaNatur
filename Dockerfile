# NinaNatur production image.
#
# Three stages: the frontend bundle, the Python install, and a runtime carrying
# neither toolchain. Build tooling never reaches the layer that runs.

# --- frontend -----------------------------------------------------------------
FROM node:22-slim AS frontend

WORKDIR /build
# Manifests first, so a source-only change reuses the install layer.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# --- python deps --------------------------------------------------------------
FROM python:3.13-slim AS build

WORKDIR /build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1

COPY pyproject.toml ./
COPY ninanatur ./ninanatur
RUN pip install --prefix=/install . "uvicorn[standard]" fastapi


# --- runtime ------------------------------------------------------------------
FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_PORT=4000 \
    NINANATUR_DB=/data/ninanatur.sqlite
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

CMD ["uvicorn", "ninanatur.web.app:app", "--host", "0.0.0.0", "--port", "4000"]

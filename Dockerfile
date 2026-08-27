# NinaNatur production image.
# Two stages so build tooling never reaches the runtime layer, and a non-root
# user so a container escape does not start as root.
FROM python:3.13-slim AS build

WORKDIR /build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1

COPY pyproject.toml ./
COPY ninanatur ./ninanatur
RUN pip install --prefix=/install . "uvicorn[standard]" fastapi


FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 APP_PORT=4000
WORKDIR /app

COPY --from=build /install /usr/local
COPY ninanatur ./ninanatur

RUN useradd --create-home --uid 10001 nina
USER nina

EXPOSE 4000

# The health probe is dependency-free on purpose (see ninanatur/web/app.py), so a
# failing container is distinguishable from a failing backing service.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:4000/healthz', timeout=4).status==200 else 1)"

CMD ["uvicorn", "ninanatur.web.app:app", "--host", "0.0.0.0", "--port", "4000"]

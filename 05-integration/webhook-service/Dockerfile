# Tromox webhook service.
# Build from the REPOSITORY ROOT (the image needs pyproject.toml and shared/):
#   docker build -f 05-integration/webhook-service/Dockerfile -t tromox-webhook .
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Optional: a closer PyPI mirror when building from a slow network, e.g.
#   docker build --build-arg PIP_INDEX_URL=<mirror>/simple -f ... .
ARG PIP_INDEX_URL=https://pypi.org/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}

WORKDIR /srv

# Shared lead schema + service dependencies (root pyproject, [service] extra).
COPY pyproject.toml ./
COPY shared ./shared
RUN pip install ".[service]"

COPY 05-integration/webhook-service/app ./app

# Non-root runtime user; /srv/data is the volume for SQLite + CSV.
RUN useradd --system --uid 10001 --no-create-home appuser \
    && mkdir -p /srv/data \
    && chown -R appuser /srv/data
USER appuser

ENV DATABASE_PATH=/srv/data/leads.db \
    CSV_EXPORT_PATH=/srv/data/leads.csv
VOLUME ["/srv/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

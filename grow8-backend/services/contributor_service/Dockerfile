# Build context: repo root (docker compose sets this).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY shared/ /app/shared/
RUN pip install /app/shared

ARG INSTALL_DEV=false
COPY services/contributor_service/requirements.txt services/contributor_service/requirements-dev.txt /app/services/contributor_service/
RUN pip install -r /app/services/contributor_service/requirements.txt \
    && if [ "$INSTALL_DEV" = "true" ]; then pip install -r /app/services/contributor_service/requirements-dev.txt; fi

COPY services/contributor_service/ /app/services/contributor_service/

RUN useradd --create-home --uid 10001 app
USER app
WORKDIR /app/services/contributor_service

CMD ["python", "-m", "app.main"]

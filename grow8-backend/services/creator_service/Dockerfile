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
COPY services/creator_service/requirements.txt services/creator_service/requirements-dev.txt /app/services/creator_service/
RUN pip install -r /app/services/creator_service/requirements.txt \
    && if [ "$INSTALL_DEV" = "true" ]; then pip install -r /app/services/creator_service/requirements-dev.txt; fi

COPY services/creator_service/ /app/services/creator_service/

RUN useradd --create-home --uid 10001 app
USER app
WORKDIR /app/services/creator_service

CMD ["python", "-m", "app.main"]

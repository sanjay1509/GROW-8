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
COPY api/requirements.txt api/requirements-dev.txt /app/api/
RUN pip install -r /app/api/requirements.txt \
    && if [ "$INSTALL_DEV" = "true" ]; then pip install -r /app/api/requirements-dev.txt; fi

COPY api/ /app/api/

RUN useradd --create-home --uid 10001 app
USER app
WORKDIR /app/api

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

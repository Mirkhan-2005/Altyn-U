FROM python:3.12-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m pip wheel \
    --wheel-dir=/wheels \
    -r requirements.txt


FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 altyn

COPY --from=builder /wheels /wheels
COPY requirements.txt .

RUN python -m pip install \
        --no-index \
        --find-links=/wheels \
        -r requirements.txt \
    && rm -rf /wheels

COPY --chown=altyn:altyn . .

RUN mkdir -p media staticfiles \
    && chown -R altyn:altyn media staticfiles

USER altyn

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
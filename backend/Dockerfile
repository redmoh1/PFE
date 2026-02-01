# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (kept minimal)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# --- Python deps ---
# Default is a "lite" install using backend/requirements.txt.
# To install full ML/NLP deps, pass: --build-arg INSTALL_FULL=true
ARG INSTALL_FULL=false

COPY backend/requirements.txt /app/backend/requirements.txt
COPY requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r /app/backend/requirements.txt \
    && if [ "$INSTALL_FULL" = "true" ]; then pip install --no-cache-dir -r /app/requirements.txt; fi

# --- Download NLTK data for TextBlob sentiment analysis ---
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('averaged_perceptron_tagger'); nltk.download('averaged_perceptron_tagger_eng'); nltk.download('brown'); nltk.download('wordnet')"

# --- App code ---
COPY backend /app/backend
COPY src /app/src

# Runtime dirs (usually mounted in compose)
RUN mkdir -p /app/data /app/logs /app/output

EXPOSE 8001

# v1 API (default)
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]

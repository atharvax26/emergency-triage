# =============================================================
# Stage 1: builder — install deps (needs build tools + libpq-dev)
# =============================================================
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# =============================================================
# Stage 2: production — lean runtime image, non-root user
# =============================================================
FROM python:3.11-slim AS production

WORKDIR /app

# Only the shared library is needed at runtime (no compiler)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Dedicated non-root user
RUN groupadd --system appgroup \
    && useradd --system --gid appgroup --no-create-home appuser

# Bring installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy only the application source — tests, venv, and data stay out
COPY --chown=appuser:appgroup app/ app/
COPY --chown=appuser:appgroup requirements.txt .

USER appuser

EXPOSE 8000

# Single worker is safe behind any external load-balancer;
# increase via UVICORN_WORKERS env or add --workers N here.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

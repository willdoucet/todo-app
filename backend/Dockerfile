# syntax=docker/dockerfile:1.9-labs   # enables better caching features

# ── Builder stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Install uv (pin a specific version for reproducibility - update when you want)
COPY --from=ghcr.io/astral-sh/uv:0.5.24 /uv /uvx /bin/

WORKDIR /app

# Optimizations for faster & smaller image
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# Copy dependency files first → excellent caching
COPY pyproject.toml uv.lock* ./

# Install dependencies only (respect lockfile, no dev deps)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Now copy the actual application code (changes most often → last expensive layer)
COPY ./app ./app
COPY ./alembic ./alembic
COPY ./alembic.ini ./alembic.ini

# Install the project itself (editable not needed in prod, but useful)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ── Dev stage (includes test deps + uv) ───────────────────────────────────────
FROM builder AS dev

# Install test extras on top of prod deps
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra test

# Keep uv available for `uv run pytest`
ENV PATH="/app/.venv/bin:$PATH"

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug"]

# ── Prod runtime stage ────────────────────────────────────────────────────────
FROM python:3.12-slim AS prod

WORKDIR /app

# Copy only the virtual environment + code (keeps image small ~200-350MB)
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app
COPY --from=builder /app/alembic /app/alembic
COPY --from=builder /app/alembic.ini /app/alembic.ini

# Make sure we can run binaries from venv
ENV PATH=".venv/bin:$PATH"

# Security: run as non-root user
RUN useradd --create-home --shell /bin/bash appuser


# Create uploads directory with proper permissions
RUN mkdir -p /app/uploads && chown appuser:appuser /app/uploads

# Copy stock icons to a staging location (will be copied to uploads volume at startup)
COPY --chown=appuser:appuser ./stock_icons /app/stock_icons_src

USER appuser

# Default command - run migrations + start server
# For development you can override with --reload in compose
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
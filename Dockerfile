FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv for dependency + command management
RUN pip install --no-cache-dir uv

# Copy dependency metadata first for better layer caching
COPY pyproject.toml uv.lock ./

# Install third-party dependencies before copying source for better layer caching.
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source
COPY app ./app
COPY shared ./shared
COPY scripts ./scripts
COPY mcp-server ./mcp-server
COPY README.md ./README.md

# Install the project package after source is present so console scripts resolve.
RUN uv sync --frozen --no-dev

# Runtime directories used by default settings
RUN mkdir -p \
        /app/data \
        /app/logs \
        /app/secrets/google \
        /app/secrets/rclone

FROM base AS runtime

EXPOSE 8000 8001

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS ops

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client rclone \
    && rm -rf /var/lib/apt/lists/*

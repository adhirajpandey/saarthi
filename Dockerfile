FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv for dependency + command management
RUN pip install --no-cache-dir uv

# Copy dependency metadata first for better layer caching
COPY pyproject.toml uv.lock ./

# Install project dependencies (including project package)
RUN uv sync --frozen --no-dev

# Copy application source
COPY app ./app
COPY shared ./shared
COPY scripts ./scripts
COPY config.py ./config.py
COPY README.md ./README.md

# Runtime directories used by default settings
RUN mkdir -p logs data

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

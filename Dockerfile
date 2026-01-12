# Use Python 3.12 on Alpine
FROM python:3.12-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install uv if using uv/pyproject.toml
COPY pyproject.toml uv.lock ./
RUN pip install uv

# Copy app code
COPY . .

# Expose port
EXPOSE 8000

# Command to run the app
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-config", "log-conf.yml"]

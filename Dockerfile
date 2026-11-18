FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5100 \
    HOST=0.0.0.0 \
    QUERY_TRAP_DATA=/app/data

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py sentinel_gateway.py wsgi.py gunicorn.conf.py ./
COPY static/ ./static/
COPY templates/ ./templates/

# Create data directory and non-root user
RUN mkdir -p /app/data && \
    useradd -u 1000 -m appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 5100

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT}/api/health || exit 1

CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]


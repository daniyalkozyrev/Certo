# Deterministic backend image for Railway (avoids Nixpacks PATH/uvicorn quirks).
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (better layer caching), then the app itself.
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

# Railway injects $PORT; bind to it (fall back to 8000 for local runs).
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

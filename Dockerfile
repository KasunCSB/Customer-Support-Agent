# Backend Dockerfile for Customer Support Agent

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install minimal system deps (ffmpeg for audio handling, build tools for some packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Use a non-root user for safety
RUN useradd -m app && chown -R app:app /app
USER app

EXPOSE 8000
ENV PORT=8000

# Run Uvicorn in production mode (no reload)
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]

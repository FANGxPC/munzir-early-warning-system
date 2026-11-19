# Munzir (منذر) - Lightweight, Production Container for Cloud & Edge Deployment (AWS Free Tier / Azure / Docker)
# Optimized for AWS Free Tier EC2 (t2.micro / t3.micro) & Container Services (<200MB RAM)

FROM python:3.10-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install CPU-only PyTorch and all dependencies using PyTorch extra-index-url
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --prefix=/install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Final Runtime Image
FROM python:3.10-slim

# Install OpenMP runtime required by LightGBM and ML models
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed Python packages from builder directly to standard /usr/local
COPY --from=builder /install /usr/local
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Copy application source code, playbooks, configuration, and pre-computed lakehouse data
COPY munzir/ /app/munzir/
COPY playbooks/ /app/playbooks/
COPY config/ /app/config/
COPY data/ /app/data/
COPY docs/ /app/docs/
COPY validation/ /app/validation/

# Non-root security user
RUN useradd -m -u 1000 munziruser && \
    chown -R munziruser:munziruser /app
USER munziruser

# Health check for Azure Container Apps
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/feeds')" || exit 1

EXPOSE 8000

# Launch FastAPI with production uvicorn worker
CMD ["python3", "-m", "uvicorn", "munzir.api.app:app", "--host", "0.0.0.0", "--port", "8000"]


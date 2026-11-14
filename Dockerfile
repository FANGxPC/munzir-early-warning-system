# Munzir (منذر) - Lightweight, Production Container for Azure Container Apps & App Service
# Optimized for Azure for Students ($0 Scale-to-Zero Free Tier, <200MB RAM)

FROM python:3.10-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Pre-install CPU-only PyTorch wheel to prevent downloading the 2.8 GB CUDA wheel
RUN pip install --no-cache-dir --prefix=/install torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# Final Runtime Image
FROM python:3.10-slim

WORKDIR /app

# Copy installed Python packages from builder directly to standard /usr/local
COPY --from=builder /install /usr/local
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Copy application source code, playbooks, configuration, and pre-computed lakehouse data
COPY prahari/ /app/prahari/
COPY playbooks/ /app/playbooks/
COPY config/ /app/config/
COPY data/ /app/data/
COPY docs/ /app/docs/
COPY validation/ /app/validation/
COPY munzir_policy_brief.md /app/munzir_policy_brief.md

# Non-root security user
RUN useradd -m -u 1000 prahariuser && \
    chown -R prahariuser:prahariuser /app
USER prahariuser

# Health check for Azure Container Apps
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/feeds')" || exit 1

EXPOSE 8000

# Launch FastAPI with production uvicorn worker
CMD ["python3", "-m", "uvicorn", "prahari.api.app:app", "--host", "0.0.0.0", "--port", "8000"]


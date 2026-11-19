#!/usr/bin/env bash
# ==============================================================================
# Munzir (منذر) - AWS Free Tier EC2 Automated Bootstrap (User Data)
# Target OS: Ubuntu 22.04 / 24.04 LTS (t2.micro or t3.micro)
# Target Cost: $0.00 / Month (100% within 750h/month AWS Free Tier)
# ==============================================================================
set -euo pipefail

echo "[1/5] Updating packages and installing Docker..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl gnupg git docker.io docker-compose-v2

systemctl start docker
systemctl enable docker
usermod -aG docker ubuntu || true

echo "[2/5] Creating 1.5 GB swap file to prevent OOM on 1 GB RAM t2.micro..."
if [ ! -f /swapfile ]; then
    fallocate -l 1536M /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=1536
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "[3/5] Cloning Munzir Sovereign Early Warning Platform..."
DEPLOY_DIR="/home/ubuntu/munzir-platform"
rm -rf "${DEPLOY_DIR}"
git clone https://github.com/FANGxPC/munzir-early-warning-system.git "${DEPLOY_DIR}"
cd "${DEPLOY_DIR}"
chown -R ubuntu:ubuntu "${DEPLOY_DIR}"

echo "[4/5] Building and launching container on ports 80 & 8000..."
docker compose up -d --build

echo "[5/5] Munzir deployed successfully!"

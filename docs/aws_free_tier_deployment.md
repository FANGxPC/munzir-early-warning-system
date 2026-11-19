# AWS Free Tier Deployment Guide

**Platform:** Munzir (منذر) Sovereign Early Warning Platform  
**Target Tier:** AWS Free Tier (12 Months Free: 750 Hours/Month of EC2 `t3.micro`)  
**Target Region:** Asia Pacific - Mumbai (`ap-south-1`)  
**Monthly Operating Cost:** **$0.00 / month** (100% within free allowance)  

---

## Live Deployment Status (Active)

| Property | Value |
| :--- | :--- |
| **Official HTTPS URL (Judges)** | [https://13.203.154.72.sslip.io](https://13.203.154.72.sslip.io) |
| **SSL / TLS Certificate** | Let's Encrypt Authority (TLS 1.3 / HTTP/2, Trusted Padlock) |
| **HTTP to HTTPS Redirect** | Automatic 301 from `http://13.203.154.72` |
| **Region** | `ap-south-1` (Mumbai, India) |
| **Instance ID** | `i-05f213a1b98dac150` |
| **Instance Type** | `t3.micro` (AWS Free Tier Eligible) |
| **Public IPv4** | `13.203.154.72` |
| **FastAPI Swagger Docs** | [https://13.203.154.72.sslip.io/docs](https://13.203.154.72.sslip.io/docs) |
| **Health & Feed Status Endpoint** | [https://13.203.154.72.sslip.io/api/v1/health/feeds](https://13.203.154.72.sslip.io/api/v1/health/feeds) |
| **OpenAQ API Integration** | Connected (`OPENAQ_API_KEY` active) |
| **Monthly Cost** | **$0.00** |

---

## 1. Free Tier Feasibility

| Resource | AWS Free Tier Allowance | Munzir Consumption | Total Billed |
| :--- | :--- | :--- | :--- |
| **Compute (EC2)** | 750 hours/month of Linux `t2.micro` (or `t3.micro`) | 1 instance running 24/7 (720–744 hours) | **$0.00** |
| **Storage (EBS)** | 30 GB General Purpose SSD (gp2/gp3) | 12 GB OS + Container disk | **$0.00** |
| **Data Transfer** | 100 GB/month internet egress free | ~2–5 GB/month | **$0.00** |
| **Memory Buffer** | 1 GB RAM instance | 1.5 GB swap file enabled via cloud-init | **$0.00** |

---

## 2. Option A: 3-Minute Web Console Deployment (Easiest)

If you use the AWS Web Management Console:

### Step 1: Launch an EC2 Instance in Mumbai
1. Sign in directly to: 👉 **[AWS EC2 Mumbai Launch Console](https://ap-south-1.console.aws.amazon.com/ec2/home?region=ap-south-1#LaunchInstances:)**
2. Confirm that the top-right region dropdown shows **Asia Pacific (Mumbai) `ap-south-1`**.
3. Configure the settings:
   - **Name:** `munzir-platform`
   - **Application and OS Images:** **Ubuntu 22.04 LTS (HVM)** *(Free tier eligible)*.
   - **Instance Type:** **`t2.micro`** (1 vCPU, 1 GiB Memory, *Free tier eligible* in Mumbai).
   - **Key pair (login):** Select *Proceed without a key pair* (or select your existing key pair if you want SSH access).

### Step 2: Configure Network & Security Group
Under **Network settings**:
- Check **Allow HTTP traffic from the internet** (Port 80).
- Check **Allow HTTPS traffic from the internet** (Port 443).
- Click **Edit** network settings $\to$ **Add security group rule**:
  - **Type:** Custom TCP
  - **Port Range:** `8000`
  - **Source Type:** Anywhere (`0.0.0.0/0`)
  - **Description:** Munzir Web & API

### Step 3: Paste User Data Script
1. Scroll down and expand **Advanced details**.
2. Scroll to the very bottom to the **User data** text field.
3. Paste the contents of [`infra/ec2_user_data.sh`](file:///home/fang/Downloads/Dubai-Hackathon/Prahari/infra/ec2_user_data.sh):

```bash
#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl gnupg git docker.io docker-compose-v2
systemctl start docker
systemctl enable docker
usermod -aG docker ubuntu || true

if [ ! -f /swapfile ]; then
    fallocate -l 1536M /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=1536
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

DEPLOY_DIR="/home/ubuntu/munzir-platform"
rm -rf "${DEPLOY_DIR}"
git clone https://github.com/FANGxPC/munzir-early-warning-system.git "${DEPLOY_DIR}"
cd "${DEPLOY_DIR}"

cat << 'ENVEOF' > "${DEPLOY_DIR}/.env"
OPENAQ_API_KEY=7d3d5a3165c2aebbc4573b32a0f7d68d599b2318d63d5143140006b5c5f350f3
SENTINEL_API_KEY=munzir_sentinel_secret_2026
PORT=8000
HOST=0.0.0.0
MUNZIR_ENV=production
ENVEOF

chown -R ubuntu:ubuntu "${DEPLOY_DIR}"
docker compose up -d --build
```

4. Click **Launch Instance**.

Within 2 to 3 minutes, your instance will be running, Docker will build the container, and Munzir will be live at:
```
http://<YOUR-EC2-PUBLIC-IP>
```
*(Also accessible at `http://<YOUR-EC2-PUBLIC-IP>:8000`)*.

---

## 3. Option B: 1-Command CLI Deployment

If you have the `aws` CLI installed and configured (`aws configure`):

Run:
```bash
./infra/deploy_aws.sh up
```

This automated script will:
1. Detect your default VPC.
2. Create the `munzir-sg` security group (opening ports 80, 8000, 22).
3. Query the latest official Ubuntu 22.04 LTS AMI.
4. Launch the `t2.micro` Free Tier instance with `infra/ec2_user_data.sh`.
5. Wait for the public IP and display the live URL.

To inspect instance status:
```bash
./infra/deploy_aws.sh status
```

To terminate the instance and stop all services:
```bash
./infra/deploy_aws.sh down
```


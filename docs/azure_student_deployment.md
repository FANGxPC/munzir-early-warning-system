# Azure for Students Deployment & Cost Optimization Guide

**Platform:** PRAHARI Early Warning Platform  
**Target Subscription:** Azure for Students ($100 credit, 12 months free services)  
**Monthly Operating Cost:** **$0.00 / month** (within free tier allowance)

---

## 1. Executive Summary: Is PRAHARI Ready for Azure for Students?

**YES, PRAHARI is 100% ready and specifically adapted for Azure for Students deployment.**

Unlike traditional enterprise health platforms that demand expensive, continuous infrastructure (e.g. 24/7 dedicated PostgreSQL servers, GPU inference nodes, and multi-tenant Kubernetes clusters that burn through a $100 student credit in 3 weeks), PRAHARI was engineered from day one with **credit-preservation guardrails**:

| Architecture Attribute | Typical Cloud Trap | PRAHARI Student-Safe Design | Azure Cost Impact |
|---|---|---|---|
| **Database & Lakehouse** | Continuous Azure PostgreSQL Flexible Server ($25–$50/mo) | **Self-Contained Parquet Lakehouse** (<50 MB total on disk) | **$0.00** (Included in container / 5 GB free Blob) |
| **Compute & Serving** | App Service Always-On / AKS Cluster ($70+/mo) | **Azure Container Apps with Scale-to-Zero** (`minReplicas: 0`) | **$0.00** (Within free 180,000 vCPU-sec/month) |
| **Inference & AI** | GPU VM ($150+/mo) or Azure OpenAI API calls | **LightGBM CPU Trees (<5ms)** + Deterministic Template Fallback | **$0.00** (No GPU or OpenAI quota required) |
| **Idle Running Cost** | Drains student credit while waiting for judges | **Shuts down to 0 instances** when inactive; wakes up on click in 2s | **$0.00** |

---

## 2. Azure for Students Free Tier Grants Leveraged

Azure for Students grants users $100 in initial credits plus 12 months of free services:

1. **Azure Container Apps:**
   - **Monthly Free Allowance:** 180,000 vCPU-seconds + 360,000 GiB-seconds + 2 million HTTP requests free per month.
   - **PRAHARI Usage:** Configured at 0.5 vCPU and 1.0 GiB RAM with `minReplicas: 0`. It only runs when an evaluator or judge opens the URL. During a 7-minute live pitch or 100 interactive evaluation sessions, PRAHARI consumes < 1,500 vCPU-seconds (<1% of the free monthly grant).
2. **Azure Static Web Apps / Container Ingress:**
   - Standard TLS/SSL certificates and custom domain ingress are completely free.
3. **Azure Blob Storage (Optional Cloud Offload):**
   - 5 GB LRS storage free for 12 months (PRAHARI's 3-year lakehouse uses ~48 MB).

---

## 3. Deployment Options

### Option A: One-Command Deployment via Azure CLI (Recommended)

You can run this directly from your laptop or inside the browser via **Azure Cloud Shell** (`https://shell.azure.com`):

```bash
# 1. Clone the repository and enter directory
git clone -b fang git@github.com:FANGxPC/munzir-early-warning-system.git
cd munzir-early-warning-system

# 2. Login to Azure (uses device code authentication)
az login --use-device-code

# 3. Execute the automated deployment script
chmod +x infra/deploy_student.sh
./infra/deploy_student.sh
```

The script will automatically:
- Register the required `Microsoft.App` container providers.
- Create an Azure resource group (`rg-prahari-student` in `eastus` or `uaenorth`).
- Build and push the container using Azure Cloud Build.
- Deploy the Container App with **`minReplicas = 0`** (scale-to-zero).
- Output the live HTTPS URL (e.g. `https://prahari-live.polarocean-12345.eastus.azurecontainerapps.io`).

---

### Option B: Bicep Infrastructure as Code Deployment

If you prefer declarative template deployment:

```bash
# 1. Create Resource Group
az group create --name rg-prahari-student --location eastus

# 2. Deploy Bicep template
az deployment group create \
  --resource-group rg-prahari-student \
  --template-file infra/main.bicep \
  --parameters appPrefix=prahari
```

---

## 4. Pre-Flight Verification Checklist for Evaluators

Once deployed to Azure, verify all features from the web browser:

- [ ] **Live Situation Map:** `https://<YOUR_APP_URL>/` renders H3 resolution 7 hexagonal cells and cluster boundaries.
- [ ] **Entra ID Role Switcher:** Switch between `surveillance_officer`, `employer_safety`, and `public` to verify privacy boundaries live.
- [ ] **Evidence Card SLA:** Open any alert and click "View Evidence Card" — verifies sub-10ms render.
- [ ] **Missing-Data Simulation:** Toggle off the clinical feed in the "Missing-Data Demo" tab to observe real-time conformal interval widening and alert policy capping.
- [ ] **Health Impact Calculator:** Adjust workforce sliders in "Health Impact & Resilience" to show instantaneous live recalculation.
- [ ] **Regulatory Policy Brief:** Click "Export Markdown Brief" to download the privacy-preserving policy summary.
- [ ] **Scale-to-Zero Verification:** Close the browser tab. Within 5 minutes, Azure Container Apps scales active replicas down to 0, completely stopping credit consumption.


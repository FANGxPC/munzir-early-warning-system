#!/usr/bin/env bash
# ==============================================================================
# PRAHARI - One-Command Azure for Students Deployment Script
# Deploys serverless Container App with scale-to-zero (Cost = $0.00 / month)
# ==============================================================================

set -euo pipefail

# Configuration Defaults
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-prahari-student}"
LOCATION="${LOCATION:-eastus}" # Or 'uaenorth' (Dubai)
APP_NAME="${APP_NAME:-prahari-live}"

echo "================================================================================"
echo "PRAHARI Early Warning Platform - Azure for Students Deployment"
echo "Target Resource Group: ${RESOURCE_GROUP}"
echo "Location:              ${LOCATION}"
echo "Container App Name:    ${APP_NAME}"
echo "================================================================================"

# 1. Verify Azure CLI is logged in
if ! az account show > /dev/null 2>&1; then
    echo "[!] Azure CLI not logged in. Initiating login..."
    az login --use-device-code
fi

SUBSCRIPTION_NAME=$(az account show --query name -o tsv)
echo "[*] Active Azure Subscription: ${SUBSCRIPTION_NAME}"

# 2. Register required Azure resource providers
echo "[*] Registering Azure Container App resource providers..."
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait

# 3. Create Resource Group if not existing
echo "[*] Ensuring Resource Group exists: ${RESOURCE_GROUP}..."
az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}" --output none

# 4. Deploy using Azure Container App up (Builds container in cloud & deploys with scale-to-zero)
echo "[*] Building and deploying PRAHARI Container App (Scale-to-Zero configured)..."
az containerapp up \
    --name "${APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --source . \
    --ingress external \
    --target-port 8000 \
    --query "properties.configuration.ingress.fqdn" \
    --output tsv > app_fqdn.txt

APP_FQDN=$(cat app_fqdn.txt)

# 5. Configure scale-to-zero explicitly to preserve student credits
echo "[*] Setting min-replicas=0 (Scale-to-Zero enabled: 0 cost when idle)..."
az containerapp update \
    --name "${APP_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --min-replicas 0 \
    --max-replicas 1 \
    --cpu 0.5 \
    --memory 1.0Gi \
    --output none

echo "================================================================================"
echo "[+] PRAHARI Successfully Deployed to Azure!"
echo "[+] Public URL: https://${APP_FQDN}"
echo "[+] Cost Safety: Scale-to-Zero Active (0 replicas when idle = \$0.00 credit burn)"
echo "================================================================================"

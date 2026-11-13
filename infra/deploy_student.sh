#!/usr/bin/env bash
# ==============================================================================
# Munzir (منذر) - Azure for Students Deployment & Lifecycle Controller
# Designed for High-Performance Evaluation (~5 Total Operating Hours, $0.00 Cost)
# ==============================================================================

set -euo pipefail

# Configuration Defaults (overrideable via environment)
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-munzir-student}"
LOCATION="${LOCATION:-eastus}" # Recommended: 'eastus' or 'uaenorth' (UAE Central)
APP_NAME="${APP_NAME:-munzir-live}"
CPU_CORES="${CPU_CORES:-1.0}"
MEMORY_SIZE="${MEMORY_SIZE:-2.0Gi}"

ACTION="${1:-up}"

check_az_login() {
    if ! az account show > /dev/null 2>&1; then
        echo "[!] Azure CLI not authenticated. Initiating device code login..."
        az login --use-device-code
    fi
    local sub_name
    sub_name=$(az account show --query name -o tsv 2>/dev/null || echo "Unknown")
    echo "[*] Connected to Azure Subscription: ${sub_name}"
}

cmd_cost() {
    echo "================================================================================"
    echo "Azure for Students Cost & Performance Math (~5 Total Evaluation Hours)"
    echo "================================================================================"
    echo "Allocation:              ${CPU_CORES} vCPU | ${MEMORY_SIZE} RAM"
    echo "Evaluation Duration:     5.0 hours (18,000 seconds non-continuous)"
    echo ""
    echo "Azure Container Apps Monthly Free Allowance:"
    echo "  - vCPU Allowance:      180,000 vCPU-seconds / month"
    echo "  - Memory Allowance:    360,000 GiB-seconds / month"
    echo "  - Requests Allowance:  2,000,000 HTTP requests / month"
    echo ""
    echo "Munzir 5-Hour Consumption (with minReplicas=1 warm instance):"
    echo "  - vCPU Used:           18,000 vCPU-seconds (10.0% of monthly free grant)"
    echo "  - Memory Used:         36,000 GiB-seconds  (10.0% of monthly free grant)"
    echo "  - Idle Period (sleep): 0 vCPU-seconds      (minReplicas=0, \$0.00 cost)"
    echo ""
    echo "Billed Amount:           \$0.00 (100% within free grant)"
    echo "Student Credit Burn:     \$0.00 (Full \$100 credit remains intact)"
    echo "Performance Profile:     Instant sub-10ms response, zero cold start when warmed"
    echo "================================================================================"
}

cmd_up() {
    check_az_login

    echo "================================================================================"
    echo "Munzir Early Warning Platform - Azure Deployment"
    echo "Target Resource Group: ${RESOURCE_GROUP}"
    echo "Location:              ${LOCATION}"
    echo "Container App Name:    ${APP_NAME}"
    echo "Compute Profile:       ${CPU_CORES} vCPU / ${MEMORY_SIZE} RAM (High Performance)"
    echo "================================================================================"

    # 1. Register required Azure resource providers
    echo "[*] Verifying Azure Container App resource providers..."
    az provider register --namespace Microsoft.App --wait
    az provider register --namespace Microsoft.OperationalInsights --wait

    # 2. Create Resource Group if not existing
    echo "[*] Ensuring Resource Group exists: ${RESOURCE_GROUP}..."
    az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}" --output none

    # 3. Deploy using Azure Container App up (Builds container in cloud)
    echo "[*] Building and deploying Munzir Container App..."
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

    # 4. Set High-Performance Configuration (1.0 vCPU, 2.0 GiB, minReplicas 1 initially for immediate warm response)
    echo "[*] Applying High-Performance tier (${CPU_CORES} vCPU, ${MEMORY_SIZE} RAM, minReplicas=1 warm)..."
    az containerapp update \
        --name "${APP_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --min-replicas 1 \
        --max-replicas 1 \
        --cpu "${CPU_CORES}" \
        --memory "${MEMORY_SIZE}" \
        --output none

    echo "================================================================================"
    echo "[+] Munzir Successfully Deployed and Warmed on Azure!"
    echo "[+] Public URL: https://${APP_FQDN}"
    echo "[+] Mode: WARM (minReplicas=1, zero cold start, sub-10ms response)"
    echo ""
    echo "Operational Commands:"
    echo "  - Put to sleep (save quota):   ./infra/deploy_student.sh sleep"
    echo "  - Wake up for judging:         ./infra/deploy_student.sh warm"
    echo "  - Check status:                ./infra/deploy_student.sh status"
    echo "================================================================================"
}

cmd_warm() {
    check_az_login
    echo "[*] Warming container ${APP_NAME} (minReplicas=1, zero cold start)..."
    az containerapp update \
        --name "${APP_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --min-replicas 1 \
        --output none
    echo "[+] Container is warm and running at peak performance."
}

cmd_sleep() {
    check_az_login
    echo "[*] Putting container ${APP_NAME} to sleep (minReplicas=0, $0.00 idle cost)..."
    az containerapp update \
        --name "${APP_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --min-replicas 0 \
        --output none
    echo "[+] Container scaled to zero. Free tier quota preserved."
}

cmd_status() {
    check_az_login
    echo "================================================================================"
    echo "Munzir Container Status: ${APP_NAME} (${RESOURCE_GROUP})"
    echo "================================================================================"
    az containerapp show \
        --name "${APP_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --query "{Name:name, ProvisioningState:properties.provisioningState, FQDN:properties.configuration.ingress.fqdn, MinReplicas:properties.template.scale.minReplicas, MaxReplicas:properties.template.scale.maxReplicas, CPU:properties.template.containers[0].resources.cpu, Memory:properties.template.containers[0].resources.memory}" \
        --output table
    echo "================================================================================"
}

case "${ACTION}" in
    up|deploy)
        cmd_up
        ;;
    warm|start|active)
        cmd_warm
        ;;
    sleep|idle|stop)
        cmd_sleep
        ;;
    status|info)
        cmd_status
        ;;
    cost|budget)
        cmd_cost
        ;;
    *)
        echo "Usage: $0 [up|warm|sleep|status|cost]"
        echo "  up      : Deploy or update container with high performance tier (default)"
        echo "  warm    : Set min-replicas=1 for zero cold-start latency during presentations"
        echo "  sleep   : Set min-replicas=0 to pause execution and preserve quota"
        echo "  status  : View current provisioning state, FQDN, and replica scale"
        echo "  cost    : View 5-hour consumption and free allowance calculation"
        exit 1
        ;;
esac

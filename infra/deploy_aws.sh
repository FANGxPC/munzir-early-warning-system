#!/usr/bin/env bash
# ==============================================================================
# Munzir (منذر) - AWS Free Tier EC2 Deployment Controller
# Deploys on 100% Free Tier (t2.micro / t3.micro) with $0.00 Cost
# ==============================================================================
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"

INSTANCE_NAME="${INSTANCE_NAME:-munzir-platform}"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-ap-south-1}}"
INSTANCE_TYPE="${INSTANCE_TYPE:-t3.micro}"
SECURITY_GROUP_NAME="munzir-sg"
USER_DATA_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/ec2_user_data.sh"

check_aws_cli() {
    if ! command -v aws >/dev/null 2>&1; then
        echo "[!] AWS CLI is not installed on this machine."
        echo "    Install with: sudo apt-get install -y awscli   (or use AWS Web Console)"
        exit 1
    fi
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        echo "[!] AWS CLI credentials not configured. Please run: aws configure"
        exit 1
    fi
    local account_id
    account_id=$(aws sts get-caller-identity --query "Account" --output text)
    echo "[*] Connected to AWS Account ID: ${account_id} (Region: ${REGION})"
}

cmd_up() {
    check_aws_cli

    echo "================================================================================"
    echo "Munzir AWS Free Tier Deployment"
    echo "Instance:       ${INSTANCE_NAME}"
    echo "Type:           ${INSTANCE_TYPE} (AWS Free Tier Eligible: 750 hrs/month)"
    echo "Region:         ${REGION}"
    echo "Cost:           \$0.00 / month (100% within free allowance)"
    echo "================================================================================"

    # 1. Get Default VPC ID
    echo "[*] Resolving default VPC..."
    VPC_ID=$(aws ec2 describe-vpcs --region "${REGION}" --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text)
    if [ -z "${VPC_ID}" ] || [ "${VPC_ID}" = "None" ]; then
        echo "[!] No default VPC found. Using first available VPC..."
        VPC_ID=$(aws ec2 describe-vpcs --region "${REGION}" --query "Vpcs[0].VpcId" --output text)
    fi
    echo "[+] Using VPC: ${VPC_ID}"

    # 2. Create or verify Security Group
    SG_ID=$(aws ec2 describe-security-groups --region "${REGION}" --filters "Name=group-name,Values=${SECURITY_GROUP_NAME}" "Name=vpc-id,Values=${VPC_ID}" --query "SecurityGroups[0].GroupId" --output text 2>/dev/null || true)
    if [ -z "${SG_ID}" ] || [ "${SG_ID}" = "None" ]; then
        echo "[*] Creating Security Group: ${SECURITY_GROUP_NAME}..."
        SG_ID=$(aws ec2 create-security-group --region "${REGION}" --group-name "${SECURITY_GROUP_NAME}" --description "Munzir Early Warning System Ports 80, 8000, 22" --vpc-id "${VPC_ID}" --query "GroupId" --output text)
        
        # Authorize Port 80 (HTTP), 443 (HTTPS), 8000 (API/Web), and 22 (SSH)
        aws ec2 authorize-security-group-ingress --region "${REGION}" --group-id "${SG_ID}" --protocol tcp --port 80 --cidr 0.0.0.0/0 >/dev/null
        aws ec2 authorize-security-group-ingress --region "${REGION}" --group-id "${SG_ID}" --protocol tcp --port 443 --cidr 0.0.0.0/0 >/dev/null
        aws ec2 authorize-security-group-ingress --region "${REGION}" --group-id "${SG_ID}" --protocol tcp --port 8000 --cidr 0.0.0.0/0 >/dev/null
        aws ec2 authorize-security-group-ingress --region "${REGION}" --group-id "${SG_ID}" --protocol tcp --port 22 --cidr 0.0.0.0/0 >/dev/null
        echo "[+] Security Group created: ${SG_ID}"
    else
        echo "[+] Using existing Security Group: ${SG_ID}"
    fi

    # 3. Find latest Ubuntu 22.04 LTS AMI in region
    echo "[*] Resolving latest Ubuntu 22.04 LTS AMI..."
    AMI_ID=$(aws ec2 describe-images --region "${REGION}" --owners 099720109477 \
        --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" "Name=state,Values=available" \
        --query "sort_by(Images, &CreationDate)[-1].ImageId" --output text)
    echo "[+] Target AMI: ${AMI_ID}"

    # 4. Launch EC2 Free Tier Instance with 20 GB Free Tier EBS Volume
    echo "[*] Launching Free Tier EC2 instance (${INSTANCE_TYPE}, 20 GB gp3)..."
    INSTANCE_ID=$(aws ec2 run-instances \
        --region "${REGION}" \
        --image-id "${AMI_ID}" \
        --instance-type "${INSTANCE_TYPE}" \
        --security-group-ids "${SG_ID}" \
        --user-data "file://${USER_DATA_PATH}" \
        --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":20,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${INSTANCE_NAME}},{Key=Project,Value=Munzir}]" \
        --query "Instances[0].InstanceId" --output text)
    echo "[+] Instance Created: ${INSTANCE_ID}"

    echo "[*] Waiting for instance to obtain public IP..."
    aws ec2 wait instance-running --region "${REGION}" --instance-ids "${INSTANCE_ID}"
    PUBLIC_IP=$(aws ec2 describe-instances --region "${REGION}" --instance-ids "${INSTANCE_ID}" --query "Reservations[0].Instances[0].PublicIpAddress" --output text)

    echo ""
    echo "================================================================================"
    echo "[SUCCESS] Munzir Free Tier Instance is Booting!"
    echo "Instance ID:  ${INSTANCE_ID}"
    echo "Public IP:    ${PUBLIC_IP}"
    echo "Live URL:     http://${PUBLIC_IP} (or http://${PUBLIC_IP}:8000)"
    echo "Status:       Docker build & launch in progress via cloud-init (~2-3 mins)."
    echo "================================================================================"
}

cmd_status() {
    check_aws_cli
    aws ec2 describe-instances --region "${REGION}" \
        --filters "Name=tag:Name,Values=${INSTANCE_NAME}" "Name=instance-state-name,Values=running,pending" \
        --query "Reservations[*].Instances[*].[InstanceId, State.Name, PublicIpAddress, LaunchTime]" --output table
}

cmd_down() {
    check_aws_cli
    echo "[*] Finding running Munzir instances..."
    IDS=$(aws ec2 describe-instances --region "${REGION}" \
        --filters "Name=tag:Name,Values=${INSTANCE_NAME}" "Name=instance-state-name,Values=running,pending" \
        --query "Reservations[*].Instances[*].InstanceId" --output text)
    if [ -z "${IDS}" ] || [ "${IDS}" = "None" ]; then
        echo "[*] No active instances found."
    else
        echo "[*] Terminating instance(s): ${IDS}..."
        aws ec2 terminate-instances --region "${REGION}" --instance-ids ${IDS} >/dev/null
        echo "[+] Terminated successfully. No ongoing costs."
    fi
}

case "${1:-up}" in
    up)     cmd_up ;;
    status) cmd_status ;;
    down)   cmd_down ;;
    *)      echo "Usage: $0 {up|status|down}" ; exit 1 ;;
esac


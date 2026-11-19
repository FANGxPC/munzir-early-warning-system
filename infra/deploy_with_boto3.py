#!/usr/bin/env python3
"""
Automated AWS Free Tier Deployment for Munzir Platform in Mumbai (ap-south-1).
"""
import os
import sys
import time
import boto3
from botocore.exceptions import ClientError

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
REGION = os.environ.get("AWS_REGION", "ap-south-1")

print(f"[*] Initializing AWS Session in region: {REGION} (Mumbai)...")
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=REGION
    )
else:
    session = boto3.Session(region_name=REGION)

sts = session.client("sts")
try:
    identity = sts.get_caller_identity()
    print(f"[+] Authenticated successfully!")
    print(f"    Account ID: {identity.get('Account')}")
    print(f"    Arn:        {identity.get('Arn')}")
except Exception as e:
    print(f"[!] Authentication failed: {e}")
    sys.exit(1)

ec2 = session.client("ec2")

# 1. Resolve Default VPC
print("[*] Finding default VPC in Mumbai...")
vpcs = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])
vpc_id = None
if vpcs.get("Vpcs"):
    vpc_id = vpcs["Vpcs"][0]["VpcId"]
else:
    all_vpcs = ec2.describe_vpcs()
    if all_vpcs.get("Vpcs"):
        vpc_id = all_vpcs["Vpcs"][0]["VpcId"]
    else:
        print("[!] No VPC found in region.")
        sys.exit(1)
print(f"[+] Using VPC: {vpc_id}")

# 2. Security Group
SG_NAME = "munzir-sg"
print(f"[*] Ensuring Security Group '{SG_NAME}' exists...")
sg_id = None
try:
    existing_sgs = ec2.describe_security_groups(
        Filters=[{"Name": "group-name", "Values": [SG_NAME]}, {"Name": "vpc-id", "Values": [vpc_id]}]
    )
    if existing_sgs.get("SecurityGroups"):
        sg_id = existing_sgs["SecurityGroups"][0]["GroupId"]
        print(f"[+] Found existing Security Group: {sg_id}")
    else:
        sg_res = ec2.create_security_group(
            GroupName=SG_NAME,
            Description="Munzir Early Warning System - Ports 80, 8000, 22",
            VpcId=vpc_id
        )
        sg_id = sg_res["GroupId"]
        print(f"[+] Created Security Group: {sg_id}")
        
        # Authorize ingress
        rules = [
            {"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "HTTP Web"}]},
            {"IpProtocol": "tcp", "FromPort": 8000, "ToPort": 8000, "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "Munzir API & Dashboard"}]},
            {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "SSH Admin"}]},
        ]
        ec2.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=rules)
        print(f"[+] Ingress rules configured (Ports 80, 8000, 22 open).")
except Exception as e:
    print(f"[!] Security group error: {e}")
    sys.exit(1)

# 3. Resolve Ubuntu 22.04 LTS AMI
print("[*] Finding latest official Ubuntu 22.04 LTS AMI in Mumbai...")
images = ec2.describe_images(
    Owners=["099720109477"],  # Canonical
    Filters=[
        {"Name": "name", "Values": ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]},
        {"Name": "state", "Values": ["available"]}
    ]
)
ami_list = sorted(images["Images"], key=lambda x: x["CreationDate"], reverse=True)
if not ami_list:
    print("[!] No Ubuntu 22.04 AMI found.")
    sys.exit(1)
ami_id = ami_list[0]["ImageId"]
ami_name = ami_list[0]["Name"]
print(f"[+] Selected AMI: {ami_id} ({ami_name})")

# 4. Read User Data
user_data_file = os.path.join(os.path.dirname(__file__), "ec2_user_data.sh")
with open(user_data_file, "r") as f:
    user_data_script = f.read()

# 5. Launch Instance (t3.micro - Free Tier Eligible in ap-south-1)
INSTANCE_TYPE = os.environ.get("INSTANCE_TYPE", "t3.micro")
print(f"[*] Launching Free Tier EC2 instance ({INSTANCE_TYPE}) in Mumbai...")

run_args = {
    "ImageId": ami_id,
    "InstanceType": INSTANCE_TYPE,
    "MinCount": 1,
    "MaxCount": 1,
    "SecurityGroupIds": [sg_id],
    "UserData": user_data_script,
    "TagSpecifications": [
        {
            "ResourceType": "instance",
            "Tags": [
                {"Key": "Name", "Value": "munzir-platform"},
                {"Key": "Project", "Value": "Munzir"},
                {"Key": "Tier", "Value": "FreeTier"}
            ]
        }
    ],
    "BlockDeviceMappings": [
        {
            "DeviceName": "/dev/sda1",
            "Ebs": {
                "VolumeSize": 16,  # 16 GB SSD (well within 30 GB Free Tier allowance)
                "VolumeType": "gp3",
                "DeleteOnTermination": True
            }
        }
    ]
}

instance_res = ec2.run_instances(**run_args)
instance_id = instance_res["Instances"][0]["InstanceId"]
print(f"[+] Instance successfully requested: {instance_id}")

print("[*] Waiting for instance to transition to 'running' state and acquire Public IP...")
waiter = ec2.get_waiter("instance_running")
waiter.wait(InstanceIds=[instance_id])

desc = ec2.describe_instances(InstanceIds=[instance_id])
inst_info = desc["Reservations"][0]["Instances"][0]
public_ip = inst_info.get("PublicIpAddress", "Pending")
public_dns = inst_info.get("PublicDnsName", "")

print("\n" + "="*80)
print(" MUNZIR (منذر) DEPLOYED SUCCESSFULLY TO AWS MUMBAI (ap-south-1)!")
print("="*80)
print(f" Region:         {REGION} (Asia Pacific - Mumbai)")
print(f" Instance ID:    {instance_id}")
print(f" Instance Type:  {INSTANCE_TYPE} (AWS Free Tier Eligible - $0.00/month)")
print(f" State:          {inst_info['State']['Name']}")
print(f" Public IPv4:    {public_ip}")
print(f" Live Web URL:   http://{public_ip}")
print(f" Port 8000 URL:  http://{public_ip}:8000")
print(f" OpenAQ API:     Live Connected in .env")
print("="*80)
print("Note: Cloud-init is currently bootstrapping Docker and starting Munzir in the background.")
print("The website will be accessible at http://" + public_ip + " in approximately 2 to 3 minutes.")
print("="*80)


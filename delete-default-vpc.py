#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#  "boto3~=1.36.19",
# ]
# ///
"""
AWS Default VPC Deletion Tool.

This script deletes default VPCs across all AWS regions. It handles the deletion
of VPC dependencies in the correct order to ensure clean removal.
"""

import concurrent.futures
import os
import sys

import boto3
from boto3.resources.base import ServiceResource
from botocore.client import BaseClient

# Type aliases
type EC2Client = BaseClient
type EC2Resource = ServiceResource
type VPCResource = ServiceResource

VERBOSE: bool = True
THREADPOOL_MAX_WORKERS: int = 20


def get_regions(client: EC2Client) -> list[str]:
    """
    Fetch a list of available AWS regions.

    Args:
        client: Boto3 EC2 client instance

    Returns:
        List of region names

    """
    regions = client.describe_regions()
    return [region["RegionName"] for region in regions["Regions"]]


def get_default_vpcs(client: EC2Client) -> list[str]:
    """
    Retrieve all default VPCs in a region.

    Args:
        client: Boto3 EC2 client instance

    Returns:
        List of VPC IDs

    """
    vpcs = client.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])
    return [vpc["VpcId"] for vpc in vpcs["Vpcs"]]


def del_igw(ec2: EC2Resource, vpc_id: str) -> None:
    """
    Detach and delete all internet gateways associated with the VPC.

    Args:
        ec2: Boto3 EC2 resource instance
        vpc_id: ID of the VPC

    """
    vpc_resource = ec2.Vpc(vpc_id)
    for igw in vpc_resource.internet_gateways.all():
        try:
            if VERBOSE:
                print(f"Detaching and Removing igw-id: {igw.id}")
            igw.detach_from_vpc(VpcId=vpc_id)
            igw.delete()
        except boto3.exceptions.Boto3Error as e:
            print(f"Error deleting IGW {igw.id}: {e}")


def del_sub(ec2: EC2Resource, vpc_id: str) -> None:
    """
    Delete all default subnets in the VPC.

    Args:
        ec2: Boto3 EC2 resource instance
        vpc_id: ID of the VPC

    """
    vpc_resource = ec2.Vpc(vpc_id)
    subnets = vpc_resource.subnets.all()
    default_subnets = [
        ec2.Subnet(subnet.id) for subnet in subnets if subnet.default_for_az
    ]

    for subnet in default_subnets:
        try:
            if VERBOSE:
                print(f"Removing subnet-id: {subnet.id}")
            subnet.delete()
        except boto3.exceptions.Boto3Error as e:
            print(f"Error deleting subnet {subnet.id}: {e}")


def del_rtb(ec2: EC2Resource, vpc_id: str) -> None:
    """
    Delete all non-main route tables in the VPC.

    Args:
        ec2: Boto3 EC2 resource instance
        vpc_id: ID of the VPC to process

    """
    vpc_resource = ec2.Vpc(vpc_id)
    for rtb in vpc_resource.route_tables.all():
        try:
            if any(assoc.get("Main", False) for assoc in rtb.associations_attribute):
                if VERBOSE:
                    print(f"{rtb.id} is the main route table, skipping...")
                continue
            if VERBOSE:
                print(f"Removing rtb-id: {rtb.id}")
            rtb.delete()
        except boto3.exceptions.Boto3Error as e:
            print(f"Error deleting route table {rtb.id}: {e}")


def del_acl(ec2: EC2Resource, vpc_id: str) -> None:
    """
    Delete all non-default network ACLs in the VPC.

    Args:
        ec2: Boto3 EC2 resource instance
        vpc_id: ID of the VPC to process

    """
    vpc_resource = ec2.Vpc(vpc_id)
    for acl in vpc_resource.network_acls.all():
        try:
            if acl.is_default:
                if VERBOSE:
                    print(f"{acl.id} is the default NACL, skipping...")
                continue
            if VERBOSE:
                print(f"Removing acl-id: {acl.id}")
            acl.delete()
        except boto3.exceptions.Boto3Error as e:
            print(f"Error deleting NACL {acl.id}: {e}")


def del_sgp(ec2: EC2Resource, vpc_id: str) -> None:
    """
    Delete all non-default security groups in the VPC.

    Args:
        ec2: Boto3 EC2 resource instance
        vpc_id: ID of the VPC to process

    """
    vpc_resource = ec2.Vpc(vpc_id)
    for sg in vpc_resource.security_groups.all():
        try:
            if sg.group_name == "default":
                if VERBOSE:
                    print(f"{sg.id} is the default security group, skipping...")
                continue
            if VERBOSE:
                print(f"Removing sg-id: {sg.id}")
            sg.delete()
        except boto3.exceptions.Boto3Error as e:
            print(f"Error deleting security group {sg.id}: {e}")


def del_vpc(ec2: EC2Resource, vpc_id: str) -> None:
    """
    Delete the VPC itself.

    Args:
        ec2: Boto3 EC2 resource instance
        vpc_id: ID of the VPC to delete

    """
    vpc_resource = ec2.Vpc(vpc_id)
    try:
        print(f"Removing vpc-id: {vpc_resource.id}")
        vpc_resource.delete()
    except boto3.exceptions.Boto3Error as e:
        print(f"Error deleting VPC {vpc_id}: {e}")
        print("Please remove dependencies and delete VPC manually.")


def del_vpc_all(ec2: EC2Resource, vpc_id: str) -> None:
    """
    Delete a VPC and all its dependencies in the correct order.

    The deletion order is:
    1. Internet gateways
    2. Subnets
    3. Route tables
    4. Network ACLs
    5. Security groups
    6. VPC

    Args:
        ec2: Boto3 EC2 resource instance
        vpc_id: ID of the VPC to delete

    """
    del_igw(ec2, vpc_id)
    del_sub(ec2, vpc_id)
    del_rtb(ec2, vpc_id)
    del_acl(ec2, vpc_id)
    del_sgp(ec2, vpc_id)
    del_vpc(ec2, vpc_id)


def main() -> None:
    """Identify all active regions and remove VPCs and related resources."""
    client = boto3.client("ec2")
    regions = get_regions(client)

    max_workers = int(os.getenv("MAX_WORKERS", THREADPOOL_MAX_WORKERS))
    futures = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for region in regions:
            try:
                client = boto3.client("ec2", region_name=region)
                ec2 = boto3.resource("ec2", region_name=region)
                vpcs = get_default_vpcs(client)
            except boto3.exceptions.Boto3Error as e:
                print(f"Error accessing region {region}: {e}")
                continue

            for vpc in vpcs:
                print(f"\n\nREGION: {region}\nVPC Id: {vpc}")
                futures.append(executor.submit(del_vpc_all, ec2, vpc))

    concurrent.futures.wait(futures)
    print("Deleted all default VPCs")


if __name__ == "__main__":
    main()

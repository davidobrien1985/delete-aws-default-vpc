#!/usr/bin/env python
# Must be the first line
from __future__ import print_function

import concurrent.futures
import sys
import os
import json
import boto3

VERBOSE = 1
THREADPOOL_MAX_WORKERS = 20

def get_regions(client):
  """ Build a region list """

  reg_list = []
  regions = client.describe_regions()
  data_str = json.dumps(regions)
  resp = json.loads(data_str)
  region_str = json.dumps(resp['Regions'])
  region = json.loads(region_str)
  for reg in region:
    reg_list.append(reg['RegionName'])
  return reg_list

def get_default_vpcs(client):
  vpc_list = []
  vpcs = client.describe_vpcs(
    Filters=[
      {
          'Name' : 'isDefault',
          'Values' : [
            'true',
          ],
      },
    ]
  )
  vpcs_str = json.dumps(vpcs)
  resp = json.loads(vpcs_str)
  data = json.dumps(resp['Vpcs'])
  vpcs = json.loads(data)
  
  for vpc in vpcs:
    vpc_list.append(vpc['VpcId'])  
  
  return vpc_list

def del_igw(ec2, vpcid):
  """ Detach and delete the internet-gateway """
  vpc_resource = ec2.Vpc(vpcid)
  igws = vpc_resource.internet_gateways.all()
  if igws:
    for igw in igws:
      try:
        print("Detaching and Removing igw-id: ", igw.id) if (VERBOSE == 1) else ""
        igw.detach_from_vpc(
          VpcId=vpcid
        )
        igw.delete(
          # DryRun=True
        )
      except boto3.exceptions.Boto3Error as e:
        print(e)

def del_sub(ec2, vpcid):
  """ Delete the subnets """
  vpc_resource = ec2.Vpc(vpcid)
  subnets = vpc_resource.subnets.all()
  default_subnets = [ec2.Subnet(subnet.id) for subnet in subnets if subnet.default_for_az]
  
  if default_subnets:
    try:
      for sub in default_subnets: 
        print("Removing sub-id: ", sub.id) if (VERBOSE == 1) else ""
        sub.delete(
          # DryRun=True
        )
    except boto3.exceptions.Boto3Error as e:
      print(e)

def del_rtb(ec2, vpcid):
  """ Delete the route-tables """
  vpc_resource = ec2.Vpc(vpcid)
  rtbs = vpc_resource.route_tables.all()
  if rtbs:
    try:
      for rtb in rtbs:
        assoc_attr = [rtb.associations_attribute for rtb in rtbs]
        if [rtb_ass[0]['RouteTableId'] for rtb_ass in assoc_attr if rtb_ass[0]['Main'] == True]:
          print(rtb.id + " is the main route table, continue...")
          continue
        print("Removing rtb-id: ", rtb.id) if (VERBOSE == 1) else ""
        table = ec2.RouteTable(rtb.id)
        table.delete(
          # DryRun=True
        )
    except boto3.exceptions.Boto3Error as e:
      print(e)

def del_acl(ec2, vpcid):
  """ Delete the network-access-lists """
  
  vpc_resource = ec2.Vpc(vpcid)      
  acls = vpc_resource.network_acls.all()

  if acls:
    try:
      for acl in acls: 
        if acl.is_default:
          print(acl.id + " is the default NACL, continue...")
          continue
        print("Removing acl-id: ", acl.id) if (VERBOSE == 1) else ""
        acl.delete(
          # DryRun=True
        )
    except boto3.exceptions.Boto3Error as e:
      print(e)

def del_sgp(ec2, vpcid):
  """ Delete any security-groups """
  vpc_resource = ec2.Vpc(vpcid)
  sgps = vpc_resource.security_groups.all()
  if sgps:
    try:
      for sg in sgps: 
        if sg.group_name == 'default':
          print(sg.id + " is the default security group, continue...")
          continue
        print("Removing sg-id: ", sg.id) if (VERBOSE == 1) else ""
        sg.delete(
          # DryRun=True
        )
    except boto3.exceptions.Boto3Error as e:
      print(e)

def del_vpc(ec2, vpcid):
  """ Delete the VPC """
  vpc_resource = ec2.Vpc(vpcid)
  try:
    print("Removing vpc-id: ", vpc_resource.id)
    vpc_resource.delete(
      # DryRun=True
    )
  except boto3.exceptions.Boto3Error as e:
      print(e)
      print("Please remove dependencies and delete VPC manually.")
  #finally:
  #  return status

def del_vpc_all(ec2, vpc):
  """
  Do the work - order of operation

  1.) Delete the internet-gateway
  2.) Delete subnets
  3.) Delete route-tables
  4.) Delete network access-lists
  5.) Delete security-groups
  6.) Delete the VPC 
  """
  del_igw(ec2, vpc)
  del_sub(ec2, vpc)
  del_rtb(ec2, vpc)
  del_acl(ec2, vpc)
  del_sgp(ec2, vpc)
  del_vpc(ec2, vpc)

def main(keyid, secret):
  client = boto3.client('ec2')
  regions = get_regions(client)
  
  futures = []
  with concurrent.futures.ThreadPoolExecutor(max_workers=int(os.getenv("MAX_WORKERS", THREADPOOL_MAX_WORKERS))) as executor:
    for region in regions:
      try:
        client = boto3.client('ec2', region_name = region)
        ec2 = boto3.resource('ec2', region_name = region)
        vpcs = get_default_vpcs(client)
      except boto3.exceptions.Boto3Error as e:
        print(e)
        exit(1)

      for vpc in vpcs:
        print("\n" + "\n" + "REGION:" + region + "\n" + "VPC Id:" + vpc)
        futures.append(executor.submit(
            del_vpc_all,
            ec2,
            vpc,
        ))
  concurrent.futures.wait(futures)
  print('Deleted all default VPCs')

if __name__ == "__main__":
  main(keyid = 'XXXX', secret = 'XXXX')

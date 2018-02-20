# Delete all default AWS VPCs in all regions

This python script will delete *ALL* default resources in *every* default VPC in *every* AWS region.
This also applies to custom VPCs that have been created by users and then flagged as the new "default VPC".

> I am not responsible for any data loss or damage!

Ideally this script gets run after an AWS account gets created.

## Usage

For ease of use on Windows the `execute.ps1` will take two parameters:

* `aws_profile`
  * the name of your configured AWS CLI profile
* `aws_region`
  * the name of the AWS region that initially you will authenticate to

Example:
`.\execute.ps1 -aws_profile sandpit -aws_region ap-southeast-2`

### Requirements

The following requirements exist:

* configured AWS profile locally on host
* docker for Windows
  * the python script will be executed from inside the container and call the AWS APIs from there

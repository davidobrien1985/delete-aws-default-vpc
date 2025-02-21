# Delete all default AWS VPCs in all regions

This python script will delete *ALL* default resources in *every* default VPC in *every* AWS region.
This also applies to custom VPCs that have been created by users and then flagged as the new "default VPC".

> I am not responsible for any data loss or damage!

Ideally this script gets run after an AWS account gets created.

## Usage

### *nix

If you have `uv` installed, you can run the script `./delete-default-vpc.py`. `uv` will pull in the dependencies for you.

If you prefer to use `pip`, run the following commands:

* Optionally create and activate a virtual env.
* `pip install .`
* `python delete-default-vpc.py`

To remove the default VPC from all regions in all accounts in your organization run the following oneliner with admin credentials from the root account:

```sh
# with uv
./delete-default-vpc.py && for account in $(aws organizations list-accounts | jq -r '.Accounts[].Id' | grep -v $(aws sts get-caller-identity | jq -r '.Account')); do creds=$(aws sts assume-role --role-arn "arn:aws:iam::${account}:role/OrganizationAccountAccessRole" --role-session-name "delete-vpc" --output json) && AWS_ACCESS_KEY_ID=$(echo $creds | jq -r '.Credentials.AccessKeyId') AWS_SECRET_ACCESS_KEY=$(echo $creds | jq -r '.Credentials.SecretAccessKey') AWS_SESSION_TOKEN=$(echo $creds | jq -r '.Credentials.SessionToken') ./delete-default-vpc.py; done; 

# with pip
python ./delete-default-vpc.py && for account in $(aws organizations list-accounts | jq -r '.Accounts[].Id' | grep -v $(aws sts get-caller-identity | jq -r '.Account')); do creds=$(aws sts assume-role --role-arn "arn:aws:iam::${account}:role/OrganizationAccountAccessRole" --role-session-name "delete-vpc" --output json) && AWS_ACCESS_KEY_ID=$(echo $creds | jq -r '.Credentials.AccessKeyId') AWS_SECRET_ACCESS_KEY=$(echo $creds | jq -r '.Credentials.SecretAccessKey') AWS_SESSION_TOKEN=$(echo $creds | jq -r '.Credentials.SessionToken') python ./delete-default-vpc.py; done; 
```

### Windows

For ease of use on Windows the `execute.ps1` will take two parameters:

* `aws_profile`
  * the name of your configured AWS CLI profile
* `aws_region`
  * the name of the AWS region that initially you will authenticate to

Example:
`.\execute.ps1 -aws_profile sandpit -aws_region ap-southeast-2`

#### Requirements

The following requirements exist:

* configured AWS profile locally on host
* docker for Windows
  * the python script will be executed from inside the container and call the AWS APIs from there

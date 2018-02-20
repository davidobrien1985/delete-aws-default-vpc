param (
    [string]$aws_profile,
    [string]$aws_region
)

$aws_creds = (Get-AWSCredential -ProfileLocation $(Join-Path $env:USERPROFILE .aws\credentials) -ProfileName $aws_profile).GetCredentials()
$AWS_ACCESS_KEY_ID= $aws_creds.AccessKey 
$AWS_SECRET_ACCESS_KEY= $aws_creds.SecretKey
$AWS_SESSION_TOKEN = $aws_creds.Token
$AWS_SECURITY_TOKEN = $aws_creds.Token
$AWS_DEFAULT_REGION= $aws_region


$location = (Get-Location).Path

docker pull davidobrien/centos_ansible_powershell:latest
docker run -it -e AWS_SECURITY_TOKEN=$AWS_SECURITY_TOKEN -e AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION -v ${location}:/run -t davidobrien/centos_ansible_powershell python run/delete-default-vpc.py

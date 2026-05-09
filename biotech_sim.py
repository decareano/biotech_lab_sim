import boto3
from botocore.exceptions import ClientError


def get_aws_secret():
    client = boto3.client("secretsmanager", region_name="us-east-1")
    try:
        response = client.get_secret_value(SecretId="biotech/lims/api_key")
        return response["SecretString"]
    except ClientError as e:
        print(f"❌ Could not fetch secret: {e}")
        raise PermissionError("AWS Authentication Failed")


def validate_api_access(provided_token):
    # Fetch the secret we just made with Terraform
    real_key = get_aws_secret()

    if provided_token != real_key:
        raise PermissionError("Security Error: Invalid API key.")

    print("🔑 AWS Secrets Manager verified access.")

import boto3

from src.config import AWS_REGION

client = boto3.client(
    service_name="bedrock-runtime",
    region_name=AWS_REGION
)
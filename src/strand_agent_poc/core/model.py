import os
import boto3
from strands.models import BedrockModel
from dotenv import load_dotenv

load_dotenv()

session = boto3.Session(
    # use BEARER_TOKEN_BEDROCK instead, can be set in .env file
    region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-2"),
    # profile_name=os.getenv("AWS_PROFILE", "default"),
)

# Claude 3.7 Sonnet model for executor
bedrock37Model = BedrockModel(
    model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0", boto_session=session
)

# Claude 4 Sonnet model for planner
claude4Model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0", boto_session=session
)

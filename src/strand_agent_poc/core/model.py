
import boto3
from strands.models import BedrockModel


session = boto3.Session(
    region_name='us-east-1',
    profile_name='ihailong-Admin'  # Optional: Use a specific profile
)

# Claude 3.7 Sonnet model for executor
bedrockModel = BedrockModel(
    model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    boto_session=session
)

# Claude 4 Sonnet model for planner
claude4Model = BedrockModel(
    model_id="anthropic.claude-sonnet-4-20250514-v1:0",
    boto_session=session
)
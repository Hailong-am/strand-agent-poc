from mcp import stdio_client, StdioServerParameters
from strands import Agent, tool
from strands.tools.mcp import MCPClient
import logging
import os
from dotenv import load_dotenv

from . import model

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
# Add a handler to see the logs
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Connect to an MCP server using stdio transport
# Note: uvx command syntax differs by platform

stdio_mcp_client = MCPClient(lambda: stdio_client(
    StdioServerParameters(
        command="uvx",
        args=["opensearch-mcp-server-py"],
        env={
            "OPENSEARCH_URL": os.getenv("OPENSEARCH_URL"),
            "OPENSEARCH_USERNAME": os.getenv("OPENSEARCH_USERNAME"),
            "OPENSEARCH_PASSWORD": os.getenv("OPENSEARCH_PASSWORD"),
            "OPENSEARCH_SSL_VERIFY": os.getenv("OPENSEARCH_SSL_VERIFY")
        }
    )
))

def get_executor_prompt() -> str:
    """Get the executor system prompt"""
    return """You are a precise and reliable executor agent in a plan-execute-reflect framework. Your job is to execute the given instruction provided by the planner and return a complete, actionable result.

Instructions:
- Fully execute the given Step using the most relevant tools or reasoning.
- Include all relevant raw tool outputs (e.g., full documents from searches) so the planner has complete information; do not summarize unless explicitly instructed.
- Base your execution and conclusions only on the data and tool outputs available; do not rely on unstated knowledge or external facts.
- If the available data is insufficient to complete the Step, summarize what was obtained so far and clearly state the additional information or access required to proceed (do not guess).
- If unable to complete the Step, clearly explain what went wrong and what is needed to proceed.
- Avoid making assumptions and relying on implicit knowledge.
- Your response must be self-contained and ready for the planner to use without modification. Never end with a question.
- Break complex searches into simpler queries when appropriate."""


def executor_agent(task: str) -> str:
    logger.info(f"Executor received task: {task}")

    try:
        # Create an agent with MCP tools
        with stdio_mcp_client:
            # Get the tools from the MCP server
            tools = stdio_mcp_client.list_tools_sync()

            # Create an agent with these tools
            executor_agent = Agent(
                model=model.bedrockModel,
                system_prompt=get_executor_prompt(),
                callback_handler=PrintingCallbackHandler(),
                tools=tools, # tools to query opensearch data and indexes
            )

            # Add observability by wrapping the agent call
            agent_result = executor_agent(task)
            return str(agent_result)
    except Exception as e:
        error_msg = f"Error in executor agent: {str(e)}"
        logger.error(error_msg)
        return error_msg
        return error_msg


if __name__ == "__main__":
    # Example usage of the executor_agent tool
    task = "Can you help to investigate high CPU for ad service in log index ss4o_logs-otel-* index for past 2 days?"
    response = executor_agent(task)
    print(f"Response from executor_agent: {response}")
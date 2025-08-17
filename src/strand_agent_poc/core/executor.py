import json
from mcp import stdio_client, StdioServerParameters
from strands import Agent, tool
from strands_tools import current_time
from strands.tools.mcp import MCPClient
import os
from dotenv import load_dotenv
from strands.agent.conversation_manager import SummarizingConversationManager
from . import model
from strands.hooks import HookProvider, HookRegistry
from strands.experimental.hooks import (
    BeforeToolInvocationEvent,
    AfterToolInvocationEvent,
)

# Load environment variables
load_dotenv()


class LoggingHook(HookProvider):
    def register_hooks(self, registry: HookRegistry, **kwargs) -> None:
        registry.add_callback(BeforeToolInvocationEvent, self.log_start)
        # registry.add_callback(AfterToolInvocationEvent, self.log_end)

    def log_start(self, event: BeforeToolInvocationEvent) -> None:
        input = event.tool_use["input"]
        input_json = (
            json.dumps(json.loads(input), indent=2) if isinstance(input, str) else input
        )
        print(
            f"Request started for agent: {event.tool_use['name']} with input: {input_json}"
        )

    # def log_end(self, event: AfterToolInvocationEvent) -> None:
    # print(f"Request completed for agent: {event.result}")


# Connect to an MCP server using stdio transport
# Note: uvx command syntax differs by platform
stdio_mcp_client = MCPClient(
    lambda: stdio_client(
        StdioServerParameters(
            command="uvx",
            args=["opensearch-mcp-server-py"],
            env={
                k: v
                for k, v in {
                    "OPENSEARCH_URL": os.getenv("OPENSEARCH_URL"),
                    "OPENSEARCH_USERNAME": os.getenv("OPENSEARCH_USERNAME"),
                    "OPENSEARCH_PASSWORD": os.getenv("OPENSEARCH_PASSWORD"),
                    "OPENSEARCH_SSL_VERIFY": os.getenv("OPENSEARCH_SSL_VERIFY"),
                }.items()
                if v is not None
            },
        )
    )
)


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


from enum import Enum

class InsightType(Enum):
    STATISTICAL_DATA = "STATISTICAL_DATA"
    FIELD_DESCRIPTION = "FIELD_DESCRIPTION"
    LOG_RELATED_INDEX_CHECK = "LOG_RELATED_INDEX_CHECK"

@tool(
    name="index_insight_tool",
    description="Use this tool to get details of one index according to different task type, including STATISTICAL_DATA: the data distribution and index mapping of the index, FIELD_DESCRIPTION: The description of each column, LOG_RELATED_INDEX_CHECK: Whether the index is related to log/trace and whether it contains trace/log fields"
)
def index_insight(index: str, insight_type: InsightType = InsightType.LOG_RELATED_INDEX_CHECK) -> str:
    """Get index insight for given index

    API endpoint: `/_plugins/_ml/insights/${index}/{insight_type}`,

    Args:
        index: The name of the index to get insight for
    """
    from opensearchpy import OpenSearch
    import json

    # Create OpenSearch client
    client = OpenSearch(
        hosts=[os.getenv("OPENSEARCH_URL")],
        http_auth=(os.getenv("OPENSEARCH_USERNAME"), os.getenv("OPENSEARCH_PASSWORD")),
        use_ssl=False,
        verify_certs=False,
        ssl_show_warn=False
    )

    try:
        # Call the ML insights API
        response = client.transport.perform_request(
            method="GET",
            url=f"/_plugins/_ml/insights/{index}/{insight_type.value}",
        )
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting index insight for {index}: {str(e)}"


def get_tool_prompt() -> str:
    with stdio_mcp_client:
        tools = stdio_mcp_client.list_tools_sync()
        tool_descriptions = "\n".join(
            [
                f"Tool {i+1} - {tool.tool_name}: {tool.tool_spec}"
                for i, tool in enumerate(tools)
            ]
        )
        
        # Add index_insight tool description
        index_insight_desc = f"Tool {len(tools)+1} - index_insight_tool: Get ML insights for a given OpenSearch index. Parameters: index (str), insight_type (STATISTICAL_DATA|FIELD_DESCRIPTION|LOG_RELATED_INDEX_CHECK, default: LOG_RELATED_INDEX_CHECK)"
        
        return f"""Available Tools:
In this environment, you have access to the tools listed below. Use these tools to execute the given instruction, and do not reference or use any tools not listed here.
{tool_descriptions}
{index_insight_desc}
No other tools are available. Do not invent tools. Only use tools to execute the instruction.
        """


def executor_agent(task: str) -> str:
    try:
        # Create an agent with MCP tools
        with stdio_mcp_client:
            # Get the tools from the MCP server
            tools = stdio_mcp_client.list_tools_sync()

            # TODO filter tools to only those relevant for the task
            # ['ListIndexTool', 'IndexMappingTool', 'SearchIndexTool', 'GetShardsTool', 'ClusterHealthTool', 'CountTool', 'MsearchTool', 'ExplainTool']

            executor_agent = Agent(
                model=model.bedrock37Model,
                agent_id="executor_agent",
                name="Executor Agent",
                description="Executor agent for executing planner steps",
                system_prompt=get_executor_prompt(),
                hooks=[LoggingHook()],
                conversation_manager=SummarizingConversationManager(
                    summary_ratio=0.3,
                    preserve_recent_messages=10,
                ),
                tools=[*tools, index_insight],  # tools to query opensearch data and indexes
            )

            # Add observability by wrapping the agent call
            agent_result = executor_agent(task)
            return str(agent_result)
    except Exception as e:
        error_msg = f"Error in executor agent: {str(e)}"
        return error_msg


if __name__ == "__main__":
    # Example usage of the executor_agent tool
    task = "Can you help to investigate high CPU for ad service in log index ss4o_logs-otel-* index for past week?"
    response = executor_agent(task)
    print(f"Response from executor_agent: {response}")

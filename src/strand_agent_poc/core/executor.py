import json
from mcp import stdio_client, StdioServerParameters
from strands import Agent
from strands.tools.mcp import MCPClient
import os
from dotenv import load_dotenv
from strands.agent.conversation_manager import SummarizingConversationManager
from . import model
from strands.hooks import HookProvider, HookRegistry
from strands.experimental.hooks import BeforeToolInvocationEvent, AfterToolInvocationEvent

# Load environment variables
load_dotenv()

class LoggingHook(HookProvider):
    def register_hooks(self, registry: HookRegistry, **kwargs) -> None:
        registry.add_callback(BeforeToolInvocationEvent, self.log_start)
        # registry.add_callback(AfterToolInvocationEvent, self.log_end)

    def log_start(self, event: BeforeToolInvocationEvent) -> None:
        input = event.tool_use['input']
        input_json = json.dumps(json.loads(input), indent=2) if isinstance(input, str) else input
        print(f"Request started for agent: {event.tool_use['name']} with input: {input_json}")

    # def log_end(self, event: AfterToolInvocationEvent) -> None:
        # print(f"Request completed for agent: {event.result}")



# Connect to an MCP server using stdio transport
# Note: uvx command syntax differs by platform
stdio_mcp_client = MCPClient(lambda: stdio_client(
    StdioServerParameters(
        command="uvx",
        args=["opensearch-mcp-server-py"],
        env={k: v for k, v in {
            "OPENSEARCH_URL": os.getenv("OPENSEARCH_URL"),
            "OPENSEARCH_USERNAME": os.getenv("OPENSEARCH_USERNAME"),
            "OPENSEARCH_PASSWORD": os.getenv("OPENSEARCH_PASSWORD"),
            "OPENSEARCH_SSL_VERIFY": os.getenv("OPENSEARCH_SSL_VERIFY")
        }.items() if v is not None},
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
    try:
        # Create an agent with MCP tools
        with stdio_mcp_client:
            # Get the tools from the MCP server
            tools = stdio_mcp_client.list_tools_sync()

            # TODO filter tools to only those relevant for the task
            # ['ListIndexTool', 'IndexMappingTool', 'SearchIndexTool', 'GetShardsTool', 'ClusterHealthTool', 'CountTool', 'MsearchTool', 'ExplainTool']

            executor_agent = Agent(
                model=model.bedrock37Model,
                agent_id= "executor_agent",
                name="Executor Agent",
                description="Executor agent for executing planner steps",
                system_prompt=get_executor_prompt(),
                hooks=[LoggingHook()],
                conversation_manager=SummarizingConversationManager(
                    summary_ratio=0.3,
                    preserve_recent_messages = 10,
                ),
                tools=tools, # tools to query opensearch data and indexes
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
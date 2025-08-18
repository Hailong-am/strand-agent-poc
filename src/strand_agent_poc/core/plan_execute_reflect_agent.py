import json
import os
from typing import Dict, Any, Optional
from strands import Agent
from strands.session.file_session_manager import FileSessionManager

# from strands.session.repository_session_manager import RepositorySessionManager
from strands_tools import current_time
from strands_tools.agent_core_memory import AgentCoreMemoryToolProvider
from strands.agent.conversation_manager import SummarizingConversationManager
from strands.telemetry import StrandsTelemetry
from strands.telemetry.tracer import get_tracer
from opentelemetry import trace as trace_api

from .prompt_management.prompts import (
    DEFAULT_PLANNER_PROMPT,
    DEFAULT_REFLECT_PROMPT,
    FINAL_RESULT_RESPONSE_INSTRUCTIONS,
    PLAN_EXECUTE_REFLECT_RESPONSE_FORMAT,
    PLANNER_RESPONSIBILITY,
)

# from .session_manager import AgentCoreSessionRepository
from . import model
from .executor import executor_agent, get_tool_prompt

from dotenv import load_dotenv

load_dotenv()

MEMORY_ID = os.getenv("MEMORY_ID","memory_ux56y-yA1dMNGN1i")
ACTOR_ID = os.getenv("ACTOR_ID", "plan_execute_reflect_agent")
NAMESPACE = os.getenv("NAMESPACE", "default")
REGION = os.getenv("REGION", "us-east-1")


# Enable tracing for the agent
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()     # Send traces to OTLP endpoint
strands_telemetry.setup_meter(
    enable_otlp_exporter=True)

class PlanExecuteReflectAgent:
    def __init__(
        self,
        session_id="default_conversation",
        max_steps: int = 20,
        executor_max_iterations: int = 20,
    ):
        self.max_steps = max_steps
        self.executor_max_iterations = executor_max_iterations
        self.completed_steps = []
        self.plan_steps = []

        self.tool_prompt = get_tool_prompt()

        # Prompt templates
        self.planner_system_prompt = self._get_planner_system_prompt()

        # Create a new AgentCoreMemoryToolProvider for each session
        agent_core_memory_provider = self._get_agent_core_memory_provider(session_id)

        # Initialize session manager with conversationId
        session_manager = FileSessionManager(
            storage_dir=os.getenv("SESSION_STORAGE_DIR", "./sessions"),
            session_id=session_id,
        )

        # Create planner agent
        self.planner = Agent(
            model=model.bedrock37Model,
            system_prompt=self.planner_system_prompt,
            tools=[current_time, agent_core_memory_provider.tools],
            conversation_manager=SummarizingConversationManager(
                preserve_recent_messages=10,
            ),
            session_manager=session_manager,
            agent_id="planner_agent",
            name="Planner Agent",
            description="Planner agent for creating step-by-step plans",
        )

    def _get_planner_system_prompt(self) -> str:
        return (
            PLANNER_RESPONSIBILITY
            + PLAN_EXECUTE_REFLECT_RESPONSE_FORMAT
            + FINAL_RESULT_RESPONSE_INSTRUCTIONS
        )

    def _get_planner_prompt_template(self, parameters: dict[str, str]) -> str:
        return f"""${parameters['tools_prompt']}
        ${parameters['planner_prompt']}
        Objective: ${parameters['user_prompt']}

        Remember: Respond only in JSON format following the required schema."""

    @DeprecationWarning
    def _get_planner_prompt_template_with_history(
        self, parameters: dict[str, str]
    ) -> str:
        return f"""${parameters['tools_prompt']}

        ${parameters['planner_prompt']}

        Objective: ```${parameters['user_prompt']}```

        You have currently executed the following steps:
        [${parameters['completed_steps']}]

        Remember: Respond only in JSON format following the required schema."""

    def _get_reflect_prompt_template(self, parameters: dict[str, str]) -> str:
        return f"""${parameters['tools_prompt']}

        ${parameters['planner_prompt']}

        Objective: ```${parameters['user_prompt']}```

        Original plan:
        [${parameters['steps']}]

        You have currently executed the following steps from the original plan:
        [${parameters['completed_steps']}]

        ${parameters['reflect_prompt']}

        Remember: Respond only in JSON format following the required schema.
    """

    def _parse_llm_output(self, response: str) -> Dict[str, Any]:
        # Parse LLM response and extract JSON
        try:
            # Remove markdown code blocks if present
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip()

            return json.loads(response)
        except json.JSONDecodeError as e:
            return {"steps": [], "result": f"Error parsing response: {str(e)}"}

    def _get_agent_core_memory_provider(self, session_id: str) -> AgentCoreMemoryToolProvider:
        # Create a new AgentCoreMemoryToolProvider for each session
        provider = AgentCoreMemoryToolProvider(
            boto_session=model.session,
            memory_id=MEMORY_ID,
            actor_id=ACTOR_ID,
            session_id=session_id,
            namespace=NAMESPACE,
            region=REGION,
        )
        return provider

    def _load_conversation_history(self, conversationId: str) -> list:
        # Use agent_core_memory with current session_id (conversationId)
        provider = self._get_agent_core_memory_provider(conversationId)
        result = provider.agent_core_memory(
            action="list",
        ) # type: ignore
        print("&&&&&")
        print(result)
        # result["content"] 是一个列表，每个元素是 {"text": ...}
        if result.get("status") == "success" and result.get("content"):
            steps = []
            for item in result["content"]:
                try:
                    # 这里假设存储的内容是json字符串
                    steps.append(json.loads(item["text"]))
                except Exception:
                    continue
            return steps
        return []

    def _save_interaction(self, conversationId: str, interaction: dict):
        # Use agent_core_memory with current session_id (conversationId)
        provider = self._get_agent_core_memory_provider(conversationId)
        provider.agent_core_memory(
            action="record", content=json.dumps(interaction, ensure_ascii=False)
        ) # type: ignore

    def execute(self, objective: str, trace_id: Optional[str] = None) -> str:
        # self.completed_steps = self._load_conversation_history(conversationId)
        # interactionId = 0  # Initialize interactionId
        # tracer = get_tracer()
        # self.planner.tracer = tracer


        # Main execution loop for Plan-Execute-Reflect agent
        while len(self.completed_steps) < self.max_steps:
            # Generate plan
            if self.completed_steps:
                # Use reflection prompt with completed steps
                # interactionId += 1
                prompt = self._get_reflect_prompt_template(
                    {
                        "tools_prompt": self.tool_prompt,
                        "planner_prompt": DEFAULT_PLANNER_PROMPT,
                        "user_prompt": objective,
                        "steps": json.dumps(self.plan_steps, ensure_ascii=False),
                        "completed_steps": json.dumps(
                            self.completed_steps, ensure_ascii=False
                        ),
                        "reflect_prompt": DEFAULT_REFLECT_PROMPT,
                    }
                )
            else:
                # Use planner prompt without completed steps
                prompt = self._get_planner_prompt_template(
                    {
                        "tools_prompt": self.tool_prompt,
                        "planner_prompt": DEFAULT_PLANNER_PROMPT,
                        "user_prompt": objective,
                    }
                )

            # Add agent_core_memory tool for planner agent dynamically
            # self.planner.tools = [self._get_agent_core_memory(conversationId)]

            # Get plan from planner
            planner_response = str(self.planner(prompt))
            parsed_response = self._parse_llm_output(planner_response)

            steps = parsed_response.get("steps", [])
            self.plan_steps = steps

            # Check if we have a final result
            if parsed_response.get("result"):
                # # Save final result
                # self._save_interaction(conversationId, {
                #     "conversationId": conversationId,
                #     "input": objective,
                #     "result": parsed_response["result"]
                # })
                return parsed_response["result"]

            # Execute next step if available

            if not steps:
                return "No more steps to execute and no final result provided."

            # Find the next unfinished step
            completed_step_texts = {s.get("input") for s in self.completed_steps}
            next_step = None
            for s in steps:
                if s not in completed_step_texts:
                    next_step = s
                    break

            if next_step is None:
                # All steps have been executed
                return f"All planned steps executed. Completed steps: {json.dumps(self.completed_steps, indent=2)}"

            span = self.planner.tracer._start_span(span_name=next_step, parent_span=self.planner.trace_span)
            step_result = executor_agent(next_step)
            self.planner.tracer._end_span(span)

            interaction = {"input": next_step, "result": step_result}
            self.completed_steps.append(interaction)
            # self._save_interaction(conversationId, interaction)

        # Max steps reached
        return f"Maximum steps ({self.max_steps}) reached. Completed steps: {json.dumps(self.completed_steps, indent=2)}"


def run_agent(
    objective: str,
    memory_id: Optional[str] = None,
    max_steps: int = 20,
    executor_max_iterations: int = 20,
    system_prompt: Optional[str] = None,
    executor_system_prompt: Optional[str] = None,
    planner_prompt: Optional[str] = None,
    reflect_prompt: Optional[str] = None,
) -> str:
    # Create the main agent instance
    if not memory_id:
        memory_id = os.urandom(16).hex()
    plan_execute_reflect_agent = PlanExecuteReflectAgent(
        session_id=memory_id,
        max_steps=max_steps,
        executor_max_iterations=executor_max_iterations,
    )
    # Main entry point for the Plan-Execute-Reflect agent
    return plan_execute_reflect_agent.execute(objective)

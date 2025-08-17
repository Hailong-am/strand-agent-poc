import json
import os
from typing import Dict, Any, Optional
from strands import Agent
from strands.session.file_session_manager import FileSessionManager
# from strands.session.repository_session_manager import RepositorySessionManager
from strands_tools import current_time
from strands_tools.agent_core_memory import AgentCoreMemoryToolProvider
from strands.agent.conversation_manager import SummarizingConversationManager

from src.strand_agent_poc.core.prompt_management.prompts import DEFAULT_PLANNER_PROMPT, DEFAULT_REFLECT_PROMPT, FINAL_RESULT_RESPONSE_INSTRUCTIONS, PLAN_EXECUTE_REFLECT_RESPONSE_FORMAT, PLANNER_RESPONSIBILITY

# from .session_manager import AgentCoreSessionRepository
from . import model
from .executor import executor_agent, get_tool_prompt

from dotenv import load_dotenv
load_dotenv()

MEMORY_ID = os.getenv("MEMORY_ID")
ACTOR_ID = os.getenv("ACTOR_ID")
NAMESPACE = os.getenv("NAMESPACE", "default")
REGION = os.getenv("REGION", "us-east-1")


class PlanExecuteReflectAgent:
    def __init__(self, session_id = 'default_conversation', max_steps: int = 20, executor_max_iterations: int = 20):
        self.max_steps = max_steps
        self.executor_max_iterations = executor_max_iterations
        self.completed_steps = []
        self.plan_steps = []

        self.tool_prompt = get_tool_prompt()

        # Prompt templates
        self.planner_system_prompt = self._get_planner_system_prompt()

        # Create a new AgentCoreMemoryToolProvider for each session
        memory_tool = self._get_agent_core_memory(session_id)

        # Initialize session manager with conversationId
        session_manager = FileSessionManager(
            storage_dir=os.getenv("SESSION_STORAGE_DIR", "./sessions"),
            session_id=session_id
        )

        # Create planner agent
        self.planner = Agent(
            model=model.bedrock37Model,
            system_prompt=self.planner_system_prompt,
            tools=[current_time, memory_tool],
            conversation_manager=SummarizingConversationManager(
                preserve_recent_messages = 10,
            ),
            session_manager=session_manager,
            agent_id="planner_agent",
            name="Planner Agent",
            description="Planner agent for creating step-by-step plans"
        )

    def _get_planner_system_prompt(self) -> str:
        return PLANNER_RESPONSIBILITY + PLAN_EXECUTE_REFLECT_RESPONSE_FORMAT + FINAL_RESULT_RESPONSE_INSTRUCTIONS

    def _get_planner_prompt_template(self, parameters: dict[str, str]) -> str:
        return f"""${parameters['tools_prompt']}
        ${parameters['planner_prompt']}
        Objective: ${parameters['user_prompt']}

        Remember: Respond only in JSON format following the required schema."""

    @DeprecationWarning
    def _get_planner_prompt_template_with_history(self, parameters: dict[str, str]) -> str:
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

    def _get_agent_core_memory(self, session_id: str):
        # Create a new AgentCoreMemoryToolProvider for each session
        provider = AgentCoreMemoryToolProvider(
            boto_session=model.session,
            memory_id=MEMORY_ID,
            actor_id=ACTOR_ID,
            session_id=session_id,
            namespace=NAMESPACE,
            region=REGION
        )
        return provider.agent_core_memory

    def _load_conversation_history(self, conversationId: str) -> list:
        # Use agent_core_memory with current session_id (conversationId)
        memory = self._get_agent_core_memory(conversationId)
        result = memory(
            action="list",
        )
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
        agent_core_memory = self._get_agent_core_memory(conversationId)
        agent_core_memory(
            action="record",
            content=json.dumps(interaction, ensure_ascii=False)
        )

    def execute(self, objective: str, conversationId: Optional[str] = None) -> str:
        # self.completed_steps = self._load_conversation_history(conversationId)
        # interactionId = 0  # Initialize interactionId

        # Main execution loop for Plan-Execute-Reflect agent
        while len(self.completed_steps) < self.max_steps:
            # Generate plan
            if self.completed_steps:
                # Use reflection prompt with completed steps
                # interactionId += 1
                prompt = self._get_reflect_prompt_template({
                    "tools_prompt": self.tool_prompt,
                    "planner_prompt": DEFAULT_PLANNER_PROMPT,
                    "user_prompt": objective,
                    'steps': json.dumps(self.plan_steps, ensure_ascii=False),
                    "completed_steps": json.dumps(self.completed_steps, ensure_ascii=False),
                    'reflect_prompt': DEFAULT_REFLECT_PROMPT
                })
            else:
                # Use planner prompt without completed steps
                prompt = self._get_planner_prompt_template({
                    "tools_prompt": self.tool_prompt,
                    "planner_prompt": DEFAULT_PLANNER_PROMPT,
                    "user_prompt": objective,
                })

            # Add agent_core_memory tool for planner agent dynamically
            # self.planner.tools = [self._get_agent_core_memory(conversationId)]

            # Get plan from planner
            planner_response = str(self.planner(prompt))
            parsed_response = self._parse_llm_output(planner_response)

            steps = parsed_response.get("steps", [])
            self.plan_steps = steps

            # Check if we have a final result
            if parsed_response.get("result") and len(steps) == 0:
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

            # Execute the step
            step_result = executor_agent(next_step)
            interaction = {
                "input": next_step,
                "result": step_result
            }
            self.completed_steps.append(interaction)
            # self._save_interaction(conversationId, interaction)


        # Max steps reached
        return f"Maximum steps ({self.max_steps}) reached. Completed steps: {json.dumps(self.completed_steps, indent=2)}"


def run_agent(objective: str, conversationId: str) -> str:
    # Create the main agent instance
    plan_execute_reflect_agent = PlanExecuteReflectAgent(session_id= conversationId)
    # Main entry point for the Plan-Execute-Reflect agent
    return plan_execute_reflect_agent.execute(objective, conversationId)


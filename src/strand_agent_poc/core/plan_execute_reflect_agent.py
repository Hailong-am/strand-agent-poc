import json
from typing import Dict, Any, Optional
from strands import Agent
# from strands_tools import current_time
from strands_tools.agent_core_memory import AgentCoreMemoryToolProvider
from . import model
from .executor import executor_agent

MEMORY_ID = "memory_anx9d-xl4QUwBOS0"
ACTOR_ID = "jiaruj"
NAMESPACE = "default"
REGION = "us-west-2"


class PlanExecuteReflectAgent:
    def __init__(self, max_steps: int = 20, executor_max_iterations: int = 20):
        self.max_steps = max_steps
        self.executor_max_iterations = executor_max_iterations
        self.completed_steps = []

        # Prompt templates
        self.planner_prompt = self._get_planner_prompt()
        self.reflect_prompt = self._get_reflect_prompt()

        # Create planner agent
        self.planner = Agent(
            model=model.bedrockModel,
            system_prompt=self.planner_prompt,
            # tools=[current_time]
        )

    def _get_planner_prompt(self) -> str:
        tools_prompt = """Available tools for execution:
- OpenSearch MCP Server tools: Query and search OpenSearch indexes and documents
- Document retrieval and analysis capabilities
- Log analysis and filtering tools

"""
        
        return f"""{tools_prompt}You are a thoughtful and analytical planner agent in a plan-execute-reflect framework. Your job is to design a clear, step-by-step plan for a given objective.

Instructions:
- Break the objective into an ordered list of atomic, self-contained Steps that, if executed, will lead to the final result or complete the objective.
- Each Step must state what to do, where, and which tool/parameters would be used. You do not execute tools, only reference them for planning.
- Use only the provided tools; do not invent or assume tools. If no suitable tool applies, use reasoning or observations instead.
- Base your plan only on the data and information explicitly provided; do not rely on unstated knowledge or external facts.
- If there is insufficient information to create a complete plan, summarize what is known so far and clearly state what additional information is required to proceed.
- Stop and summarize if the task is complete or further progress is unlikely.
- Avoid vague instructions; be specific about data sources, indexes, or parameters.
- Never make assumptions or rely on implicit knowledge.
- Respond only in JSON format.

Response Instructions:
Only respond in JSON format. Always follow the given response instructions. Do not return any content that does not follow the response instructions. Do not add anything before or after the expected JSON.
Always respond with a valid JSON object that strictly follows the below schema:
{{
    "steps": array[string],
    "result": string
}}
Use "steps" to return an array of strings where each string is a step to complete the objective, leave it empty if you know the final result. Please wrap each step in quotes and escape any special characters within the string.
Use "result" return the final response when you have enough information, leave it empty if you want to execute more steps. Please escape any special characters within the result.

Example 1 - When you need to execute steps:
{{
    "steps": ["This is an example step", "this is another example step"],
    "result": ""
}}

Example 2 - When you have the final result:
{{
    "steps": [],
    "result": "This is an example result\\n with escaped special characters"
}}"""

    def _get_reflect_prompt(self) -> str:
        return """Update your plan based on the latest step results. If the task is complete, return the final answer. Otherwise, include only the remaining steps. Do not repeat previously completed steps."""

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
            memory_id=MEMORY_ID,
            actor_id=ACTOR_ID,
            session_id=session_id,
            namespace=NAMESPACE,
            region=REGION
        )
        return provider.agent_core_memory

    def _load_conversation_history(self, conversationId: str) -> list:
        # Use agent_core_memory with current session_id (conversationId)
        agent_core_memory = self._get_agent_core_memory(conversationId)
        result = agent_core_memory(
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
        # Main execution loop for Plan-Execute-Reflect agent
        if conversationId is None:
            conversationId = "default_conversation"

        self.completed_steps = self._load_conversation_history(conversationId)
        interactionId = 0  # Initialize interactionId

        while len(self.completed_steps) < self.max_steps:
            if len(self.completed_steps) > 0:
                # Use reflection prompt with completed steps
                interactionId += 1
                prompt = f"""Objective: {objective}

You have currently executed the following steps:
{json.dumps(self.completed_steps, indent=2)}

{self.reflect_prompt}

Remember: Respond only in JSON format following the required schema."""
            else:
                prompt = f"""Objective: {objective}

Remember: Respond only in JSON format following the required schema."""

            # Add agent_core_memory tool for planner agent dynamically
            self.planner.tools = [self._get_agent_core_memory(conversationId)]

            # Get plan from planner
            planner_response = str(self.planner(prompt))
            parsed_response = self._parse_llm_output(planner_response)

            # Check if we have a final result
            if parsed_response.get("result"):
                # Save final result
                self._save_interaction(conversationId, {
                    "conversationId": conversationId,
                    "input": objective,
                    "result": parsed_response["result"]
                })
                return parsed_response["result"]

            # Execute next step if available
            steps = parsed_response.get("steps", [])
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
                "interactionId": interactionId,
                "input": next_step,
                "result": step_result
            }
            self.completed_steps.append(interaction)
            self._save_interaction(conversationId, interaction)


        # Max steps reached
        return f"Maximum steps ({self.max_steps}) reached. Completed steps: {json.dumps(self.completed_steps, indent=2)}"


# Create the main agent instance
plan_execute_reflect_agent = PlanExecuteReflectAgent()

def run_agent(objective: str, conversationId: Optional[str] = None) -> str:
    # Main entry point for the Plan-Execute-Reflect agent
    return plan_execute_reflect_agent.execute(objective, conversationId)


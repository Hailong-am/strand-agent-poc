import json
from typing import Dict, Any
from strands import Agent
from strands_tools import current_time
from . import model
from .executor import executor_agent


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
            tools=[current_time]
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
        """Parse LLM response and extract JSON"""
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

    def execute(self, objective: str) -> str:
        """Main execution loop implementing Plan-Execute-Reflect pattern"""
        self.completed_steps = []

        if len(self.completed_steps) < self.max_steps:
            # Generate plan
            if len(self.completed_steps) > 0:
                # Use reflection prompt with completed steps
                prompt = f"""Objective: {objective}

You have currently executed the following steps:
{json.dumps(self.completed_steps, indent=2)}

{self.reflect_prompt}

Remember: Respond only in JSON format following the required schema."""
            else:
                # Initial planning
                prompt = f"""Objective: {objective}

Remember: Respond only in JSON format following the required schema."""

            # Get plan from planner
            planner_response = str(self.planner(prompt))
            parsed_response = self._parse_llm_output(planner_response)

            # Check if we have a final result
            if parsed_response.get("result"):
                return parsed_response["result"]

            # Execute first step if available
            steps = parsed_response.get("steps", [])
            if not steps:
                return "No more steps to execute and no final result provided."

            # Execute the first step
            first_step = steps[0]
            step_result = executor_agent(first_step)

            # Add to completed steps
            self.completed_steps.append({
                "step": first_step,
                "result": step_result
            })

        # Max steps reached
        return f"Maximum steps ({self.max_steps}) reached. Completed steps: {json.dumps(self.completed_steps, indent=2)}"


# Create the main agent instance
plan_execute_reflect_agent = PlanExecuteReflectAgent()

def run_agent(objective: str) -> str:
    """Main entry point for the Plan-Execute-Reflect agent"""
    return plan_execute_reflect_agent.execute(objective)

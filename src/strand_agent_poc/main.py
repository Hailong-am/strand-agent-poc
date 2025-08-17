#!/usr/bin/env python3

import sys
from .core.plan_execute_reflect_agent import run_agent, _load_conversation_history
from strands_tools.agent_core_memory import AgentCoreMemoryToolProvider


MEMORY_ID = "memory_anx9d-xl4QUwBOS0"
ACTOR_ID = "jiaruj"
NAMESPACE = "default"
REGION = "us-west-2"


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py '<objective>'")
        print(
            "Example: python main.py 'Calculate the current time and create a Python script'"
        )
        sys.exit(1)

    objective = " ".join(sys.argv[1:])

    print(f"Objective: {objective}")
    print("-" * 50)

    try:
        result = run_agent(objective)
        print("\nResult:")
        print(result)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    provider = AgentCoreMemoryToolProvider(
        memory_id=MEMORY_ID,
        actor_id=ACTOR_ID,
        session_id="111",
        namespace=NAMESPACE,
        region=REGION,
    )
    result = provider.agent_core_memory(
        action="list",
    )
    print(result)

#!/usr/bin/env python3

from ..core.plan_execute_reflect_agent import run_agent


def main():
    # Test the Plan-Execute-Reflect agent
    objective = """
    I need to analyze the current time and calculate how many hours are left until midnight.
    Then create a Python script that can perform this calculation automatically.
    """
    
    print("Starting Plan-Execute-Reflect Agent...")
    print(f"Objective: {objective}")
    print("-" * 50)
    
    result = run_agent(objective)
    
    print("Final Result:")
    print(result)


if __name__ == "__main__":
    main()

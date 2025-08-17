#!/usr/bin/env python3

from strand_agent_poc.core.plan_execute_reflect_agent import run_agent


def main():
    # Test the Plan-Execute-Reflect agent
    objective = """
        Users are reporting payment failures during checkout process. Investigate the root cause of the payment failures and determine if there’s a pattern to the failures
    """

    print("Starting Plan-Execute-Reflect Agent...")
    print(f"Objective: {objective}")
    print("-" * 50)

    result = run_agent(objective, "111")

    print("Final Result:")
    print(result)


if __name__ == "__main__":
    main()

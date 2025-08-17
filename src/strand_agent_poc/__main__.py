#!/usr/bin/env python3
import sys
from .core import run_agent


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m strand_agent_poc <objective>")
        sys.exit(1)

    objective = " ".join(sys.argv[1:])
    result = run_agent(objective)
    print(result)


if __name__ == "__main__":
    main()

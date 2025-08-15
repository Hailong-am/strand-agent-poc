#!/usr/bin/env python3
import sys
import json
from src.strand_agent_poc.core import get_conversation_history, search_memory

def main():
    if len(sys.argv) < 2:
        print("Usage: python query_memory.py <session_id> [search_query]")
        sys.exit(1)
    
    session_id = sys.argv[1]
    
    if len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        results = search_memory(session_id, query)
        print(f"Search results for '{query}':")
    else:
        results = get_conversation_history(session_id)
        print(f"History for session '{session_id}':")
    
    print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
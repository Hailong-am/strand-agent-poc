import json
from typing import List, Dict, Any, Optional
from strands_tools.agent_core_memory import AgentCoreMemoryToolProvider

MEMORY_ID = "memory_anx9d-xl4QUwBOS0"
ACTOR_ID = "jiaruj"
NAMESPACE = "default"


def query_agent_core_memory(
    session_id: str,
    action: str = "list",
    content: Optional[str] = None,
    query: Optional[str] = None
) -> Dict[str, Any]:
    """
    查询agent core memory中的数据
    
    Args:
        session_id: 会话ID
        action: 操作类型 ("list", "record", "search", "delete")
        content: 要记录的内容 (当action为"record"时使用)
        query: 搜索查询 (当action为"search"时使用)
    
    Returns:
        Dict containing the result from agent core memory
    """
    provider = AgentCoreMemoryToolProvider(
        memory_id=MEMORY_ID,
        actor_id=ACTOR_ID,
        session_id=session_id,
        namespace=NAMESPACE
    )
    
    agent_core_memory = provider.agent_core_memory
    
    kwargs = {"action": action}
    if content:
        kwargs["content"] = content
    if query:
        kwargs["query"] = query
    
    return agent_core_memory(**kwargs)


def get_conversation_history(session_id: str) -> List[Dict[str, Any]]:
    """
    获取指定会话的历史记录
    
    Args:
        session_id: 会话ID
    
    Returns:
        List of conversation steps
    """
    result = query_agent_core_memory(session_id, action="list")
    
    if result.get("status") == "success" and result.get("content"):
        steps = []
        for item in result["content"]:
            try:
                steps.append(json.loads(item["text"]))
            except json.JSONDecodeError:
                # 如果不是JSON格式，直接添加文本
                steps.append({"text": item["text"]})
        return steps
    return []


def save_to_memory(session_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    保存数据到agent core memory
    
    Args:
        session_id: 会话ID
        data: 要保存的数据
    
    Returns:
        Result from the save operation
    """
    content = json.dumps(data, ensure_ascii=False)
    return query_agent_core_memory(session_id, action="record", content=content)


def search_memory(session_id: str, query: str) -> List[Dict[str, Any]]:
    """
    在agent core memory中搜索数据
    
    Args:
        session_id: 会话ID
        query: 搜索查询
    
    Returns:
        List of matching results
    """
    result = query_agent_core_memory(session_id, action="search", query=query)
    
    if result.get("status") == "success" and result.get("content"):
        matches = []
        for item in result["content"]:
            try:
                matches.append(json.loads(item["text"]))
            except json.JSONDecodeError:
                matches.append({"text": item["text"]})
        return matches
    return []
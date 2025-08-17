from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ..core.plan_execute_reflect_agent import run_agent


app = FastAPI(title="Strand Agent API", version="0.1.0")


class AgentRequest(BaseModel):
    # Required
    objective: str

    # Optional parameters
    memory_id: Optional[str] = None
    system_prompt: Optional[str] = None
    executor_system_prompt: Optional[str] = None
    planner_prompt: Optional[str] = None
    reflect_prompt: Optional[str] = None
    planner_prompt_template: Optional[str] = None
    reflect_prompt_template: Optional[str] = None
    planner_with_history_template: Optional[str] = None
    max_steps: int = 20
    executor_max_iterations: int = 20
    message_history_limit: int = 10
    executor_message_history_limit: int = 10


class AgentResponse(BaseModel):
    result: str
    success: bool


@app.post("/execute", response_model=AgentResponse)
async def execute_agent(request: AgentRequest):
    """Execute the Plan-Execute-Reflect agent with the given objective"""
    try:
        result = run_agent(
            objective=request.objective,
            memory_id=request.memory_id,
            max_steps=request.max_steps,
            executor_max_iterations=request.executor_max_iterations,
            system_prompt=request.system_prompt,
            executor_system_prompt=request.executor_system_prompt,
            planner_prompt=request.planner_prompt,
            reflect_prompt=request.reflect_prompt,
        )
        return AgentResponse(result=result, success=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


def main():
    """Entry point for the API server"""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

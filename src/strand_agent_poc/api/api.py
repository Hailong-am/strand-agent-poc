from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ..core.plan_execute_reflect_agent import run_agent


app = FastAPI(title="Strand Agent API", version="0.1.0")


class AgentRequest(BaseModel):
    objective: str
    memory_id: Optional[str] = None
    max_steps: int = 20


class AgentResponse(BaseModel):
    result: str
    success: bool


@app.post("/execute", response_model=AgentResponse)
async def execute_agent(request: AgentRequest):
    """Execute the Plan-Execute-Reflect agent with the given objective"""
    try:
        result = run_agent(request.objective, request.memory_id)
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

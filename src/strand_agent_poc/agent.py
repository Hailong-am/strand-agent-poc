from core.plan_execute_reflect_agent import run_agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp


app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload):
    """Process user input and return a response"""
    user_message = payload.get("prompt", "Hello")

    response = run_agent(user_message)
    print(response)
    return str(response) # response should be json serializable


if __name__ == "__main__":
    app.run()
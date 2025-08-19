# Strand Agent POC

A Plan-Execute-Reflect agent implementation using the Strands framework, mimicking Java MLPlanExecuteAndReflectAgentRunner architecture.

## Features

- **Plan-Execute-Reflect Pattern**: Iterative planning, execution, and reflection
- **Claude 4 Planner**: Advanced planning with Claude 4 Sonnet
- **Claude 3.7 Executor**: Reliable execution with Claude 3.7 Sonnet
- **MCP Integration**: OpenSearch tools via Model Context Protocol
- **FastAPI Interface**: REST API for agent interactions
- **Environment Configuration**: Secure credential management

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Planner   │───▶│  Executor   │───▶│  Reflector  │
│ (Claude 4)  │    │(Claude 3.7) │    │ (Claude 4)  │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌─────────────┐
                    │ MCP Tools   │
                    │(OpenSearch) │
                    └─────────────┘
```

## Installation

```bash
# Clone and install
git clone <repository>
cd strand-agent-poc
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your OpenSearch credentials
```

## Usage

### CLI
```bash
strand-agent "Analyze high CPU usage in ad service logs"
```

### API
```bash
# Start API server
strand-agent-api

# Make requests
curl -X POST "http://localhost:8000/execute" \
  -H "Content-Type: application/json" \
  -d '{"objective": "Query OpenSearch for error logs"}'
```

### Python
```python
from strand_agent_poc import run_agent

result = run_agent("Your objective here")
print(result)
```

## Configuration

Create `.env` file:
```env
OPENSEARCH_URL=your-opensearch-url
OPENSEARCH_USERNAME=your-username
OPENSEARCH_PASSWORD=your-password
OPENSEARCH_SSL_VERIFY=false
```

## Project Structure

```
src/strand_agent_poc/
├── core/                          # Core agent logic
│   ├── plan_execute_reflect_agent.py  # Main agent
│   ├── planner.py                     # Planning component
│   ├── executor.py                    # Execution component
│   └── model.py                       # LLM configurations
├── api/                           # FastAPI interface
│   └── api.py                     # REST endpoints
└── tests/                         # Test files
    └── test_agent.py              # Agent tests
```

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
python -m pytest

# Format code
black src/

# Lint code
flake8 src/
```

## Deployment (AgentCore)

1. Configure environment variables

Create a .env file in the project root and fill in your credentials:

```
# AWS settings
AWS_BEARER_TOKEN_BEDROCK=
AWS_DEFAULT_REGION=us-west-2

# OpenSearch settings
OPENSEARCH_URL=
OPENSEARCH_USERNAME=
OPENSEARCH_PASSWORD=
OPENSEARCH_SSL_VERIFY=

MEMORY_ID=
ACTOR_ID=
NAMESPACE=
REGION=
```

2. Local testing

```
python agent.py
```

3. Deploy with AgentCore

Ensure Docker is running before proceeding:

```
# Configure your agent
# will generate Docker file
agentcore configure --entrypoint agent_example.py -er <YOUR_IAM_ROLE_ARN>

# Local testing
agentcore launch -l

# Deploy to AWS
agentcore launch

# Test your agent with CLI
agentcore invoke '{"prompt": "Hello"}'
```
## License

MIT

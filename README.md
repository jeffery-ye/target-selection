# Target Selection Pipeline with LLM
## TSEL-364

```
pip install -r requirements.txt
```

## Setting up GCP ADC for Gemini
https://docs.cloud.google.com/docs/authentication/set-up-adc-local-dev-environment
```
gcloud auth application-default login --impersonate-service-account SERVICE_ACCT_EMAIL
```

LangGraph manages the Flow (Nodes & Edges). It is the "Orchestrator" that decides which agent to run and when, based on a central State object.

PydanticAI/Pydantic manages the Data (State & Tools). It defines the schema for the State object and the inputs/outputs of all tools. If data is ever malformed (e.g., from an API call or an LLM), it raises a ValidationError, "failing loudly" exactly as you want.

1: Define Data Schemas (The Pydantic Core)

2: Define the LangGraph State
The State is a central object that all nodes read from and write to. We use LangGraph's TypedDict integration.

3: The Literature Agent (Node & Tool)
This agent is a LangGraph node. Its job is to run a Tool. That tool is our wrapper for the Asta Semantic Scholar MCP Server.

3a. The Asta MCP Tool 
Asta MCP is called here

3b. The Literature Agent Node (LangGraph)

4: The NER Agent (Abstracted)

5: Assembling the Graph
Outline in LangGraph, including the "broaden search" loop.
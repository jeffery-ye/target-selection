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

PydanticAI/Pydantic manages the Data (State & Tools). It defines the schema for the State object and the inputs/outputs of all tools. If data is ever malformed (e.g., from an API call or an LLM), it raises a ValidationError, "failing loudly"


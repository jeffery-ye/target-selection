# target-selection

The Core Architectural Principle
LangGraph manages the Flow (Nodes & Edges). It is the "Orchestrator" that decides which agent to run and when, based on a central State object.

PydanticAI/Pydantic manages the Data (State & Tools). It defines the schema for the State object and the inputs/outputs of all tools. If data is ever malformed (e.g., from an API call or an LLM), it raises a ValidationError, "failing loudly" exactly as you want.

1: Define Data Schemas (The Pydantic Core)

```python

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Literal
import pydantic_ai
from langchain_openai import ChatOpenAI

# 1. Schema for data from the Literature Agent
class Article(BaseModel):
    """Data schema for a single retrieved scientific article."""
    doi: str = Field(..., description="Digital Object Identifier.")
    pmid: Optional[str] = Field(None, description="PubMed ID.")
    title: str
    abstract: str
    is_open_access: bool = Field(..., description="Flag for open access full text.")
    full_text_url: Optional[HttpUrl] = Field(None, description="Link to full text if available.")
    relevance_score: float = Field(..., description="Asta MCP relevance score.")

# 2. Schema for data from the (Abstracted) NER Agent
class ProteinCandidate(BaseModel):
    """Schema for an extracted protein entity."""
    protein_name: str = Field(..., description="The name of the protein, e.g., 'Cyp51'")
    species: str = Field(..., description="The source species, e.g., 'Coccidioides immitis'")
    accession_id: Optional[str] = Field(None, description="UniProt ID, if found in the paper.")
    source_doi: str = Field(..., description="DOI of the paper it was found in.")
```

2: Define the LangGraph State
The State is a central object that all nodes read from and write to. We use LangGraph's TypedDict integration.

```python

from typing_extensions import TypedDict

class PipelineState(TypedDict):
    """The complete state of our protein target pipeline."""
    
    # Input
    original_query: str
    target_protein_count: int
    
    # State for the Literature Agent
    retrieved_articles: List[Article]
    articles_to_process: List[Article] # A queue of articles to send to NER
    
    # State for the NER/Validation Agents
    protein_candidates: List[ProteinCandidate]
    validated_uniprot_ids: List[str]
    
    # Control flags
    search_batch_size: int
    total_articles_fetched: int
```

3: The Literature Agent (Node & Tool)
This agent is a LangGraph node. Its job is to run a Tool. That tool is our wrapper for the Asta Semantic Scholar MCP Server.

3a. The Asta MCP Tool 
Asta MCP is called here
```python

import mcp_client # A hypothetical client for the MCP protocol
from pydantic import TypeAdapter

# We use Pydantic's TypeAdapter to validate the *list* of articles
ArticleListAdapter = TypeAdapter(List[Article])

# This is our "on-the-rails" tool.
# It fails loudly if the MCP server is down or returns bad data.
def search_asta_mcp_tool(query: str, batch_size: int, open_access: bool) -> List[Article]:
    """
    Calls the locally-running Asta/Semantic Scholar MCP server.
    """
    print(f"Tool: Calling Asta MCP with query: '{query}'")
    
    # 1. This is where you call the MCP server
    # It exposes pre-built tools like 'search_semantic_scholar'
    try:
        # mcp_client.call(target="semanticscholar", 
        #                tool="search_semantic_scholar",
        #                ...
        # )
        # For this example, we'll use a mock response:
        mock_response_from_mcp = [
            {
                "doi": "10.1126/science.1187142",
                "pmid": "20194751",
                "title": "Drug Target in Coccidioides",
                "abstract": "We identify Cyp51... as a key target.",
                "is_open_access": True,
                "full_text_url": "https.../full.pdf",
                "relevance_score": 0.95
            },
            # ... more results
        ]
        
        # 2. THE "FAIL LOUDLY" STEP:
        # We parse the raw JSON from the API call using our Pydantic model.
        # If the API response is missing a 'doi' or 'is_open_access'
        # is a string instead of a bool, this line will RAISE a
        # ValidationError, stopping the pipeline.
        validated_articles = ArticleListAdapter.validate_python(mock_response_from_mcp)
        
        return validated_articles
        
    except Exception as e:
        print(f"ASTA MCP TOOL FAILED: {e}")
        # Re-raise or return empty list to be handled by the node
        raise
```

3b. The Literature Agent Node (LangGraph)
```python
def literature_agent_node(state: PipelineState) -> PipelineState:
    """
    The LangGraph node responsible for searching for literature.
    """
    print("--- 1. ENTERING LITERATURE AGENT NODE ---")
    query = state["original_query"]
    batch_size = state["search_batch_size"]
    
    # Call the tool, which has Pydantic validation built-in
    try:
        new_articles = search_asta_mcp_tool(
            query=query, 
            batch_size=batch_size, 
            open_access=True # Per your design notes
        )
        
        # Update the state
        current_list = state.get("retrieved_articles", [])
        current_list.extend(new_articles)
        state["retrieved_articles"] = current_list
        state["articles_to_process"] = new_articles # Add new articles to the queue
        state["total_articles_fetched"] = len(current_list)
        
        print(f"--- Found {len(new_articles)} new articles. Total: {state['total_articles_fetched']} ---")
        
    except Exception as e:
        # If the tool failed loudly, we catch it here.
        # The graph can now be routed to a "fallback" or "error" state.
        print(f"--- LITERATURE AGENT FAILED TO RUN: {e} ---")
        # For now, we'll just stop processing this batch
        state["articles_to_process"] = [] 
        
    return state
```

4: The NER Agent (Abstracted)

```python
# Setup the LLM and the PydanticAI client
llm = ChatOpenAI(model="gpt-4-turbo")
pa_client = pydantic_ai.PydanticAI(llm=llm)

def ner_agent_node(state: PipelineState) -> PipelineState:
    """
    (Abstracted) Reads articles and uses PydanticAI to extract proteins.
    """
    print("--- 2. ENTERING NER AGENT NODE ---")
    articles_to_process = state.get("articles_to_process", [])
    if not articles_to_process:
        print("--- No new articles to process. ---")
        return state

    current_candidates = state.get("protein_candidates", [])
    
    for article in articles_to_process:
        # This is where your flowchart logic "Has Open Access?" happens
        if article.is_open_access:
            # text_to_scan = get_full_text(article.full_text_url) # (A helper function)
            text_to_scan = article.abstract # (Using abstract for demo)
        else:
            text_to_scan = article.abstract
            
        print(f"--- Scanning {article.doi} for proteins... ---")
        try:
            # THIS IS THE PYDANTIC-AI CALL:
            # It runs the LLM, constrains it to the schema, and parses
            # the output, "failing loudly" if the LLM's output
            # doesn't match the ProteinCandidate schema.
            extracted = pa_client.call(
                text_to_scan,
                output_model=ProteinCandidate, 
                query=f"Extract all protein drug targets mentioned in this text from {article.doi}."
            )
            
            if extracted:
                current_candidates.append(extracted) # (Assuming 1 for demo)
                
        except Exception as e:
            # The LLM failed to produce valid, structured output
            print(f"--- NER FAILED on {article.doi}: {e} ---")

    state["protein_candidates"] = current_candidates
    state["articles_to_process"] = [] # Clear the queue
    print(f"--- NER complete. Total candidates: {len(current_candidates)} ---")
    return state
```

5: Assembling the Graph
Outline in LangGraph, including the "broaden search" loop.

```python
Python

from langgraph.graph import StateGraph, END

# Define abstracted nodes for the rest of the flow
def validation_agent_node(state: PipelineState) -> PipelineState:
    """(Abstracted) Takes candidates, calls UniProt, populates validated_uniprot_ids."""
    print("--- 3. ENTERING VALIDATION AGENT ---")
    # ... UniProt API call logic ...
    # This node populates state["validated_uniprot_ids"]
    state["validated_uniprot_ids"] = list(set(["P12345", "Q67890"])) # Mock data
    print(f"--- Validation complete. Found {len(state['validated_uniprot_ids'])} unique IDs. ---")
    return state

def query_refiner_node(state: PipelineState) -> PipelineState:
    """(Abstracted) If more proteins are needed, it broadens the query."""
    print("--- 4. ENTERING QUERY REFINER ---")
    old_query = state["original_query"]
    # This would use an LLM call to broaden the search
    state["original_query"] = f"{old_query} OR related enzymes" 
    print(f"--- Broadening query to: {state['original_query']} ---")
    return state

# Define the conditional edge logic from your flowchart
def should_continue(state: PipelineState) -> Literal["continue", "broaden_search"]:
    """The "Enough proteins?" check."""
    if len(state["validated_uniprot_ids"]) >= state["target_protein_count"]:
        print("--- CONDITION: Enough proteins found. ENDING. ---")
        return "continue"
    else:
        print("--- CONDITION: Not enough proteins. Broadening search. ---")
        return "broaden_search"

# Build the graph
workflow = StateGraph(PipelineState)

# 1. Add all the nodes
workflow.add_node("literature_agent", literature_agent_node)
workflow.add_node("ner_agent", ner_agent_node)
workflow.add_node("validation_agent", validation_agent_node)
workflow.add_node("query_refiner", query_refiner_node)

# 2. Set the entry point
workflow.set_entry_point("literature_agent")

# 3. Add the edges
workflow.add_edge("literature_agent", "ner_agent")
workflow.add_edge("ner_agent", "validation_agent")

# 4. Add the all-important conditional edge
workflow.add_conditional_edges(
    "validation_agent",         # Source node
    should_continue,            # Function to call
    {
        "continue": END,        # If "continue", end the graph
        "broaden_search": "query_refiner" # If "broaden_search", go to refiner
    }
)

# 5. Add the loop-back edge
workflow.add_edge("query_refiner", "literature_agent")

# Compile the graph
app = workflow.compile()
```
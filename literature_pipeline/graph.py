from langgraph.graph import StateGraph, END
from typing import Literal

from .schemas import PipelineState
from .nodes.literature import literature_agent_node
from .nodes.ner import ner_agent_node
from .nodes.validation import validation_agent_node
from .nodes.refiner import query_refiner_node

# Define the conditional edge logic
def should_continue(state: PipelineState) -> Literal["continue", "broaden_search"]:
    """The "Enough proteins?" check."""
    if len(state.get("validated_uniprot_ids", [])) >= state["target_protein_count"]:
        print("--- CONDITION: Enough proteins found. ENDING. ---")
        return "continue"
    else:
        print("--- CONDITION: Not enough proteins. Broadening search. ---")
        return "broaden_search"

# Build the graph
def create_graph():
    """Creates and compiles the LangGraph workflow."""
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
    workflow.add_conditional_edges(
        "validation_agent",
        should_continue,
        {"continue": END, "broaden_search": "query_refiner"}
    )
    workflow.add_edge("query_refiner", "literature_agent")

    return workflow.compile()
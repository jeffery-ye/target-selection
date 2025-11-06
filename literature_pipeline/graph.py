from langgraph.graph import StateGraph, END
from typing import Literal

from .schemas import PipelineState
from .nodes.literature_agent import literature_search_node
from .nodes.reflection import literature_reflection_node
from .nodes.ner import ner_agent_node
#from .nodes.validation import validation_agent_node
#from .nodes.refiner import query_refiner_node

def should_continue(state: PipelineState) -> Literal["continue", "broaden_search"]:
    """The "Enough proteins?" check."""
    if len(state.get("validated_uniprot_ids", [])) >= state["target_protein_count"]:
        print("Condition: Target count met. Ending.")
        return "continue"
    else:
        print("Condition: Target count not met. Broadening search.")
        return "broaden_search"

def create_graph():
    """Creates and compiles the LangGraph workflow."""
    workflow = StateGraph(PipelineState)

    workflow.add_node("literature_searcher", literature_search_node)
    #workflow.add_node("literature_reflector", literature_reflection_node)
    #workflow.add_node("ner_agent", ner_agent_node)
    #workflow.add_node("validation_agent", validation_agent_node)
    #workflow.add_node("query_refiner", query_refiner_node)

    workflow.set_entry_point("literature_searcher")
    workflow.add_edge("literature_searcher", END)
    # workflow.add_edge("literature_searcher", "literature_reflector")
    # workflow.add_edge("literature_reflector", "ner_agent")
    # workflow.add_edge("ner_agent", "validation_agent")
    # workflow.add_conditional_edges(
    #     "validation_agent",
    #     should_continue,
    #     {"continue": END, "broaden_search": "query_refiner"}
    # )
    # workflow.add_edge("query_refiner", "literature_searcher")

    return workflow.compile()
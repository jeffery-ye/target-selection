from langgraph.graph import StateGraph, END
from .schemas import PipelineState
from .nodes.literature_retrieval_node import literature_node
from .nodes.literature_reflection_node import literature_reflection_node

def create_graph():
    """Creates and compiles the LangGraph workflow."""
    workflow = StateGraph(PipelineState)

    workflow.add_node("literature_agent", literature_node)
    
    workflow.add_node("literature_reflection", literature_reflection_node)

    workflow.set_entry_point("literature_agent")

    workflow.add_edge("literature_agent", "literature_reflection")
    workflow.add_edge("literature_reflection", END)

    return workflow.compile()
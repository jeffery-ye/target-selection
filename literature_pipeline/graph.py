from langgraph.graph import StateGraph, END

from .schemas import PipelineState
from .nodes.literature_agent import literature_agent_node

def start_node(state: PipelineState) -> PipelineState:
    """A simple node that logs a message."""
    state['original_query'] = "coccidioides drug targets"
    print("Executing start_node")
    return state

def create_graph():
    """Creates and compiles the LangGraph workflow."""
    workflow = StateGraph(PipelineState)

    workflow.add_node("start", start_node)
    workflow.add_node("literature_agent", literature_agent_node)

    workflow.set_entry_point("start")
    workflow.add_edge("start", "literature_agent")
    workflow.add_edge("literature_agent", END)

    return workflow.compile()
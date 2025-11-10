from langgraph.graph import StateGraph, END
from .schemas import PipelineState
from .nodes.literature_retrieval_node import literature_retrieval_node
from .nodes.literature_reflection_node import literature_reflection_node
from .nodes.literature_ner_node import ner_agent_node


def create_graph():
    """Creates and compiles the LangGraph workflow."""
    workflow = StateGraph(PipelineState)

    workflow.add_node("literature_retrieval", literature_retrieval_node)
    workflow.add_node("literature_reflection", literature_reflection_node)
    workflow.add_node("ner_agent", ner_agent_node)

    workflow.set_entry_point("literature_retrieval")
    workflow.add_edge("literature_retrieval", "literature_reflection")
    workflow.add_edge("literature_reflection", "ner_agent")
    workflow.add_edge("ner_agent", END)

    return workflow.compile()
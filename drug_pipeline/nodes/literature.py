from ..schemas import PipelineState
from ..tools.asta_client import search_asta_mcp_tool

def literature_agent_node(state: PipelineState) -> PipelineState:
    """
    The LangGraph node responsible for searching for literature.
    """
    print("--- 1. ENTERING LITERATURE AGENT NODE ---")
    query = state["original_query"]
    batch_size = state["search_batch_size"]
    
    try:
        new_articles = search_asta_mcp_tool(
            query=query, 
            batch_size=batch_size, 
            open_access=True
        )
        
        current_list = state.get("retrieved_articles", [])
        current_list.extend(new_articles)
        state["retrieved_articles"] = current_list
        state["articles_to_process"] = new_articles
        state["total_articles_fetched"] = len(current_list)
        print(f"--- Found {len(new_articles)} new articles. Total: {state['total_articles_fetched']} ---")
    except Exception as e:
        print(f"--- LITERATURE AGENT FAILED TO RUN: {e} ---")
        state["articles_to_process"] = [] 
        
    return state
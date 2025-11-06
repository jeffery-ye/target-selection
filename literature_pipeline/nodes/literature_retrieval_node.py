from ..schemas import PipelineState
from ..tools.asta_literature_search import search_asta_mcp_tool

def literature_node(state: PipelineState) -> dict:
    """
    Reads the query from the state, calls the Asta tool, 
    and returns the new articles to be added to the state.
    """
    print("--- LITERATURE EXTRACTION AGENT ---")
    query = state["original_query"]
    batch_size = state["search_batch_size"]
    
    try:
        # Call the tool, which has Pydantic validation built-in
        new_articles = search_asta_mcp_tool(
            query=query, 
            batch_size=batch_size
        )
        
        # Get the current list of all articles found so far
        current_list = state.get("retrieved_articles", [])
        current_list.extend(new_articles)
        
        print(f"Found {len(new_articles)} new. Total: {len(current_list)}")
        
        # Return the dictionary of state keys to update
        return {
            "retrieved_articles": current_list,
            "newly_found_articles": new_articles,
            "articles_to_process": new_articles, # Set queue for next agent
            "total_articles_fetched": len(current_list)
        }
        
    except Exception as e:
        # Handle tool failure (e.g., API error, validation error)
        print(f"Literature agent failed: {e}")
        return {
            "newly_found_articles": [], # Ensure pipeline continues cleanly
            "articles_to_process": [] 
        }
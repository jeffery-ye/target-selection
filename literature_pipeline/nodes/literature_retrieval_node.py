from ..schemas import PipelineState
from ..tools.asta_literature_search import search_asta_mcp_tool

def literature_node(state: PipelineState) -> dict:
    """
    Reads the query from the state, calls the Asta tool, 
    and returns the new articles to be added to the state.
    """
    print("--- LITERATURE EXTRACTION ---")
    query = state["all_articles"]
    
    try:
        # Call the tool, which has Pydantic validation built-in
        new_articles = search_asta_mcp_tool(
            query=query, 
            batch_size=batch_size
        )
        
        print(f"Found {len(new_articles)} new articles.")
        
        # Return the dictionary of state keys to update
        return {
            "retrieved_articles": new_articles,
        }
        
    except Exception as e:
        # Handle tool failure (e.g., API error, validation error)
        print(f"Literature agent failed: {e}")
        return {
            "retrieved_articles": [],
        }
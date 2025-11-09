from ..schemas import PipelineState
from ..tools.literature_search import search_asta_mcp_tool
import logging

logger = logging.getLogger(__name__)

def literature_retrieval_node(state: PipelineState) -> dict:
    """
    Reads the query from the state, calls the Asta tool, 
    and returns the new articles to be added to the state.
    """
    logger.info("--- LITERATURE EXTRACTION ---")
    query = state["original_query"]
    batch_size = state["search_batch_size"]
    
    try:
        # Call the tool, which has Pydantic validation built-in
        new_articles = search_asta_mcp_tool(
            query=query, 
            batch_size=batch_size
        )
        
        logger.info(f"Found {len(new_articles)} new articles.\n")
        
        # Return the dictionary of state keys to update
        return {
            "articles_to_process": new_articles,
        }
        
    except Exception as e:
        # Handle tool failure (e.g., API error, validation error)
        logger.info(f"Literature agent failed: {e}\n")
        return {
            "articles_to_process": [],
        }
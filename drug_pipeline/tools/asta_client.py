# import mcp_client # A hypothetical client for the MCP protocol
from pydantic import TypeAdapter
from typing import List

from ..schemas import Article

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
                "full_text_url": "https://science.sciencemag.org/content/327/5970/1230.full.pdf",
                "relevance_score": 0.95
            },
            # ... more results
        ]
        
        validated_articles = ArticleListAdapter.validate_python(mock_response_from_mcp)
        return validated_articles
        
    except Exception as e:
        print(f"ASTA MCP TOOL FAILED: {e}")
        raise
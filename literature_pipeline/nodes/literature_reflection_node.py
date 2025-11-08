from typing import List
from ..schemas import PipelineState, Article
from ..tools.literature_reflection import article_reflection_tool

def literature_reflection_node(state: PipelineState) -> PipelineState:
    """
    Loops through all retrieved articles
    Evaluates likelihood to contain potential drug targets
    Returns ones that are likely
    """

    print("--- LITERATURE REFLECTION AGENT ---")
    retrieved_articles = state["retrieved_articles"]
    
    try:
        requirements = "This article must be be related to potential drug, vaccine, antifungul, etc. targets in either Coccidioides Valley Fever or Aspergillus."
        
        # Use the tool to classify articles
        article_reflection_tool(
            articles=retrieved_articles,
            requirements=requirements
        )
        
        
    except Exception as e:
        # Handle tool failure (e.g., API error, validation error)
        print(f"Literature agent failed: {e}")
        return {
            "retrieved_articles": [],
        }
    

    return
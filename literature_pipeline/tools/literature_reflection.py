import os
from typing import List
from ..schemas import Article, ReflectionBatch
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import pydantic_ai

load_dotenv()

if not os.getenv("GOOGLE_API_KEY"):
    print("Error: GOOGLE_API_KEY or GEMINI_API_KEY not found in environment.")

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
pa_client = pydantic_ai.PydanticAI(llm=llm)

def article_reflection_tool(articles: List[Article], requirements: str) -> ReflectionBatch:
    """
    Uses an LLM to reflect on a list of article abstracts.
    
    Classifies each article as 'true', 'false', or 'unclear' based on
    its relevance to the user's requirements, and returns a validated
    ReflectionBatch object.
    """
    
    if not articles:
        print("Tool: No articles provided for reflection.")
        return ReflectionBatch(reflections=[])

    # Format articles for the LLM prompt
    llm_food = ""
    for article in articles:
        llm_food += f"DOI: {article.doi}\nABSTRACT: {article.abstract}\n\n"
        
    # Define the prompt for PydanticAI
    prompt_query = f"""
    Review the following scientific abstracts based on this requirement: '{requirements}'

    For each article, classify its potential to contain a drug target:
    - 'true': The abstract strongly suggests it discusses a specific drug target or targets.
    - 'false': The abstract is clearly irrelevant (e.g., wrong topic, review paper, methods paper).
    - 'unclear': The abstract is relevant but doesn't explicitly mention a target; it might be in the full text.

    Provide a brief reasoning for each classification.
    """
    
    print(f"Tool: Reflecting on {len(articles)} articles with Gemini Flash...")

    # Execute the agent call
    try:
        # PydanticAI runs the LLM, validates, and returns the object
        result = pa_client.call(
            text=llm_food,
            output_model=ReflectionBatch,
            query=prompt_query
        )
        
        print(f"Tool: Reflection complete. Validated {len(result.reflections)} decisions.")
        return result
        
    except Exception as e:
        print(f"Tool Error: PydanticAI reflection failed. {e}")
        raise
import os
from typing import List
from ..schemas import Article, ReflectionBatch
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
''
import logging

logger = logging.getLogger(__name__)
load_dotenv()

if not os.getenv("GOOGLE_API_KEY"):
    logger.info("Error: GOOGLE_API_KEY or GEMINI_API_KEY not found in environment.")

def article_reflection_tool(articles: List[Article], requirements: str) -> ReflectionBatch:
    """
    Part of literature_reflection_node

    Uses an LLM to reflect on a list of article abstracts.
    
    Classifies each article as 'true', 'false', or 'unclear' based on
    its relevance to the user's requirements, and returns a validated
    ReflectionBatch object.
    """
    
    if not articles:
        logger.info("Tool: No articles provided for reflection.")
        return ReflectionBatch(reflections=[])

    # Format articles for the LLM prompt
    text_for_llm = ""
    for article in articles:
        text_for_llm += f"DOI: {article.doi}\nABSTRACT: {article.abstract}\n\n"

    # open source llm for testing purposes  
    model_name=''
    ollama_model = OpenAIChatModel(
        model_name=model_name,
        provider=OllamaProvider(base_url='http://localhost:11434/v1'),  
    )

    agent = Agent(  
        'google-gla:gemini-2.5-flash', # Uncomment to use gemini model
        # ollama_model, # Uncomment to use model from local
        output_type=ReflectionBatch,  
        instructions=(f"""
            Review the following scientific abstracts based on this requirement: '{requirements}'

            For each article, classify its potential to contain a drug target for Coccidioides, or for a related:
            - 'true': The abstract strongly suggests it discusses a specific drug target or targets.
            - 'false': The abstract is clearly irrelevant (e.g., wrong topic, review paper, methods paper).
            - 'unclear': The abstract is relevant but doesn't explicitly mention a target; it might be in the full text.

            Provide a brief reasoning for each classification.
        """
        ),
    )

    logger.info(f"Tool: Reflecting on {len(articles)} articles with Gemini Flash...")

    # Execute the agent call
    try:
        # PydanticAI runs the LLM, validates, and returns the object
        run_result = agent.run_sync(f"Here are the articles: {text_for_llm}")
        result: ReflectionBatch = run_result.output
        
        if not result or not result.reflections:
            logger.warning("Tool: Reflection ran but returned no valid reflection objects.")
            return result 

        # Log the formatted output
        logger.info(f"Tool: Reflection complete. Validated {len(result.reflections)} decisions.")
        for reflection in result.reflections:
            # Build a structured, multi-line string for the log
            log_entry = (
                f"\n  DOI:            {reflection.doi}\n"
                f"  Classification: {reflection.classification}\n"
                f"  Reasoning:      {reflection.reasoning}"
            )
            logger.info(log_entry + "\n")

        logger.info(run_result.usage())

        return run_result.output
        
    except AttributeError as e:
        logger.info(f"Tool Error: {e}")
        logger.info("Tool Debug: The 'run_result' object did not have an '.output' attribute or '.output' was None.")
        logger.info(f"Tool Debug: Full run_result object: {run_result}")
        raise
    except Exception as e:
        logger.info(f"Tool Error: PydanticAI reflection failed. {e}")
        if run_result:
            logger.info(f"Tool Debug: Full run_result object: {run_result}")
        raise
from typing import List, Dict
from ..schemas import PipelineState, Article, ArticleReflection, ReflectionBatch
from ..tools.literature_reflection import article_reflection_tool
import logging

logger = logging.getLogger(__name__)

def literature_reflection_node(state: PipelineState) -> Dict:
    """
    Reflects on new articles using an LLM to classify their relevance.
    
    Filters the article list to only include those classified as 'true'.
    """

    logger.info("--- LITERATURE REFLECTION AGENT ---")
    
    articles_to_reflect = state["articles_to_process"]
    
    if not articles_to_reflect:
        logger.info("Reflection: No new articles to process.")
        return {"articles_to_process": []}

    try:
        requirements = "This article must be related to potential drug, vaccine, or antifungal targets in either Coccidioides or Aspergillus."
        
        reflection_batch: ReflectionBatch = article_reflection_tool(
            articles=articles_to_reflect,
            requirements=requirements
        )
        
        # Map DOIs
        article_map = {}

        for article in articles_to_reflect:
            article_map[article.doi] = article
            
        
        articles_for_ner = []
        articles_for_full_text = []
        discarded = 0
        
        for reflection in reflection_batch.reflections:
            article = article_map.get(reflection.doi)
            if not article:
                continue

            if reflection.classification == "true":
                articles_for_ner.append(article)
            elif reflection.classification == "unclear":
                articles_for_full_text.append(article)
            else:
                discarded += 1
        
        logger.info(f"Reflection complete. Relevant: {len(articles_for_ner)}. Unclear: {len(articles_for_full_text)}. Discarded: {discarded} .\n")
        
        # Return the state update
        # Only 'true' articles proceed to the next node (NER)
        return {
            "confirmed_articles": articles_for_ner,
            "unclear_articles": articles_for_full_text
        }

    except Exception as e:
        logger.info(f"Literature reflection agent failed: {e}\n")
        return {
            "articles_to_process": [],
        }
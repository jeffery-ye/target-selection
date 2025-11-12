import os
import requests
from typing import List
from pydantic import TypeAdapter, ValidationError
from ..schemas import Article
from dotenv import load_dotenv
import logging
import datetime

logger = logging.getLogger(__name__)
load_dotenv()

# URL for the locally running Asta Paper Finder service
ASTA_PAPER_FINDER_URL = "http://localhost:8000/api/2/rounds"

ArticleListAdapter = TypeAdapter(List[Article])

def search_asta_mcp_tool(query: str, batch_size: int) -> List[Article]:
    """
    Part of the literature_retrieval_node: This tool uses the
    Asta Paper Finder agent service to retrieve n number of papers.

    Assumes the Asta Paper Finder service is running at ASTA_PAPER_FINDER_URL.
    """
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "paper_description": query,
        "operation_mode": "fast", 
    }
    
    logger.info(f"Tool: Calling local Asta Paper Finder service. Query: {query[:50]}...")
    
    try:
        # Use a long timeout. 'fast' mode can take ~30-60 seconds.
        response = requests.post(
            ASTA_PAPER_FINDER_URL,
            headers=headers,
            json=payload,
            timeout=120 
        )
        
        logger.info(f"Tool: Response status: {response.status_code}")
        response.raise_for_status()
        
        response_data = response.json()
        
        # --- Corrected Key ---
        # The list of papers is at response_data['doc_collection']['documents']
        doc_collection = response_data.get("doc_collection", {})
        raw_results = doc_collection.get("documents", [])
        
        if not raw_results:
            logger.info("Tool: Asta Paper Finder returned no 'documents' or 'documents' list was empty.")
            return []
        
        # --- Corrected TRANSFORMATION LAYER ---
        # Map the Asta agent's fields to our internal Article schema.
        transformed_results = []
        for r in raw_results:
            
            # Use corpus_id as the unique ID for 'doi' field
            unique_id = r.get("corpus_id")
            if not unique_id:
                # Fallback if corpus_id is missing for some reason
                unique_id = r.get("url", "N/A")

            transformed_results.append({
                "doi": unique_id,
                "pmid": None, # Not present in Asta response
                "title": r.get("title"),
                "abstract": r.get("abstract"),
                "is_open_access": False, # Not present in Asta response
                "full_text_url": r.get("url"),
                "relevance_score": r.get("relevance_judgement", {}).get("relevance_score", 0.0)
            })
        
        # Limit results to batch_size (handles your "limit to 10" request)
        transformed_results = transformed_results[:batch_size]

        validated_articles = ArticleListAdapter.validate_python(transformed_results)
        
        logger.info(f"Tool: Success. Validated {len(validated_articles)} articles.\n")
        for article in validated_articles:
            log_entry = (
                f"\n  DOI:           {article.doi}\n"
                f"  Title:         {article.title}\n"
                f"  Abstract:      {article.abstract}"
            )
            logger.info(log_entry + "\n")
            
        return validated_articles
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"Tool Error: HTTP {response.status_code} - {e}")
        logger.error(f"Tool Error: Response body: {response.text}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Tool Error: HTTP request to Asta service failed. {e}")
        raise
    except ValidationError as e:
        logger.error(f"Tool Error: Pydantic validation failed on Asta output. {e}")
        logger.error(f"Tool Error: Failed records: {transformed_results}")
        raise
    except Exception as e:
        logger.error(f"Tool Error: Data processing failed. {e}", exc_info=True)
        raise
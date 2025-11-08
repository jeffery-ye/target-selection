import os
import requests
from typing import List
from pydantic import TypeAdapter, ValidationError
from ..schemas import Article
from dotenv import load_dotenv

load_dotenv()

SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_API_KEY = os.getenv("ASTA_API_KEY")  

ARTICLE_FIELDS = "paperId,externalIds,title,abstract,isOpenAccess,url,citationCount"

ArticleListAdapter = TypeAdapter(List[Article])

def search_asta_mcp_tool(query: str, batch_size: int) -> List[Article]:
    """
    Part of the literature_retrieval_node: This tool uses Semantic Scholar
    to retrieve n number of papers, returning a list of articles.
    
    Searches papers using the Semantic Scholar API directly.
    """
    if not SEMANTIC_SCHOLAR_API_KEY:
        print("Warning: SEMANTIC_SCHOLAR_API_KEY not found. Using rate-limited public API.")
    
    headers = {
        "Accept": "application/json"
    }
    
    if SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY
    
    params = {
        "query": query,
        "limit": batch_size,
        "fields": ARTICLE_FIELDS
    }
    
    print(f"Tool: Calling Semantic Scholar API. Query: {query[:50]}... Size: {batch_size}")
    
    try:
        response = requests.get(
            SEMANTIC_SCHOLAR_API_URL,
            headers=headers,
            params=params,
            timeout=30
        )
        
        print(f"Tool: Response status: {response.status_code}")
        response.raise_for_status()
        
        response_data = response.json()
        raw_results = response_data.get("data", [])
        
        if not raw_results:
            print("Tool: Semantic Scholar returned no results.")
            return []
        
        # Translation layer - map Semantic Scholar fields to your Article model
        transformed_results = []
        for r in raw_results:
            external_ids = r.get("externalIds") or {}
            
            paper_id = r.get("paperId", "")
            paper_url = r.get("url") or f"https://www.semanticscholar.org/paper/{paper_id}"
            
            citation_count = r.get("citationCount", 0)
            relevance_score = min(citation_count / 100.0, 1.0) if citation_count else 0.0
            
            transformed_results.append({
                "doi": external_ids.get("DOI"),
                "pmid": external_ids.get("PubMed"),
                "title": r.get("title"),
                "abstract": r.get("abstract"),
                "is_open_access": r.get("isOpenAccess"),
                "full_text_url": paper_url,
                "relevance_score": relevance_score
            })
        
        validated_articles = ArticleListAdapter.validate_python(transformed_results)
        
        print(f"Tool: Success. Found {len(validated_articles)} articles.")
        return validated_articles
        
    except requests.exceptions.HTTPError as e:
        print(f"Tool Error: HTTP {response.status_code} - {e}")
        print(f"Tool Error: Response body: {response.text}")
        raise
    except requests.exceptions.RequestException as e:
        print(f"Tool Error: HTTP request failed. {e}")
        raise
    except ValidationError as e:
        print(f"Tool Error: Pydantic validation failed. {e}")
        print(f"Tool Error: Failed records: {transformed_results}")
        raise
    except Exception as e:
        print(f"Tool Error: Data processing failed. {e}")
        raise
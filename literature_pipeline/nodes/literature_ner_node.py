import logging
from typing import Dict, List
from ..schemas import PipelineState, Article, ProteinCandidate
from ..tools.full_text_retrieval import retrieve_article
from ..tools.ner_tool import extract_proteins_tool

logger = logging.getLogger(__name__)

def ner_agent_node(state: PipelineState) -> Dict:
    """
    Orchestrates the NER pipeline.
    
    For each "true" article, it fetches the best available text (Methods > Abstract),
    runs the NER tool, tags the results with the source DOI, and stores them.
    """
    logger.info("--- ENTERING: NER AGENT ---\n")
    
    articles_to_process: List[Article] = state["confirmed_articles"]
    all_found_candidates: List[ProteinCandidate] = []
    
    if not articles_to_process:
        logger.warning("NER Node: No articles to process.")
        return {"protein_candidates": []}

    for article in articles_to_process:
        logger.info(f"NER Node: Processing article DOI: {article.doi}")
        text_to_scan = None
        source_doc = "abstract"
        
        # Fetch Text
        if article.pmid:
            try:
                fetched_data = retrieve_article(article.pmid)
                if fetched_data:
                    if fetched_data.get('methods'):
                        text_to_scan = fetched_data['methods']
                        source_doc = "methods section"
            except Exception as e:
                logger.error(f"NER Node: Entrez fetch failed for PMID {article.pmid}. {e}\n")
        
        # Fallback to abstract from original search
        if not text_to_scan:
            text_to_scan = article.abstract

        logger.info(f"NER Node: Scanning {source_doc} for DOI {article.doi}...")
        
        # Run NER 
        try:
            ner_batch = extract_proteins_tool(text_to_scan)
            
            for candidate in ner_batch.protein_candidates:
                candidate.source_doi = article.doi
                all_found_candidates.append(candidate)
                
            logger.info(f"NER Node: Found {len(ner_batch.protein_candidates)} candidates in {article.doi}.")
            
        except Exception as e:
            logger.error(f"NER Node: Failed to extract proteins for {article.doi}. {e}\n")

    logger.info(f"NER Node: Finished. Total candidates found: {len(all_found_candidates)}\n")
    
    # 5. Write to State
    return {
        "protein_candidates": all_found_candidates,
        "articles_to_process": []
    }
import logging
import os
from typing import Optional
from Bio import Entrez
from xml.etree import ElementTree

logger = logging.getLogger(__name__)

# NCBI requires you to identify yourself
ENTREZ_EMAIL = os.getenv("ENTREZ_EMAIL")
if not ENTREZ_EMAIL:
    logger.warning("ENTREZ_EMAIL not set in .env. Using default.")
    ENTREZ_EMAIL = "pydantic-ai-agent@example.com"

Entrez.email = ENTREZ_EMAIL

def _parse_pmc_xml(xml_data: str) -> str:
    """Extracts plain text from PMC XML body."""
    try:
        root = ElementTree.fromstring(xml_data)
        body = root.find('.//body')
        if body is None:
            return None
        
        # Extract text from all paragraphs
        text_parts = [para.text for para in body.findall('.//p') if para.text]
        return "\n".join(text_parts)
    except ElementTree.ParseError as e:
        logger.error(f"Failed to parse PMC XML: {e}")
        return None

def _fetch_abstract(pmid: str) -> Optional[str]:
    """Fallback to fetching the abstract from PubMed."""
    logger.info(f"Tool: PMCID not found for {pmid}. Fetching abstract from PubMed.")
    try:
        handle = Entrez.efetch(db="pubmed", id=pmid, rettype="xml", retmode="text")
        records = Entrez.read(handle)
        handle.close()
        
        if "PubmedArticle" in records and records["PubmedArticle"]:
            article = records["PubmedArticle"][0]
            if "MedlineCitation" in article and "Article" in article["MedlineCitation"]:
                abstract = article["MedlineCitation"]["Article"].get("Abstract", {}).get("AbstractText")
                if abstract:
                    return "\n".join(abstract)
        
        logger.warning(f"Tool: No abstract found for PMID {pmid} in PubMed.")
        return None
    except Exception as e:
        logger.error(f"Tool: Failed to fetch abstract for PMID {pmid}. Error: {e}")
        return None

def fetch_full_text(pmid: str) -> Optional[str]:
    """
    Fetches the full text of an article from PMC using its PMID.
    
    If full text is not available in PMC, it falls back to fetching 
    just the abstract from PubMed.
    """
    logger.info(f"Tool: Attempting to fetch full text for PMID {pmid}...")
    
    try:
        # 1. Link PMID to PMCID
        link_handle = Entrez.elink(dbfrom="pubmed", db="pmc", id=pmid, linkname="pubmed_pmc_refs")
        link_result = Entrez.read(link_handle)
        link_handle.close()
        
        if not link_result[0]["LinkSetDb"]:
            # No PMCID link found
            return _fetch_abstract(pmid)
            
        pmcid = link_result[0]["LinkSetDb"][0]["Link"][0]["Id"]
        
        # 2. Fetch full text from PMC using PMCID
        logger.info(f"Tool: Found PMCID {pmcid}. Fetching full text...")
        fetch_handle = Entrez.efetch(db="pmc", id=pmcid, rettype="xml", retmode="text")
        xml_data = fetch_handle.read()
        fetch_handle.close()
        
        # 3. Parse XML to plain text
        full_text = _parse_pmc_xml(xml_data)
        
        if full_text:
            logger.info(f"Tool: Successfully extracted full text for PMCID {pmcid}.")
            return full_text
        else:
            # XML was empty or unparseable, fall back to abstract
            logger.warning(f"Tool: Could not parse full text for PMCID {pmcid}.")
            return _fetch_abstract(pmid)

    except Exception as e:
        logger.error(f"Tool: Entrez query failed for PMID {pmid}. Error: {e}")
        # Final fallback to abstract
        return _fetch_abstract(pmid)
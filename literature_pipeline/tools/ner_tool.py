import os
import logging
from typing import List
from ..schemas import NerBatch
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.agent import AgentRunResult

load_dotenv()

logger = logging.getLogger(__name__)

if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")

if not os.getenv("GOOGLE_API_KEY"):
    logger.error("Error: GOOGLE_API_KEY not found in environment.")

def extract_proteins_tool(text_to_scan: str) -> NerBatch:
    """
    Part of literature_ner_node

    Uses PydanticAI's Agent to perform NER on a block of text.
    
    Extracts protein candidates and returns a validated NerBatch object.
    """
    
    if not text_to_scan:
        logger.warning("Tool: extract_proteins_tool called with no text.")
        return NerBatch(protein_candidates=[])
        
    agent = Agent(
        'google-gla:gemini-2.5-flash',
        output_type=NerBatch,
        instructions=(f"""
            You are a biomedical Named Entity Recognition (NER) specialist.
            Your task is to extract all potential drug targets from the provided text.
            
            Find entities that are:
            1.  protein_name: The name of the protein (e.g., 'Cyp51', 'Hsp90').
            2.  species: The source species (e.g., 'Coccidioides immitis', 'Aspergillus fumigatus').
            3.  accession_id: Any UniProt or accession ID, if mentioned (e.g., 'P12345').
            
            Return a list of all candidates. If no targets are found, return an empty list.
        """
        ),
    )

    logger.info(f"Tool: Extracting proteins from text (length: {len(text_to_scan)})...")

    run_result: AgentRunResult = None
    try:
        run_result = agent.run_sync(f"Here is the text: {text_to_scan}") 
        result: NerBatch = run_result.output
        
        if not result or not result.protein_candidates:
            logger.info("Tool: NER ran but found no protein candidates.")
            return NerBatch(protein_candidates=[])
        
        logger.info(f"Tool: NER complete. Extracted {len(result.protein_candidates)} candidates.")
        logger.info(f"Tool Usage: {run_result.usage()}")
        
        return result
        
    except Exception as e:
        logger.error(f"Tool Error: PydanticAI NER failed. {e}")
        if run_result:
            logger.error(f"Tool Debug: Full run_result object: {run_result}")
        # Return empty batch to allow pipeline to continue
        return NerBatch(protein_candidates=[])

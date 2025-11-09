from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Literal
from typing_extensions import TypedDict

# Article class used to keep all articles in memory
class Article(BaseModel):
    """Data schema for a single retrieved scientific article."""
    doi: str = Field(..., description="Digital Object Identifier.")
    pmid: Optional[str] = Field(None, description="PubMed ID.")
    title: str
    abstract: str
    is_open_access: bool = Field(..., description="Flag for open access full text.")
    full_text_url: Optional[HttpUrl] = Field(None, description="Link to full text if available.")
    relevance_score: float = Field(..., description="Asta MCP relevance score.")

# --- REFLECTION AGENT ----
# Articles' relevancy status
class ArticleReflection(BaseModel):
    """Data schema for storing article relevancy"""
    doi: str = Field(..., description="Digital Object Identifier.")
    classification: Literal["true", "false", "unclear"]
    reasoning: str

# Relevancy Batch Processing
class ReflectionBatch(BaseModel):
    """Data schema for storing article relevancy"""
    reflections: List[ArticleReflection]

class ProteinCandidate(BaseModel):
    """Schema for an extracted protein entity."""
    protein_name: str = Field(..., description="The name of the protein, e.g., 'Cyp51'")
    species: str = Field(..., description="The source species, e.g., 'Coccidioides immitis'")
    accession_id: Optional[str] = Field(None, description="UniProt ID, if found in the paper.")
    source_doi: str = Field(..., description="DOI of the paper it was found in.")

class PipelineState(TypedDict):
    """The complete state of our protein target pipeline."""
    
    original_query: str
    target_protein_count: int
    
    articles_to_process: List[Article]
    article_status: List[Article]

    unclear_articles: List[Article]
    confirmed_articles: List[Article]
    
    protein_candidates: List[ProteinCandidate]
    validated_uniprot_ids: List[str]
    
    search_batch_size: int
    total_articles_fetched: int
import pydantic_ai
from langchain_openai import ChatOpenAI

from ..schemas import PipelineState, ProteinCandidate
from ..tools.text_utils import get_full_text

# Setup the LLM and the PydanticAI client
llm = ChatOpenAI(model="gpt-4-turbo")
pa_client = pydantic_ai.PydanticAI(llm=llm)

def ner_agent_node(state: PipelineState) -> PipelineState:
    """
    Reads articles and uses PydanticAI to extract proteins.
    """
    print("--- 2. ENTERING NER AGENT NODE ---")
    articles_to_process = state.get("articles_to_process", [])
    if not articles_to_process:
        print("--- No new articles to process. ---")
        return state

    current_candidates = state.get("protein_candidates", [])
    
    for article in articles_to_process:
        if article.is_open_access and article.full_text_url:
            text_to_scan = get_full_text(article.full_text_url)
        else:
            text_to_scan = article.abstract
            
        print(f"--- Scanning {article.doi} for proteins... ---")
        try:
            extracted = pa_client.call(
                text_to_scan,
                output_model=ProteinCandidate, 
                query=f"Extract all protein drug targets mentioned in this text from {article.doi}."
            )
            if extracted:
                current_candidates.append(extracted)
        except Exception as e:
            print(f"--- NER FAILED on {article.doi}: {e} ---")

    state["protein_candidates"] = current_candidates
    state["articles_to_process"] = [] # Clear the queue
    print(f"--- NER complete. Total candidates: {len(current_candidates)} ---")
    return state
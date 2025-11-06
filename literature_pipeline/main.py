import pprint
from .graph import create_graph
from .schemas import PipelineState

def run():
    """Initializes and runs the LangGraph workflow."""
    app = create_graph()

    initial_input: PipelineState = {
        #"original_query": input(),
        "original_query": "drug targets for Coccidioides",
        "target_protein_count": 5,
        "search_batch_size": 10,
        
        "retrieved_articles": [],
        "newly_found_articles": [],
        "articles_to_process": [],
        "protein_candidates": [],
        "validated_uniprot_ids": [],
        "total_articles_fetched": 0
    }

    print("Graph: Invoking with initial state...")
    
    for event in app.stream(initial_input):
        pprint.pprint(event)
        print("---")

    print("\nGraph execution complete.")

if __name__ == "__main__":
    run()
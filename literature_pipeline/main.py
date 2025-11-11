import pprint
import logging
import warnings
from .graph import create_graph
from .schemas import PipelineState

REPORT_FILE = "pipeline_run_report.txt"

# This is just really annoying -- langgraph, please fix your Pydantic imports
warnings.filterwarnings(
    "ignore",
    message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.*"
)

def run():
    """Initializes and runs the LangGraph workflow."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        filename=REPORT_FILE,
        filemode="w"
    )
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.info("--- Starting New Pipeline Run ---\n")

    app = create_graph()

    initial_input: PipelineState = {
        #"original_query": input(),
        "original_query": "drug targets for Coccidioides",
        "target_protein_count": 5,
        "search_batch_size": 10,
        
        "articles_to_process": [],
        "unclear_articles": [],
        "confirmed_articles": [],
        "protein_candidates": [],
        "validated_uniprot_ids": [],
        "total_articles_fetched": 0
    }

    logging.info(f"Initial State: query='{initial_input['original_query']}'\n")

    print("Graph: Invoking with initial state...")
    
    for event in app.stream(initial_input):
        pprint.pprint(event)
        print("---")

    print("\nGraph execution complete.")

    logging.info(f"Initial State: query='{initial_input['original_query']}'")

if __name__ == "__main__":
    run()
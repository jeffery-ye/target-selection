import logging
import threading
import uuid
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sse import sse
import redis
import sys
import os

# Asta
sys.path.append(os.path.join(os.path.dirname(__file__), "agent-baselines"))

# --- Import from existing pipeline ---
from literature_pipeline.graph import create_graph
from literature_pipeline.schemas import PipelineState

# --- Logging ---
REPORT_FILE = "pipeline_run_report.txt"
logging.basicConfig(
    level=logging.INFO,  # Set to INFO for production
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=REPORT_FILE,
    filemode="w"
)
# Add console handler
logging.getLogger().addHandler(logging.StreamHandler())
logger = logging.getLogger(__name__)

# --- App & SSE Configuration ---
app = Flask(__name__)
app.config["SSE_REDIS_URL"] = "redis://localhost:6379"
app.register_blueprint(sse, url_prefix='/stream')

# --- Test Redis Connection ---
try:
    redis_client = redis.StrictRedis.from_url(app.config["SSE_REDIS_URL"])
    redis_client.ping()
    logger.info("✓ Redis connection successful")
except Exception as e:
    logger.error(f"✗ Redis connection failed: {e}")
    redis_client = None

# --- Compile graph once on startup ---
try:
    graph = create_graph()
    logger.info("✓ LangGraph compiled successfully.")
except Exception as e:
    logger.error(f"✗ Failed to compile graph: {e}", exc_info=True)
    graph = None

def format_event_for_display(event: dict) -> str:
    """
    Converts a graph event dictionary into a human-readable log message.
    """
    messages = []
    
    for node_name, node_data in event.items():
        if node_name == "literature_retrieval":
            articles = node_data.get("articles_to_process", [])
            messages.append(f"\n{'='*60}")
            messages.append(f"📚 LITERATURE RETRIEVAL - Found {len(articles)} articles")
            messages.append(f"{'='*60}")
            
            for i, article in enumerate(articles, 1):
                messages.append(f"\n[Article {i}]")
                messages.append(f"Title: {article.title[:80]}{'...' if len(article.title) > 80 else ''}")
                messages.append(f"DOI: {article.doi}")
                abstract = article.abstract[:200] if article.abstract else "N/A"
                messages.append(f"Abstract: {abstract}{'...' if len(article.abstract or '') > 200 else ''}")
                messages.append("")
        
        elif node_name == "literature_reflection":
            confirmed = node_data.get("confirmed_articles", [])
            unclear = node_data.get("unclear_articles", [])
            reflections = node_data.get("reflection_results", [])
            
            reflection_map = {ref.doi: ref for ref in reflections}
            
            all_processed_articles = confirmed + unclear

            messages.append(f"\n{'='*60}")
            messages.append(f"🔍 LITERATURE REFLECTION")
            messages.append(f"{'='*60}")
            messages.append(f"Processed {len(all_processed_articles)} articles:")
            messages.append(f"  • ✅ Relevant: {len(confirmed)}")
            messages.append(f"  • ❓ Unclear: {len(unclear)}")
            messages.append(f"  • ❌ Discarded: {len(reflections) - len(all_processed_articles)}")
            
            if all_processed_articles:
                messages.append("\n--- Article Details ---")
            
            for article in all_processed_articles:
                reflection = reflection_map.get(article.doi)
                
                if reflection:
                    classification = reflection.classification.upper()
                    reasoning = reflection.reasoning
                else:
                    classification = "N/A"
                    reasoning = "N/A (Error in lookup)"

                title = article.title[:70]
                messages.append(f"\nTitle: {title}{'...' if len(article.title) > 70 else ''}")
                messages.append(f"  • DOI: {article.doi}")
                messages.append(f"  • Classification: {classification}")
                messages.append(f"  • Reasoning: {reasoning}")
            
            messages.append("\n")
        
        elif node_name == "ner_agent":
            candidates = node_data.get("protein_candidates", [])
            
            messages.append(f"\n{'='*60}")
            messages.append(f"🧬 PROTEIN EXTRACTION - Found {len(candidates)} candidates")
            messages.append(f"{'='*60}")
            
            for i, candidate in enumerate(candidates, 1):
                messages.append(f"\n[Candidate {i}]")
                messages.append(f"Protein: {candidate.protein_name}")
                messages.append(f"Species: {candidate.species}")
                if candidate.accession_id:
                    messages.append(f"Accession: {candidate.accession_id}")
                messages.append(f"Source: {candidate.source_doi}")
            messages.append("")
    
    return "\n".join(messages)


def run_pipeline_worker(job_id: str, initial_state: PipelineState):
    """
    Runs the full graph in a background thread.
    Publishes SSE events for each step and the final result.
    """
    with app.app_context():
        if not graph:
            logger.error(f"[{job_id}] Graph is not compiled. Worker cannot start.")
            sse.publish({"error": "Graph not compiled"}, channel=job_id)
            return

        logger.info(f"[{job_id}] Worker started for query: {initial_state['original_query']}")
        
        try:
            sse.publish({"message": "🚀 Pipeline started..."}, channel=job_id)
        except Exception as e:
            logger.error(f"[{job_id}] SSE publish test failed: {e}", exc_info=True)

        try:
            final_state = None
            
            # Stream events for real-time progress updates
            for event in graph.stream(initial_state):
                
                # Format the event into readable text
                formatted_message = format_event_for_display(event)
                
                # Publish the formatted message
                try:
                    sse.publish({"message": formatted_message}, channel=job_id)
                except Exception as e:
                    logger.error(f"[{job_id}] Failed to publish event: {e}", exc_info=True)
                
                # Capture the last state from the stream
                for node_name, node_state in event.items():
                    if isinstance(node_state, dict):
                        if final_state is None:
                            final_state = node_state.copy()
                        else:
                            final_state.update(node_state)

            if not final_state:
                logger.warning(f"[{job_id}] No final state captured from stream")
                final_state = initial_state

            # Serialize Pydantic models to JSON-safe dicts
            candidates_list = []
            if final_state.get("protein_candidates"):
                candidates_list = [
                    c.model_dump() if hasattr(c, 'model_dump') else c 
                    for c in final_state["protein_candidates"]
                ]

            logger.info(f"[{job_id}] Found {len(candidates_list)} candidates. Publishing results.")

            # Publish the final, structured results
            try:
                sse.publish({"results": candidates_list}, channel=job_id)
            except Exception as e:
                logger.error(f"[{job_id}] Failed to publish results: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"[{job_id}] Pipeline worker failed: {e}", exc_info=True)
            try:
                sse.publish({"error": str(e)}, channel=job_id)
            except Exception:
                pass  # Failed to publish error

        finally:
            logger.info(f"[{job_id}] Worker finished.")
            try:
                sse.publish({"message": "\n✅ PIPELINE COMPLETE"}, channel=job_id)
            except Exception:
                pass  # Failed to publish completion

@app.route("/")
def index():
    """Step 1: Renders the initial query page."""
    return render_template("step1_query.html")

@app.route("/submit", methods=["POST"])
def submit_job():
    """Kicks off the pipeline run in a background thread."""
    query = request.form["query"]
    job_id = str(uuid.uuid4())
    
    logger.info(f"[{job_id}] New job submitted: {query}")
    
    initial_state: PipelineState = {
        "original_query": query,
        "target_protein_count": 5,
        "search_batch_size": 2,
        "articles_to_process": [],
        "confirmed_articles": [],
        "unclear_articles": [],
        "reflection_results": [],
        "protein_candidates": [],
        "validated_uniprot_ids": [],
        "total_articles_fetched": 0
    }

    # Start the pipeline in a separate thread
    thread = threading.Thread(
        target=run_pipeline_worker,
        args=(job_id, initial_state),
        daemon=True  # Make thread daemon so it doesn't block shutdown
    )
    thread.start()
    logger.info(f"[{job_id}] Worker thread started")

    return redirect(url_for("progress_page", job_id=job_id, query=query))

@app.route("/progress")
def progress_page():
    """Step 2: Renders the progress page."""
    job_id = request.args.get("job_id")
    query = request.args.get("query")
    logger.info(f"[{job_id}] Progress page accessed")
    return render_template("step2_progress.html", job_id=job_id, query=query)

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Starting Flask application")
    logger.info(f"Redis URL: {app.config['SSE_REDIS_URL']}")
    logger.info("=" * 60)
    # Set debug=False for production
    app.run(debug=False, threaded=True)
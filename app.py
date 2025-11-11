import logging
import pprint
import threading
import uuid
import warnings
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sse import sse
import redis

# --- Import from existing pipeline ---
from literature_pipeline.graph import create_graph
from literature_pipeline.schemas import PipelineState

# --- Logging ---
REPORT_FILE = "pipeline_run_report.txt"
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more verbose output
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

def run_pipeline_worker(job_id: str, initial_state: PipelineState):
    """
    Runs the full graph in a background thread.
    Publishes SSE events for each step and the final result.
    """
    print(f"\n{'='*80}")
    print(f"DEBUG: Worker thread started for job {job_id}")
    print(f"{'='*80}\n")
    
    with app.app_context():
        print(f"DEBUG: Inside app context for job {job_id}")
        
        if not graph:
            logger.error(f"[{job_id}] Graph is not compiled. Worker cannot start.")
            sse.publish({"error": "Graph not compiled"}, channel=job_id)
            return

        logger.info(f"[{job_id}] Worker started for query: {initial_state['original_query']}")
        
        # Test SSE connection immediately
        try:
            print(f"DEBUG: Testing SSE publish for job {job_id}")
            sse.publish({"message": "=== PIPELINE STARTED ==="}, channel=job_id)
            print(f"DEBUG: SSE test publish successful for job {job_id}")
        except Exception as e:
            print(f"DEBUG: SSE test publish FAILED for job {job_id}: {e}")
            logger.error(f"[{job_id}] SSE publish test failed: {e}", exc_info=True)

        try:
            final_state = None
            event_count = 0
            
            print(f"DEBUG: Starting graph.stream() for job {job_id}")
            
            # Stream events for real-time progress updates
            for event in graph.stream(initial_state):
                event_count += 1
                print(f"DEBUG: Received event #{event_count} for job {job_id}")
                
                # Convert event to string for logging
                event_str = pprint.pformat(event)
                logger.debug(f"[{job_id}] Event: {event_str[:150]}...")
                
                # Publish each event as a message
                try:
                    print(f"DEBUG: Publishing event #{event_count} to SSE for job {job_id}")
                    sse.publish({"message": f"Event {event_count}: {event_str}"}, channel=job_id)
                    print(f"DEBUG: Event #{event_count} published successfully")
                except Exception as e:
                    print(f"DEBUG: Failed to publish event #{event_count}: {e}")
                    logger.error(f"[{job_id}] Failed to publish event: {e}", exc_info=True)
                
                # Capture the last state from the stream
                for node_name, node_state in event.items():
                    print(f"DEBUG: Processing node '{node_name}' from event #{event_count}")
                    if isinstance(node_state, dict):
                        if final_state is None:
                            final_state = node_state.copy()
                        else:
                            final_state.update(node_state)

            print(f"DEBUG: Graph stream complete for job {job_id}. Total events: {event_count}")

            # If we didn't capture a final state, use initial state
            if not final_state:
                logger.warning(f"[{job_id}] No final state captured from stream")
                final_state = initial_state

            # Serialize Pydantic models to JSON-safe dicts
            candidates_list = []
            if final_state.get("protein_candidates"):
                print(f"DEBUG: Processing {len(final_state['protein_candidates'])} candidates")
                candidates_list = [
                    c.model_dump() if hasattr(c, 'model_dump') else c 
                    for c in final_state["protein_candidates"]
                ]

            logger.info(f"[{job_id}] Found {len(candidates_list)} candidates. Publishing results.")

            # Publish the final, structured results
            try:
                print(f"DEBUG: Publishing final results for job {job_id}")
                sse.publish({"results": candidates_list}, channel=job_id)
                print(f"DEBUG: Final results published successfully")
            except Exception as e:
                print(f"DEBUG: Failed to publish final results: {e}")
                logger.error(f"[{job_id}] Failed to publish results: {e}", exc_info=True)

        except Exception as e:
            print(f"DEBUG: Pipeline worker exception for job {job_id}: {e}")
            logger.error(f"[{job_id}] Pipeline worker failed: {e}", exc_info=True)
            try:
                sse.publish({"error": str(e)}, channel=job_id)
            except Exception as pub_error:
                print(f"DEBUG: Failed to publish error: {pub_error}")

        finally:
            logger.info(f"[{job_id}] Worker finished.")
            try:
                print(f"DEBUG: Publishing completion message for job {job_id}")
                sse.publish({"message": "--- PIPELINE COMPLETE ---"}, channel=job_id)
                print(f"DEBUG: Completion message published")
            except Exception as e:
                print(f"DEBUG: Failed to publish completion message: {e}")
            
            print(f"\n{'='*80}")
            print(f"DEBUG: Worker thread finished for job {job_id}")
            print(f"{'='*80}\n")


def test_redis_connection():
    """Test if Redis is accessible"""
    try:
        import redis
        redis_client = redis.StrictRedis.from_url(app.config["SSE_REDIS_URL"])
        redis_client.ping()
        logger.info("✓ Redis connection successful")
        return True
    except Exception as e:
        logger.error(f"✗ Redis connection failed: {e}")
        return False

# Add this after creating the app and before compiling the graph:
if __name__ == "__main__":
    logger.info("Testing Redis connection...")
    if not test_redis_connection():
        logger.error("WARNING: Redis is not running! SSE will not work.")
        logger.error("Please start Redis with: redis-server")

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

# Debug endpoint to test Redis publishing
@app.route("/test-redis/<job_id>")
def test_redis(job_id):
    """Test endpoint to verify Redis publishing works."""
    try:
        with app.app_context():
            sse.publish({"message": "Test message from /test-redis endpoint"}, channel=job_id)
        return jsonify({"status": "success", "message": "Test message published"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Debug endpoint to check Redis subscriptions
@app.route("/debug-redis")
def debug_redis():
    """Debug endpoint to check Redis status."""
    try:
        info = {
            "redis_url": app.config["SSE_REDIS_URL"],
            "redis_ping": redis_client.ping() if redis_client else False,
            "active_channels": redis_client.pubsub_channels() if redis_client else []
        }
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Starting Flask application with debug mode")
    logger.info(f"Redis URL: {app.config['SSE_REDIS_URL']}")
    logger.info("=" * 60)
    app.run(debug=True, threaded=True)
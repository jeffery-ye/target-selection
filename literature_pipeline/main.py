from .graph import create_graph

def run():
    """Initializes and runs the LangGraph workflow."""
    app = create_graph()

    initial_input = {
        "query": "drug targets for Coccidioides immitis",
        "articles": []
    }

    final_state = app.invoke(initial_input)

    print("\nGraph execution complete.")
    print(f"Final state: {final_state}")

if __name__ == "__main__":
    run()

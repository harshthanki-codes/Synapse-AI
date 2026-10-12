import os
import sys
import logging
from typing import Annotated, TypedDict
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# --- State ---
class AgentState(TypedDict):
    items: list[str]
    results: dict[str, str]
    current_index: int
    llm_call_count: int

# --- LLM (Multi-key fallback to prevent quota exhaustion) ---
api_keys = [os.environ.get(f"GEMINI_API_KEY_{i}") for i in range(1, 6) if os.environ.get(f"GEMINI_API_KEY_{i}")]

if api_keys:
    llms = [ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", temperature=0, max_retries=0, api_key=key) for key in api_keys]
    llm = llms[0].with_fallbacks(llms[1:]) if len(llms) > 1 else llms[0]
else:
    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", temperature=0, max_retries=0)

# --- Nodes ---
def process_item(state: AgentState):
    """Processes the current item and increments the index."""
    idx = state.get("current_index", 0)
    items = state.get("items", [])
    results = dict(state.get("results", {}))
    calls = state.get("llm_call_count", 0)
    
    if idx >= len(items):
        return state # Should not happen based on routing, but safe
        
    item = items[idx]
    logger.info(f"\n--- PROCESSING ITEM {idx + 1}/{len(items)} ---")
    logger.info(f"Content: {item}")
    
    # Deliberately poison item index 2 to test the validation check later
    if idx == 2:
        logger.warning("[!] Deliberately poisoning result for item 3 (index 2)")
        summary = "EMPTY_OR_CORRUPTED_RESULT"
    else:
        prompt = f"Summarize this short text in one sentence: {item}"
        response = llm.invoke([HumanMessage(content=prompt)])
        calls += 1
        # Robustly handle if the model returns a list or a string
        raw_content = response.content
        if isinstance(raw_content, list):
            # Extract text from the first item if it's a list of dictionaries
            summary = raw_content[0].get("text", "").strip() if isinstance(raw_content[0], dict) else str(raw_content).strip()
        else:
            summary = raw_content.strip()
        
    results[f"item_{idx}"] = summary
    logger.info(f"Result saved: {summary}")
    
    return {
        "results": results,
        "completed_items": results,
        "current_index": idx + 1,
        "llm_call_count": calls
    }

def check_results(state: AgentState):
    """Self-check node that verifies all items were processed correctly."""
    logger.info("\n--- RUNNING SELF-CHECK VALIDATION ---")
    
    items = state["items"]
    results = state["results"]
    calls = state.get("llm_call_count", 0)
    
    for i, original_text in enumerate(items):
        key = f"item_{i}"
        result = results.get(key, "")
        
        logger.info(f"Validating item {i+1}...")
        
        class Validation(BaseModel):
            is_valid: bool = Field(description="True if the summary accurately reflects the text and is not blank/corrupted.")
            reason: str = Field(description="Reason for validity or invalidity")
            
        validator_llm = llm.with_structured_output(Validation)
        prompt = f"Original text: {original_text}\n\nSummary: {result}\n\nIs this summary a valid, non-empty reflection of the original text?"
        
        val_res = validator_llm.invoke([HumanMessage(content=prompt)])
        calls += 1
        
        if not val_res.is_valid:
            logger.error(f"[!] VALIDATION FAILED on item {i+1}: {val_res.reason}")
        else:
            logger.info(f"[✓] Item {i+1} passed validation.")
            
    return {"llm_call_count": calls}

# --- Routing ---
def route_processing(state: AgentState, config: RunnableConfig | None = None):
    idx = state.get("current_index", 0)
    items = state.get("items", [])
    
    if idx < len(items):
        crash_enabled = True
        if config and isinstance(config, dict) and "configurable" in config:
            crash_enabled = config["configurable"].get("crash_at_item_3", True)

        # We simulate a crash/stop after the 2nd item (index 1) has been processed.
        # This allows us to demonstrate resume functionality.
        if crash_enabled and idx == 2 and not os.path.exists(".resumed"):
            logger.critical("\n[FATAL] Simulated crash! Process interrupted before processing item 3.")
            with open(".resumed", "w") as f:
                f.write("true") # Marker so we don't crash again on resume
            sys.exit(1)
            
        return "process"
    return "check"

# --- Graph Assembly ---
workflow = StateGraph(AgentState)
workflow.add_node("process", process_item)
workflow.add_node("check", check_results)

workflow.set_entry_point("process")
workflow.add_conditional_edges("process", route_processing, {"process": "process", "check": "check"})
workflow.add_edge("check", END)

import sqlite3
# Set up Sqlite checkpointing
conn = sqlite3.connect("state.db", check_same_thread=False)
memory = SqliteSaver(conn)
app = workflow.compile(checkpointer=memory)

if __name__ == "__main__":
    thread_config = {"configurable": {"thread_id": "assignment_3_run"}}
    
    initial_items = [
        "Company A reported a 20% increase in revenue, largely driven by their new cloud division.",
        "Company B saw flat growth but is investing $2B into generative AI data centers.",
        "Company C announced layoffs of 500 people to restructure their hardware operations.",
        "Company D acquired a small startup to bolster their machine learning models."
    ]
    
    # Initialize state only if we are starting fresh (idx 0)
    state = app.get_state(thread_config)
    if not state.values:
        logger.info("Starting fresh run...")
        initial_state = {
            "items": initial_items,
            "results": {},
            "current_index": 0,
            "llm_call_count": 0
        }
        app.update_state(thread_config, initial_state)
    else:
        logger.info(f"Resuming run from index {state.values.get('current_index')}...")

    # Run the graph
    # If the process hits the simulated crash, it will sys.exit(1).
    # When you run the script again, it will resume from the checkpoint.
    try:
        final_state = app.invoke(None, config=thread_config)
        print("\n" + "="*50)
        print("WORKFLOW COMPLETE")
        print("="*50)
        print(f"Total LLM Calls Made: {final_state['llm_call_count']}")
    except SystemExit:
        print("\nProcess exited. Run the script again to resume.")

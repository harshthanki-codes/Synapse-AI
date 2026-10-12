import os
import sys
import logging
from typing import Annotated, TypedDict
from dotenv import load_dotenv

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.callbacks import BaseCallbackHandler

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# --- Token Tracking Callback ---
class TokenTrackingCallback(BaseCallbackHandler):
    def __init__(self):
        self.total_tokens = 0
        self.total_calls = 0

    def on_llm_end(self, response, **kwargs):
        self.total_calls += 1
        if response.llm_output and "token_usage" in response.llm_output:
            self.total_tokens += response.llm_output["token_usage"].get("total_tokens", 0)

token_tracker = TokenTrackingCallback()

# --- State ---
class AgentState(TypedDict):
    task: str
    worker_output: str
    review_verdict: str
    review_reason: str

# --- Pydantic Models for Structured Output ---
class ReviewResult(BaseModel):
    is_approved: bool = Field(description="True if the output meets all criteria, False otherwise.")
    reason: str = Field(description="Specific, concrete reasons for approval or rejection.")

# Backward compatibility alias
ReviewVerdict = ReviewResult

# --- LLM Initialization (Multi-key fallback for quota limits) ---
api_keys = [os.environ.get(f"GEMINI_API_KEY_{i}") for i in range(1, 6) if os.environ.get(f"GEMINI_API_KEY_{i}")]

if api_keys:
    llms = [ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", temperature=0, max_retries=0, callbacks=[token_tracker], api_key=key) for key in api_keys]
    llm = llms[0].with_fallbacks(llms[1:]) if len(llms) > 1 else llms[0]
else:
    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", temperature=0, max_retries=0, callbacks=[token_tracker])

# --- Nodes ---
def worker_node(state: AgentState):
    logger.info("--- WORKER AGENT RUNNING ---")
    prompt = f"Write a Python function for the following task:\n{state['task']}\n\nOnly output the code, no markdown wrappers."
    
    response = llm.invoke([HumanMessage(content=prompt)])
    logger.info("Worker produced output.")
    
    return {"worker_output": response.content}

def reviewer_node(state: AgentState):
    logger.info("--- REVIEWER AGENT RUNNING ---")
    
    # Define concrete criteria
    criteria = (
        "1. Must use the standard library 'time' module for sleeping.\n"
        "2. Must include type hints.\n"
        "3. Must not contain any syntax errors or incomplete code.\n"
    )
    
    prompt = f"""
    Review the following Python code against these strict criteria:
    {criteria}
    
    Task: {state['task']}
    Code to review:
    {state['worker_output']}
    
    If it fails ANY criteria, reject it with a specific reason.
    """
    
    # Use structured output for the reviewer
    reviewer_llm = llm.with_structured_output(ReviewResult)
    result = reviewer_llm.invoke([HumanMessage(content=prompt)])
    
    verdict = "approved" if result.is_approved else "rejected"
    logger.info(f"Reviewer Verdict: {verdict.upper()}")
    
    return {"review_verdict": verdict, "review_reason": result.reason}

# --- Graph Assembly ---
workflow = StateGraph(AgentState)
workflow.add_node("worker", worker_node)
workflow.add_node("reviewer", reviewer_node)

workflow.set_entry_point("worker")
workflow.add_edge("worker", "reviewer")
workflow.add_edge("reviewer", END)

app = workflow.compile()

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "approve"
    
    if mode == "approve":
        # Simple task that it will get right
        task = "Write a function that takes two numbers and returns their sum. Include type hints."
    else:
        # Complex task designed to fail a strict criterion (e.g., we ask for no sleep but the worker might use it, or we ask for a complex retry decorator that it might mess up)
        task = "Write a complex asynchronous retry decorator with exponential backoff. Do not use type hints."

    print(f"\n=== RUNNING MODE: {mode.upper()} ===\n")
    initial_state = {"task": task}
    
    result = app.invoke(initial_state)
    
    print("\n" + "="*50)
    print("FINAL REPORT:")
    print("="*50)
    print(f"Verdict: {result['review_verdict'].upper()}")
    print(f"Reason: {result['review_reason']}")
    print("-" * 50)
    print("Worker Output:")
    print(result['worker_output'])
    
    print("\n" + "="*50)
    print(f"Total LLM Calls: {token_tracker.total_calls}")
    print(f"Total Tokens Used: {token_tracker.total_tokens}")

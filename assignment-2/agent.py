import ast
import os
import sys
import time
import logging
from typing import Annotated, Literal, TypedDict
from utils.helpers import load_env, strip_code_fences, telemetry_tracker

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.callbacks import BaseCallbackHandler

load_env()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# --- Token Tracking Callback ---
class TokenTrackingCallback(BaseCallbackHandler):
    def __init__(self):
        self.total_tokens = 0
        self.total_calls = 0

    def on_llm_end(self, response, **kwargs):
        self.total_calls += 1
        tokens_added = 0
        if getattr(response, "llm_output", None) and "token_usage" in response.llm_output:
            tokens_added = response.llm_output["token_usage"].get("total_tokens", 0)
        elif getattr(response, "generations", None):
            for gen_list in response.generations:
                for gen in gen_list:
                    msg = getattr(gen, "message", None)
                    usage = getattr(msg, "usage_metadata", None)
                    if isinstance(usage, dict):
                        tokens_added += usage.get("total_tokens", 0)
        self.total_tokens += tokens_added

token_tracker = TokenTrackingCallback()

# --- State ---
class AgentState(TypedDict, total=False):
    task: str
    worker_output: str
    review_verdict: str
    review_reason: str
    revision_count: int
    max_revisions: int

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
    feedback = state.get("review_reason", "")
    revision = state.get("revision_count", 0)
    if revision > 0 and feedback:
        prompt = (
            f"Write a Python function for the following task:\n{state['task']}\n\n"
            f"Previous attempt was rejected by Reviewer for this reason:\n{feedback}\n\n"
            f"Fix all issues, include full type hints, and only output valid Python code with no markdown wrappers."
        )
    else:
        prompt = f"Write a Python function for the following task:\n{state['task']}\n\nOnly output the code, no markdown wrappers."
    
    t0 = time.perf_counter()
    response = llm.invoke([HumanMessage(content=prompt)])
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    cleaned_code = strip_code_fences(response.content)
    telemetry_tracker.record_event("Worker-Core2", elapsed_ms, tokens=max(len(cleaned_code) // 4, 20), status="ACTIVE")
    logger.info("Worker produced output.")
    
    return {"worker_output": cleaned_code}

def reviewer_node(state: AgentState):
    logger.info("--- REVIEWER AGENT RUNNING ---")
    task_text = state.get("task", "")
    code_text = strip_code_fences(state.get("worker_output", ""))
    revision_count = state.get("revision_count", 0) + 1

    # Deterministic AST syntax check first
    try:
        ast.parse(code_text)
    except SyntaxError as syn_err:
        reason = f"SyntaxError in generated Python code at line {syn_err.lineno}: {syn_err.msg}"
        logger.info("Reviewer Verdict: REJECTED (AST SyntaxError)")
        return {"review_verdict": "rejected", "review_reason": reason, "revision_count": revision_count}

    needs_time_module = any(w in task_text.lower() for w in ("sleep", "retry", "backoff", "delay", "wait"))
    time_criterion = (
        "1. Must use the standard library 'time' module for sleeping/delays.\n"
        if needs_time_module
        else "1. Must use clean, idiomatic standard Python constructs.\n"
    )
    criteria = (
        f"{time_criterion}"
        "2. Must include type hints on function parameters and return value.\n"
        "3. Must not contain any syntax errors or incomplete code.\n"
    )
    
    prompt = f"""
    Review the following Python code against these strict criteria:
    {criteria}
    
    Task: {task_text}
    Code to review:
    {code_text}
    
    If it fails ANY criteria, reject it with a specific reason.
    """
    
    t0 = time.perf_counter()
    reviewer_llm = llm.with_structured_output(ReviewResult)
    result = reviewer_llm.invoke([HumanMessage(content=prompt)])
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    telemetry_tracker.record_event("Reviewer-Core2", elapsed_ms, tokens=max(len(result.reason) // 4, 20), status="ACTIVE")
    
    verdict = "approved" if result.is_approved else "rejected"
    logger.info(f"Reviewer Verdict: {verdict.upper()}")
    
    return {
        "review_verdict": verdict,
        "review_reason": result.reason,
        "revision_count": revision_count,
    }

def should_retry_review(state: AgentState) -> Literal["worker", "__end__"]:
    """Routes back to worker if rejected and within max_revisions budget."""
    verdict = state.get("review_verdict", "")
    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions", 0)
    if verdict == "rejected" and revision_count <= max_revisions:
        logger.info(f"Routing back to Worker for self-correction (Revision {revision_count}/{max_revisions})...")
        return "worker"
    return "__end__"

# --- Graph Assembly ---
workflow = StateGraph(AgentState)
workflow.add_node("worker", worker_node)
workflow.add_node("reviewer", reviewer_node)

workflow.set_entry_point("worker")
workflow.add_edge("worker", "reviewer")
workflow.add_conditional_edges("reviewer", should_retry_review, {"worker": "worker", "__end__": END})

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

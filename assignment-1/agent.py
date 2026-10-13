import os
import sys
import time
import logging
from typing import Annotated, Sequence, TypedDict, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_google_genai import ChatGoogleGenerativeAI
from utils.helpers import load_env, telemetry_tracker

load_env()

# Configure logging for standard output reasoning traces
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """State tracks message history, tool execution limits, and failure conditions."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    tool_call_count: int
    should_fail: bool  # Flag to inject mock failure for resilience testing

# --- Tools ---
@tool
def calculate_latency_budget(db_read_ms: int, network_ms: int, compute_ms: int) -> str:
    """Calculates total pipeline latency given component latencies."""
    total = db_read_ms + network_ms + compute_ms
    return f"Total latency budget is {total}ms."

@tool
def search_caching_strategies(query: str) -> str:
    """Searches a knowledge base for caching strategies."""
    if "redis" in query.lower() or "heavy" in query.lower():
        return "Redis is highly recommended for read-heavy workloads with 10k req/sec due to low-latency memory access and pub/sub capabilities."
    return "Consider CDN caching for static assets, and Redis/Memcached for dynamic application data."

@tool
def fetch_system_metrics(system_name: str) -> str:
    """Fetches real-time performance metrics of a target system."""
    return f"Metrics for {system_name}: 99th percentile latency is 150ms. CPU usage 85%."

tools = [calculate_latency_budget, search_caching_strategies, fetch_system_metrics]

# Initialize LLM with Gemini (Multi-key fallback to prevent quota exhaustion)
api_keys = [os.environ.get(f"GEMINI_API_KEY_{i}") for i in range(1, 6) if os.environ.get(f"GEMINI_API_KEY_{i}")]

if api_keys:
    llms = [ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", temperature=0, max_retries=0, api_key=key) for key in api_keys]
    llm = llms[0].with_fallbacks(llms[1:]) if len(llms) > 1 else llms[0]
else:
    # Fallback to default system key if specific keys aren't set yet
    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", temperature=0, max_retries=0)

llm_with_tools = llm.bind_tools(tools)

# --- Nodes ---
def call_agent(state: AgentState):
    """Invokes the agent LLM and records reasoning."""
    messages = state["messages"]
    logger.info("\n--- LLM REASONING STEP ---")
    
    t0 = time.perf_counter()
    try:
        response = llm_with_tools.invoke(messages)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        telemetry_tracker.record_event("Researcher-Core1", elapsed_ms, tokens=max(len(str(response.content)) // 4, 25), status="ACTIVE")
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        logger.error(f"LLM invocation error: {exc}")
        telemetry_tracker.record_event("Researcher-Core1", elapsed_ms, tokens=0, status="DEGRADED")
        response = AIMessage(content=f"Fallback response (LLM unavailable): {exc}")
    
    # Trace logic
    if getattr(response, "tool_calls", None):
        for tc in response.tool_calls:
            logger.info(f"DECISION: Call tool '{tc['name']}' with args {tc['args']}.")
            logger.info(f"REASON: The agent requires this data to formulate an answer.")
    else:
        logger.info(f"DECISION: Generate final answer.")
        logger.info(f"REASON: Sufficient context gathered.")

    return {"messages": [response]}

def execute_tools(state: AgentState):
    """Executes tools and handles failures gracefully."""
    messages = state["messages"]
    last_message = messages[-1]
    
    tool_count = state.get("tool_call_count", 0)
    should_fail = state.get("should_fail", False)
    
    tool_responses = []
    
    for tool_call in last_message.tool_calls:
        tool_count += 1
        name = tool_call["name"]
        
        # Inject deterministic failure on first tool call if requested
        if should_fail and tool_count == 1:
            logger.warning(f"\n[!] INJECTED MOCK FAILURE FOR TOOL '{name}'")
            error_msg = f"Error: Tool '{name}' timed out after 5000ms. Please try again or use an alternative approach."
            tool_responses.append(ToolMessage(content=error_msg, name=name, tool_call_id=tool_call["id"]))
            should_fail = False # Reset so retry succeeds
            continue

        logger.info(f"\nExecuting tool '{name}'...")
        tool_func = {t.name: t for t in tools}.get(name)
        if tool_func:
            try:
                result = tool_func.invoke(tool_call["args"])
                tool_responses.append(ToolMessage(content=result, name=name, tool_call_id=tool_call["id"]))
                logger.info(f"Result: {result}")
            except Exception as e:
                tool_responses.append(ToolMessage(content=f"Execution error: {str(e)}", name=name, tool_call_id=tool_call["id"]))
                logger.error(f"Execution error: {str(e)}")
        else:
             tool_responses.append(ToolMessage(content=f"Error: Tool '{name}' not found.", name=name, tool_call_id=tool_call["id"]))
             
    return {"messages": tool_responses, "tool_call_count": tool_count, "should_fail": should_fail}

# --- Routing ---
def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    """Determines if we continue to tools or terminate."""
    last_message = state["messages"][-1]
    
    # If no tool calls, we are done
    if not last_message.tool_calls:
        return "__end__"
        
    # hard limit on tool calls
    if state.get("tool_call_count", 0) >= 6:
        logger.warning("\n[!] TOOL CALL LIMIT REACHED (6). FORCING EXIT.")
        return "__end__"
        
    return "tools"

# --- Graph Assembly ---
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_agent)
workflow.add_node("tools", execute_tools)

workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

app = workflow.compile()

if __name__ == "__main__":
    question = (
        "What's the best caching strategy for a read-heavy API with 10k req/sec? "
        "Also calculate my latency budget if DB is 150ms, Network is 20ms, Compute is 50ms."
    )
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "clean"
    inject = (mode == "fail")
    
    print(f"\n=== RUNNING MODE: {mode.upper()} ===\n")
    initial_state = {"messages": [HumanMessage(content=question)], "tool_call_count": 0, "should_fail": inject}
    
    result = app.invoke(initial_state)
    
    print("\n" + "="*50)
    print("FINAL OUTPUT:")
    print("="*50)
    print(result["messages"][-1].content)
    print(f"\nTotal Tool Calls Executed: {result.get('tool_call_count', 0)}")

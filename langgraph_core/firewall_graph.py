# langgraph_core/firewall_graph.py

from concurrent.futures import ThreadPoolExecutor, as_completed
from langgraph.graph import StateGraph, END
from agents.prompt_scan_agent import PromptScanAgent
from agents.safe_prompt_agent import SafePromptAgent
from agents.response_verifier_agent import ResponseVerifierAgent
from agents.audit_chain_agent import AuditChainAgent
from agents.attack_detection_agent import AttackDetectionAgent
# These agents are now imported at the top level for better organization
from agents.code_validation_agent import CodeValidationAgent
from agents.web_search_agent import WebSearchAgent
# Note: You will need to create this new, consolidated agent.
from agents.intial_analysis_agent import InitialAnalysisAgent
from llm_utils import call_llm
from typing import TypedDict, Optional, Dict, Any

RISK_BLOCK_THRESHOLD = 0.85  # Risk score threshold for blocking
RISK_FAST_PATH_THRESHOLD = 0.3  # Risk score threshold for fast verification path


# Step 1: Define system state
class FirewallState(TypedDict):
    user_prompt: str
    classification: Optional[str]
    risk_reason: Optional[str]
    risk_score: Optional[float]
    final_prompt: Optional[str]
    llm_response: Optional[str]
    verdict: Optional[str]
    code_verdict: Optional[str]
    code_fragment: Optional[str]
    attack_detection: Optional[Dict[str, Any]]
    blockchain_log: Optional[bool]


# --- Agent Instantiation ---
# Agents are instantiated once at the module level and reused.
# This avoids the overhead of re-creating them on every graph run.

# Note: You will need to create this new agent. It should be designed to
# perform both prompt classification and attack detection in a single LLM call.
initial_analyzer = InitialAnalysisAgent()

prompt_rewriter = SafePromptAgent()
response_verifier = ResponseVerifierAgent()
code_validator = CodeValidationAgent()
web_searcher = WebSearchAgent()
audit_logger = AuditChainAgent()


# --- Node Definitions ---

def initial_analysis_node(state: FirewallState) -> FirewallState:
    """
    OPTIMIZATION: Combines prompt scanning and attack detection into a single
    agent call to reduce the number of sequential LLM calls.
    """
    analysis_result = initial_analyzer.run(state["user_prompt"])

    state["classification"] = analysis_result.get("classification")
    state["risk_score"] = analysis_result.get("risk_score", 0.0)
    state["risk_reason"] = analysis_result.get("reason", "")
    state["attack_detection"] = analysis_result.get("attack_detection", {})
    return state


def safe_prompt_node(state: FirewallState) -> FirewallState:
    """Rewrites risky prompts to be safer."""
    state["final_prompt"] = prompt_rewriter.run(state["user_prompt"])
    return state


def passthrough_prompt_node(state: FirewallState) -> FirewallState:
    """Passes the prompt through unchanged."""
    state["final_prompt"] = state["user_prompt"]
    return state


def blocked_prompt_node(state: FirewallState) -> FirewallState:
    """Blocks the prompt and sets a rejection message."""
    state["final_prompt"] = "[BLOCKED due to safety policy]"
    state["llm_response"] = "⛔ This prompt is blocked."
    state["verdict"] = "Prompt rejected due to risk."
    state["blockchain_log"] = True  # Log blocked prompts
    return state


def llm_response_node(state: FirewallState) -> FirewallState:
    """Calls the LLM if not already present."""
    if "llm_response" not in state or not state["llm_response"]:
        state["llm_response"] = call_llm(state["final_prompt"])
    return state


def verify_response_node(state: FirewallState) -> FirewallState:
    """
    OPTIMIZATION: Verifies the LLM response for factuality, code validity,
    and web consistency in parallel to dramatically reduce latency.
    """
    prompt = state.get("final_prompt") or ""
    response = state.get("llm_response") or ""

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_task = {
            executor.submit(response_verifier.run, prompt, response): "verdict",
            executor.submit(code_validator.run, prompt, response): "code",
            executor.submit(web_searcher.run, prompt, response): "search",
        }

        for future in as_completed(future_to_task):
            task_name = future_to_task[future]
            try:
                result = future.result()
                if task_name == "verdict":
                    if isinstance(result, dict):
                        state["verdict"] = result.get("verdict")
                    else:
                        state["verdict"] = result
                elif task_name == "code":
                    state.update(result)
                elif task_name == "search":
                    state.update(result)
            except Exception as e:
                print(f"Error in verification task '{task_name}': {e}")
                if task_name == "verdict":
                    state["verdict"] = f"Error: {e}"
                elif task_name == "code":
                    state["code_verdict"] = f"Error: {e}"

    return state


def fast_verify_response_node(state: FirewallState) -> FirewallState:
    """Fast verification for low-risk prompts - minimal checks."""
    state["verdict"] = "Likely factual - low risk prompt"
    state["code_verdict"] = "Skipped - low risk"
    state["code_fragment"] = None
    return state


def log_audit_node(state: FirewallState) -> FirewallState:
    """Logs the event if necessary."""
    """
    OPTIMIZATION: High-cost logging is run in a background thread to avoid
    blocking the final response to the user.
    """
    # Determine if we should log to blockchain (risk score > 0.85)
    risk_score = state.get("risk_score", 0.0)
    attack_detection = state.get("attack_detection", {})
    overall_attack_score = attack_detection.get("overall_risk_score", 0.0)

    # Log if high risk or attack detected
    should_log = (
            risk_score >= RISK_BLOCK_THRESHOLD or
            overall_attack_score >= RISK_BLOCK_THRESHOLD or
            state.get("blockchain_log", False)
    )

    if should_log:
        state["blockchain_log"] = True

        def background_log(current_state):
            """Function to run the logger in a separate thread."""
            try:
                print("Starting background audit log...")
                audit_logger.log_event(current_state)
                print("Background audit log finished successfully.")
            except Exception as e:
                # Log any errors from the background task
                print(f"CRITICAL: Background audit logging failed: {e}")

        # Submit the logging task to a thread pool to run asynchronously
        ThreadPoolExecutor(max_workers=1).submit(background_log, state.copy())

    return state


# Step 3: Build LangGraph flow
def build_firewall_graph():
    builder = StateGraph(FirewallState)

    builder.add_node("initial_analysis", initial_analysis_node)
    builder.add_node("rewrite_prompt", safe_prompt_node)
    builder.add_node("passthrough_prompt", passthrough_prompt_node)
    builder.add_node("blocked", blocked_prompt_node)
    builder.add_node("llm_call", llm_response_node)
    builder.add_node("verify", verify_response_node)
    builder.add_node("fast_verify", fast_verify_response_node)
    builder.add_node("audit", log_audit_node)

    # ✅ This sets the START node
    builder.set_entry_point("initial_analysis")

    # Conditional branching after attack detection
    builder.add_conditional_edges(
        "initial_analysis",
        lambda state: "Blocked" if state["classification"] == "Blocked" or float(
            state.get("risk_score") or 0.0) >= RISK_BLOCK_THRESHOLD else state["classification"],
        {
            "Safe": "passthrough_prompt",
            "Risky": "rewrite_prompt",  # Always rewrite risky prompts
            "Blocked": "blocked"
        }
    )

    # Fast path for very low risk prompts - skip heavy verification
    builder.add_conditional_edges(
        "llm_call",
        lambda state: "fast_verify" if float(state.get("risk_score") or 0.0) < RISK_FAST_PATH_THRESHOLD else "verify",
        {
            "fast_verify": "fast_verify",
            "verify": "verify"
        }
    )

    builder.add_edge("rewrite_prompt", "llm_call")  # Risky prompts go through SafePromptAgent
    builder.add_edge("passthrough_prompt", "llm_call")  # Safe prompts go directly to LLM
    builder.add_edge("fast_verify", "audit")
    builder.add_edge("verify", "audit")
    builder.add_edge("blocked", "audit")  # No LLM if blocked
    builder.add_edge("audit", END)

    return builder.compile()
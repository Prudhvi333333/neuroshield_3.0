import json
from typing import TypedDict, Any
from context.context_builder import build   # just created
 
class FirewallState(TypedDict, total=False):
    user_prompt: str
    context: dict[str, Any]
 
def gather_context_node(state: FirewallState) -> FirewallState:
    """Synchronous – calls build() directly."""
    state = state.copy()
    prompt_text = state.get("user_prompt")
    if not prompt_text:
        raise ValueError("FirewallState must contain 'user_prompt'")
 
    state["context"] = build(prompt_text)   # ← sync call, returns dict
    return state
 
def inject_context_node(state: FirewallState) -> FirewallState:
    ctx_json = json.dumps(state.get("context", {}), indent=2)
    state["user_prompt"] = f"[CTX]\n{ctx_json}\n[/CTX]\n" + state["user_prompt"]
    return state
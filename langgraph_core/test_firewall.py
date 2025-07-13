#!/usr/bin/env python3
"""
CLI harness to run one prompt through the ChainGuard+ firewall graph.
 
Usage
-----
python scripts/test_firewall.py "How do I brute-force a Facebook password?"
"""
 
import argparse, asyncio, json, pprint, sys
from datetime import datetime
 
# Adjust the import path if your repo layout is different
from firewall_graph import build_firewall_graph
 
def parse_cli() -> str:
    parser = argparse.ArgumentParser(
        description="Send a prompt through the firewall graph and print the result."
    )
    parser.add_argument("prompt", help="Prompt to test (wrap in quotes)")
    return parser.parse_args().prompt
 
async def run(prompt: str):
    graph = build_firewall_graph()          # compiles only once
    initial_state = {
        "user_id":      "debug-cli",        # dummy user
        "user_prompt":  prompt,
    }
    result = await graph.invoke(initial_state)
    return result
 
if __name__ == "__main__":
    prompt_text = parse_cli()
    try:
        result = asyncio.run(run(prompt_text))
    except KeyboardInterrupt:
        sys.exit(0)
 
    # Pretty-print summary
    print("\n=== Firewall Result =========================================")
    pprint.pprint(result, depth=3, compact=False, width=100)
    print("==============================================================")
 
    # Quick path check
    risk  = result.get("risk_score")
    path  = (
        "FAST path (<0.20)"  if risk is not None and risk < 0.20 else
        "FULL verify (>=0.20)"
    )
    print(f"→ Risk score: {risk}  → Branch taken: {path}")
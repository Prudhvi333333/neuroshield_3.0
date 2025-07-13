# # context/context_builder.py
# """
# Builds a structured context object for every user prompt.
 
# Pulls from:
#   • Firestore user profile           (async)
#   • BigQuery – last 3 prompts        (async)
#   • RAG vector store (optional)      (async)
#   • Lightweight goal inference       (LLM, temperature 0)
# Return shape:
# {
#   "user_id": "abc123",
#   "profile": {...},
#   "recent_prompts": ["...", "...", "..."],
#   "session_goal": "Convert MySQL queries to SQLMI",
#   "examples": [ { "text": "...", "score": 0.78 }, ... ]
# }
# """
# import asyncio, os, json
# from datetime import datetime, timezone
 
# from google.cloud import firestore_async, bigquery
# from vertexai.generative_models import GenerativeModel
# from vertexai import init as vertex_init
 
# PROJECT_ID  =  "fqkmwqpb-61mr-00mp-3824-ymblnk"
# LOCATION    = "global"
# MODEL_NAME  = "gemini-2.5-pro"
 
# vertex_init(project=PROJECT_ID, location=LOCATION)
 
# _llm = GenerativeModel(MODEL_NAME, generation_config={"temperature": 0.0})
# _fs  = firestore_async.AsyncClient()
# _bq  = bigquery.Client()
 
# # ---------- Firestore helpers ---------- #
# async def _get_profile(user_id: str) -> dict:
#     doc = await _fs.collection("users").document(user_id).get()
#     return doc.to_dict() or {}
 
# # ---------- BigQuery helpers ---------- #
# async def _get_recent_prompts(user_id: str, limit:int=3) -> list[str]:
#     sql = """
#         SELECT prompt
#         FROM  `neuroshield_logs.events_*`
#         WHERE user_id = @uid
#         ORDER BY timestamp DESC
#         LIMIT @lim
#     """
#     job = _bq.query(
#         sql,
#         job_config=bigquery.QueryJobConfig(
#             query_parameters=[
#                 bigquery.ScalarQueryParameter("uid",  "STRING", user_id),
#                 bigquery.ScalarQueryParameter("lim",  "INT64",  limit),
#             ]
#         ),
#     )
#     return [row.prompt for row in job]
 
# # ---------- Goal inference ---------- #
# async def _infer_goal(raw_prompt:str, history:list[str]) -> str:
#     prompt = f"""
# Given this new user prompt and their recent prompt history,
# briefly infer the user’s **current goal** in one short sentence.
 
# ### Recent History
# {json.dumps(history, indent=2)}
 
# ### New Prompt
# {raw_prompt}
 
# Respond ONLY with the goal sentence.
# """
#     resp = await _llm.generate_content_async(prompt)
#     return resp.text.strip()
 
# # ---------- MAIN entry ---------- #
# async def build(user_id:str, raw_prompt:str) -> dict:
#     profile_task  = asyncio.create_task(_get_profile(user_id))
#     recent_task   = asyncio.create_task(_get_recent_prompts(user_id))
    
#     # Run profile + recent prompts in parallel
#     profile, recent = await asyncio.gather(profile_task, recent_task)
 
#     # Lightweight goal inference (can be skipped if you want absolute speed)
#     goal = await _infer_goal(raw_prompt, recent)
 
#     # TODO: plug in RAG retrieval here if desired
#     examples = []   # leave empty for now
 
#     return {
#         "user_id": user_id,
#         "profile": profile,
#         "recent_prompts": recent,
#         "session_goal": goal,
#         "examples": examples,
# "ctx_timestamp": datetime.now(timezone.utc).isoformat()
#     }

"""
Context Builder – ultra-light, synchronous, uses existing call_llm()
 
Returns:
{
  "session_goal":  "<one-line inferred goal>",
  "ctx_timestamp": "<UTC ISO-time>"
}
"""
 
from datetime import datetime, timezone
from llm_utils import call_llm   # already configured for Gemini via Vertex AI
 
def infer_goal(raw_prompt: str) -> str:
    """Ask the LLM (temperature-0) to summarise the user’s goal."""
    system_msg = (
        "You are a concise goal-inferrer. "
        "Given the following prompt, reply with ONE short sentence that "
        "captures the user's goal. Respond with only that sentence."
    )
    return call_llm(prompt=raw_prompt, system_msg=system_msg).strip()
 
def build(raw_prompt: str) -> dict:
    return {
        "session_goal":  infer_goal(raw_prompt),
"ctx_timestamp": datetime.now(timezone.utc).isoformat()
    }
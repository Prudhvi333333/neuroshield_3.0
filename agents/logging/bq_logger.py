# logging/bq_logger.py
"""
Tiny helper that streams a single JSON event to BigQuery.
Assumes the table neuroshield_logs.events exists (partitioned by ingestion time).
"""
 
import hashlib, json, os
from datetime import datetime, timezone
 
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError
 
PROJECT_ID   = "fqkmwqpb-61mr-00mp-3824-ymblnk"          # set in Cloud Run / local env
DATASET_ID   = "neuroshield_logs"
TABLE_ID     = "events"                           # final table = project.dataset.table
 
_bq_client   = bigquery.Client(project=PROJECT_ID)
_FULL_TABLE  = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
 
def _digest_ctx(ctx: dict | None) -> str:
    """Return a short sha1 of the context block so we don’t store the full blob."""
    if not ctx:
        return ""
    s = json.dumps(ctx, sort_keys=True).encode()
    return hashlib.sha1(s).hexdigest()[:12]
 
def write_event(event: dict):
    """
    Convert the in-memory firewall `state` into a BigQuery row and stream it.
    Raises RuntimeError on insert errors so callers can catch/log.
    """
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id":       event.get("user_id", "anon"),
        "prompt":        event.get("user_prompt", "")[:10_000],   # BQ string limit 16MB
        "classification":event.get("classification"),
        "risk_score":    float(event.get("risk_score", 0.0)),
        "attack_flags":  event.get("attack_detection", {}),
        "verdict":       event.get("verdict"),
        "context_digest":_digest_ctx(event.get("context")),
    }
 
    errors = _bq_client.insert_rows_json(_FULL_TABLE, [row])
    if errors:
        raise RuntimeError(f"BQ insert failed: {errors}")
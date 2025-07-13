# agents/audit_chain_agent.py

import json
import os
from datetime import datetime

class AuditChainAgent:
    def __init__(self, log_file="logs/audit_log.json"):
        self.log_file = log_file
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def log_event(self, event_data):
        """
        Logs event only if necessary:
        - Prompt is classified as Risky or Blocked
        - Response is marked as Hallucinated

        This method appends log entries as JSON lines for high performance,
        avoiding reading the entire log file for each event.
        """
        classification = event_data.get("classification", "Safe")
        verdict = event_data.get("verdict", "")

        should_log = (
            classification in ["Blocked", "Risky"] or
            ("hallucinat" in verdict.lower()) # Catches "Likely hallucinated", etc.
        )

        if not should_log:
            return  # Don't log if everything looks clean

        # Create a copy to avoid modifying the original dict passed to this method.
        log_entry = event_data.copy()
        log_entry["timestamp"] = datetime.utcnow().isoformat()

        # The original code had a line: `event_data["reason"] = event_data.get("risk_reason", "")`
        # This was removed as it could incorrectly overwrite a 'reason' field from other agents.
        # The calling context is now responsible for ensuring event_data is correct.

        try:
            # For performance, append events as JSON lines (ndjson format) instead of
            # reading/writing the whole file. This is significantly faster for large log files.
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except IOError as e:
            print(f"Error writing to audit log {self.log_file}: {e}")

# import json
# import os
# import threading
# from datetime import datetime
 
# from agents.logging import bq_logger
 
 
# class AuditChainAgent:
#     """
#     Streams high-risk or hallucinated events to BigQuery (primary) and
#     falls back to a local NDJSON file if BigQuery is unreachable.
#     """
 
#     def __init__(self, log_file: str = "logs/audit_log.json"):
#         self.log_file = log_file
#         os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
 
#     # ------------------------------------------------------------------ #
#     # Public API
#     # ------------------------------------------------------------------ #
#     def log_event(self, event_data: dict) -> None:
#         """
#         Asynchronously logs an event when either condition is true:
#         • `classification` is "Risky" or "Blocked"
#         • `verdict` contains the substring "hallucinat" (case-insensitive)
#         """
#         classification = event_data.get("classification", "Safe")
#         verdict        = (event_data.get("verdict") or "").lower()
 
#         should_log = (
#             classification in {"Risky", "Blocked"} or
#             "hallucinat" in verdict
#         )
#         if not should_log:
#             return
 
#         # Make a shallow copy so we never mutate upstream state
#         log_entry               = event_data.copy()
#         log_entry["timestamp"]  = datetime.utcnow().isoformat()
 
#         # ------------------------------------------------------------------ #
#         # Fire-and-forget so we don’t block the request path
#         # ------------------------------------------------------------------ #
#         def _bq_task(entry: dict):
#             try:
#                 bq_logger.write_event(entry)                       # primary sink
#             except Exception as bq_err:
#                 # Fallback: append to local NDJSON file
#                 try:
#                     with open(self.log_file, "a") as fh:
#                         fh.write(json.dumps(entry) + "\n")
#                 except Exception as file_err:
#                     print(
#                         f"[CRITICAL] Audit log failed – "
#                         f"BigQuery: {bq_err}; file fallback: {file_err}"
#                     )
 
#         threading.Thread(target=_bq_task, args=(log_entry,), daemon=True).start()
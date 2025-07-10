# agents/prompt_scan_agent.py


from .base_agent import BaseAgent
import json, re

class PromptScanAgent(BaseAgent):
    def __init__(self):
        super().__init__("PromptScanAgent")

    def run(self, prompt: str) -> dict:
        system_msg = (
            "You are a Prompt Risk Classifier for an AI firewall. "
            "Classify the prompt into one of: [Safe, Risky, Blocked].\n\n"
            "Definitions:\n"
            "- 'Safe': General, harmless, and non-sensitive requests.\n"
            "- 'Risky': Prompts involving code that manipulates, extracts, or decodes tokens, credentials, or sensitive data, but not overtly malicious.\n"
            "- 'Blocked': Prompts that request or facilitate hacking, credential theft, malware, or unauthorized access.\n\n"
            "If a prompt involves regex, tokens, decoding, or anything that could be used to extract or manipulate sensitive data, classify as 'Risky' or 'Blocked'.\n\n"
            "Respond as JSON with 'classification', 'reason', and 'risk_score' (0 = totally safe, 1 = extremely risky).\n\n"
            "Example Response:\n"
            "{\n  \"classification\": \"Risky\",\n  \"reason\": \"Prompt involves decoding a token, which could be sensitive.\",\n  \"risk_score\": 0.85\n}"
        )

        user_msg = (
            f"Prompt:\n{prompt}\n\n"
            "Example Response:\n"
            "{\n \"classification\": \"Risky\", \"reason\": \"Sensitive data extraction\", \"risk_score\": 0.87 }"
        )

        response = self.reason(user_msg, system_msg)
        print("LLM raw response:", response)
        return self.extract_json(response)

    def extract_json(self, response: str) -> dict:
        try:
            json_match = re.search(r"\{.*?\}", response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                parsed["risk_score"] = float(parsed.get("risk_score", 0.0))
                return parsed
        except Exception as e:
            print("⚠️ Failed to parse classification response:", e)

        # Heuristic fallback
        risky_keywords = ["token", "decode", "credential", "password", "auth"]
        if any(word in response.lower() for word in risky_keywords):
            return {
                "classification": "Risky",
                "reason": "Heuristic: contains risky keywords.",
                "risk_score": 0.8
            }
        return {
            "classification": "Safe",
            "reason": "Default fallback.",
            "risk_score": 0.0
        }




# # agents/response_verifier_agent.py

# from .base_agent import BaseAgent

# class ResponseVerifierAgent(BaseAgent):
#     def __init__(self):
#         super().__init__("ResponseVerifierAgent")

#     def run(self, prompt, response):
#         system_msg = (
#             "You are a hallucination detector AI. "
#             "Analyze the response and identify whether it is factually accurate, executable, or hallucinated. "
#             "If hallucinated, explain briefly why and suggest a fix."
#         )
#         analysis_prompt = f"User Prompt:\n{prompt}\n\nLLM Response:\n{response}\n\nAnalysis:"
#         verdict = self.reason(analysis_prompt, system_msg)
#         return verdict.strip()

# agents/response_verifier_agent.py

from .base_agent import BaseAgent

class ResponseVerifierAgent(BaseAgent):
    def __init__(self):
        super().__init__("ResponseVerifierAgent")

    def run(self, prompt: str, response: str) -> dict:
        system_msg = (
            "You are a hallucination and fact-checking agent. "
            "Analyze the LLM response to the prompt. "
            "Return a JSON with 'verdict' (one of: 'Factually correct', 'Likely hallucinated', 'Unverifiable'), "
            "and 'reason' (brief explanation)."
        )
        user_msg = (
            f"Prompt: {prompt}\n\n"
            f"LLM Response: {response}\n\n"
            "Example reply:\n"
            "{ \"verdict\": \"Likely hallucinated\", \"reason\": \"The response makes unverifiable claims about encryption keys.\" }"
        )
        result = self.reason(user_msg, system_msg)
        import json, re
        try:
            match = re.search(r"\{.*?\}", result, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception as e:
            print("ResponseVerifierAgent JSON parse error:", e)
        return {"verdict": "Unverifiable", "reason": "Could not parse LLM output."}

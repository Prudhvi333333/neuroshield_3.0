# agents/base_agent.py

from abc import ABC, abstractmethod
from llm_utils import call_llm

class BaseAgent(ABC):
    def __init__(self, name):
        self.name = name

    @abstractmethod
    def run(self, *args, **kwargs):
        pass

    def reason(self, prompt, system_msg=None):
        try:
            result = call_llm(prompt, system_msg or f"You are {self.name}. Think step by step.")
            # Optionally log the prompt and result here
            return result
        except Exception as e:
            print(f"[{self.name}] LLM call failed: {e}")
            return "LLM call failed."

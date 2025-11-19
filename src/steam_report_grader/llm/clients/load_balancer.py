# src/steam_report_grader/llm/clients/load_balancer.py
import itertools
from typing import List
from ..base import LLMClient, LLMMessage, LLMResponse

class RoundRobinLLMClient:
    def __init__(self, clients: List[LLMClient]):
        if not clients:
            raise ValueError("clients must not be empty")
        self.clients = clients
        self._cycle = itertools.cycle(self.clients)

    def chat(self, messages, temperature=0.0, max_tokens=None, response_format=None) -> LLMResponse:
        client = next(self._cycle)
        return client.chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )

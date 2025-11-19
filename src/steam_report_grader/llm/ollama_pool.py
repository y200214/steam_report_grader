# src/steam_report_grader/llm/ollama_pool.py

from __future__ import annotations
from typing import List

from .ollama_client import OllamaClient, OllamaConfig
from ..config import (
    OLLAMA_BASE_URLS,
    OLLAMA_DEFAULT_MODEL,
)

import logging

logger = logging.getLogger(__name__)


class RoundRobinLLMClient:
    """
    複数の OllamaClient をラップして、
    呼び出しのたびに順番に使う（データ並列用）
    """
    def __init__(self, clients: List[OllamaClient]):
        if not clients:
            raise ValueError("RoundRobinLLMClient requires at least one client")
        self.clients = clients
        self.index = 0

    def _next(self) -> OllamaClient:
        client = self.clients[self.index]
        self.index = (self.index + 1) % len(self.clients)
        logger.debug("Dispatching request to backend %s", client.config.base_url)
        return client

    # AbsoluteScorer などから見える interface は元の OllamaClient と同じにする
    def generate(self, *args, **kwargs):
        return self._next().generate(*args, **kwargs)

    def chat(self, *args, **kwargs):
        return self._next().chat(*args, **kwargs)


# グローバルなプール（scoring_pipeline などから使う）
_llm_client_pool: RoundRobinLLMClient | None = None


def get_ollama_client() -> RoundRobinLLMClient:
    """
    スコアリングなどで使う LLM クライアント。
    OLLAMA_BASE_URLS に書かれたサーバをラウンドロビンで使う。
    """
    global _llm_client_pool
    if _llm_client_pool is None:
        clients: List[OllamaClient] = []
        for base_url in OLLAMA_BASE_URLS:
            cfg = OllamaConfig(
                model=OLLAMA_DEFAULT_MODEL,
                base_url=base_url,
            )
            logger.info("Register Ollama backend: %s (model=%s)", base_url, cfg.model)
            clients.append(OllamaClient(cfg))

        _llm_client_pool = RoundRobinLLMClient(clients)

    return _llm_client_pool

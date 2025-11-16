# src/steam_report_grader/llm/ollama_client.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional
import logging
import time

import requests

logger = logging.getLogger(__name__)


@dataclass
class OllamaConfig:
    base_url: str = "http://127.0.0.1:11434"
    model: str = "gpt-oss:20b"  # ← コロン付きにしておく
    timeout: int = 120
    max_retries: int = 3
    retry_delay: float = 2.0  # seconds


class OllamaClient:
    def __init__(self, config: Optional[OllamaConfig] = None) -> None:
        self.config = config or OllamaConfig()

    def generate(self, prompt: str) -> str:
        """
        Ollama の /api/generate を叩いてテキストを生成する。
        """
        url = f"{self.config.base_url}/api/generate"
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
        }

        for attempt in range(1, self.config.max_retries + 1):
            try:
                resp = requests.post(url, json=payload, timeout=self.config.timeout)
                resp.raise_for_status()
                data = resp.json()
                text = data.get("response", "")
                return text.strip()
            except Exception as e:
                logger.warning(
                    "Ollama /api/generate failed (attempt %d/%d): %s",
                    attempt,
                    self.config.max_retries,
                    e,
                )
                if attempt == self.config.max_retries:
                    logger.error("Max retries for /api/generate reached. Giving up.")
                    raise
                time.sleep(self.config.retry_delay)

# src/steam_report_grader/llm/ollama_client.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import logging
import time

import requests

from .base import LLMClient
from ..config import (
    OLLAMA_DEFAULT_BASE_URL,
    OLLAMA_DEFAULT_MODEL,
    OLLAMA_DEFAULT_TIMEOUT,
    OLLAMA_DEFAULT_MAX_RETRIES,
    OLLAMA_DEFAULT_RETRY_DELAY,
    OLLAMA_DEFAULT_TEMPERATURE,
    OLLAMA_DEFAULT_TOP_P,
    OLLAMA_DEFAULT_SEED,
)

logger = logging.getLogger(__name__)


@dataclass
class OllamaConfig:
    base_url: str = OLLAMA_DEFAULT_BASE_URL
    model: str = OLLAMA_DEFAULT_MODEL
    timeout: int = OLLAMA_DEFAULT_TIMEOUT
    max_retries: int = OLLAMA_DEFAULT_MAX_RETRIES
    retry_delay: float = OLLAMA_DEFAULT_RETRY_DELAY  # seconds
    temperature: float = OLLAMA_DEFAULT_TEMPERATURE
    top_p: float = OLLAMA_DEFAULT_TOP_P
    seed: Optional[int] = OLLAMA_DEFAULT_SEED



class OllamaClient(LLMClient):
    """
    Ollama /api/generate を叩くクライアント。
    """

    def __init__(self, config: OllamaConfig) -> None:
        self.config = config

    def _build_payload(
        self,
        prompt: str,
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        temp = temperature if temperature is not None else self.config.temperature

        payload: Dict[str, Any] = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "temperature": temp,
            "options": {
                "seed": self.config.seed,
            },
        }

        if max_tokens is not None:
            # Ollama の num_predict に流す
            payload["options"]["num_predict"] = max_tokens

        # 追加 options があればマージ
        extra_options = kwargs.get("options")
        if isinstance(extra_options, dict):
            payload["options"].update(extra_options)

        return payload

    def generate(
        self,
        prompt: str,
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """
        LLMClient.generate の実装。
        """
        url = f"{self.config.base_url.rstrip('/')}/api/generate"
        payload = self._build_payload(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        last_exc: Optional[Exception] = None

        for attempt in range(1, self.config.max_retries + 1):
            try:
                logger.debug(
                    "Calling Ollama /api/generate (attempt %d): %s",
                    attempt,
                    payload,
                )
                resp = requests.post(
                    url,
                    json=payload,
                    timeout=self.config.timeout,
                )
                resp.raise_for_status()

                data = resp.json()
                text = data.get("response", "")

                if not isinstance(text, str):
                    logger.warning("Unexpected response type from Ollama: %r", data)
                    text = str(text)

                return text.strip()

            except Exception as e:
                last_exc = e
                logger.warning(
                    "Ollama /api/generate failed (attempt %d/%d): %s",
                    attempt,
                    self.config.max_retries,
                    e,
                )

                if attempt == self.config.max_retries:
                    break

                time.sleep(self.config.retry_delay)

        logger.error("Max retries for Ollama /api/generate reached. Giving up.")
        if last_exc:
            raise last_exc
        raise RuntimeError("Ollama /api/generate failed for unknown reasons")


__all__ = ["OllamaConfig", "OllamaClient"]

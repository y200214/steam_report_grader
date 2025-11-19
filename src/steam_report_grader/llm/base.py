# src/steam_report_grader/llm/base.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class LLMConfig:
    provider: str           # "ollama", "openai", "http"
    model: str
    base_url: str | None = None
    api_key: str | None = None
    timeout: int = 60
    extra: Dict[str, Any] | None = None  # provider固有のパラメータを入れる

@dataclass
class LLMMessage:
    role: str   # "system" | "user" | "assistant"
    content: str

@dataclass
class LLMResponse:
    content: str
    raw: Any | None = None  # デバッグ用に生レスポンス持っておく

class LLMClient(Protocol):
    def chat(
        self,
        messages: List[LLMMessage],
        *,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,  # "json"とか
    ) -> LLMResponse:
        ...

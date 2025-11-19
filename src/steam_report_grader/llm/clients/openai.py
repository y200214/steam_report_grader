# src/steam_report_grader/llm/clients/openai.py
import requests
from ..base import LLMClient, LLMConfig, LLMMessage, LLMResponse


class OpenAIClient:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.base_url = (cfg.base_url or "https://api.openai.com/v1").rstrip("/")
        if not cfg.api_key:
            raise ValueError("OpenAIClient requires api_key")

    def chat(self, messages, temperature=0.0, max_tokens=None, response_format=None):
        headers = {
            "Authorization": f"Bearer {self.cfg.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.cfg.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        resp = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=headers, timeout=self.cfg.timeout)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return LLMResponse(content=content, raw=data)

# src/steam_report_grader/llm/clients/ollama.py
import requests
from ..base import LLMClient, LLMConfig, LLMMessage, LLMResponse
from steam_report_grader.config import OLLAMA_DEFAULT_BASE_URL


class OllamaClient:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.base_url = cfg.base_url.rstrip("/") if cfg.base_url else OLLAMA_DEFAULT_BASE_URL

    def chat(self, messages, temperature=0.0, max_tokens=None, response_format=None):
        payload = {
            "model": self.cfg.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "options": {
                "temperature": temperature,
            },
            "stream": False,
        }
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens

        # ollama独自でjson modeあるならここでoptionsに追加

        resp = requests.post(f"{self.base_url}/v1/chat/completions", json=payload, timeout=self.cfg.timeout)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return LLMResponse(content=content, raw=data)

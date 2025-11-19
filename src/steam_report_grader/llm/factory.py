# src/steam_report_grader/llm/factory.py
from __future__ import annotations

import os
from typing import List

from ..config import (
    LLM_PROFILES,
    OLLAMA_INSTANCES,
    OLLAMA_DEFAULT_BASE_URL,  # config にある前提
)
from .base import LLMConfig
from .clients.ollama import OllamaClient
from .clients.openai import OpenAIClient
from .clients.load_balancer import RoundRobinLLMClient


def _create_ollama_client(model: str, base_url: str | None = None) -> OllamaClient:
    """
    単体の OllamaClient を組み立てるヘルパ。
    base_url が None のときは OLLAMA_DEFAULT_BASE_URL を使う。
    """
    cfg = LLMConfig(
        provider="ollama",
        model=model,
        base_url=(base_url or OLLAMA_DEFAULT_BASE_URL),
    )
    return OllamaClient(cfg)


def _create_ollama_lb_clients(model: str, profile: dict) -> RoundRobinLLMClient:
    """
    2枚GPUなど、複数の Ollama インスタンスをまとめて
    RoundRobinLLMClient に包むためのヘルパ。
    優先順：
      1. profile["base_urls"] があればそれを使用
      2. global の OLLAMA_INSTANCES があればそれを使用
      3. 何もなければ OLLAMA_DEFAULT_BASE_URL だけを使う
    """
    # 役割プロファイル側に base_urls が書かれている場合
    urls: List[str] = profile.get("base_urls") or []

    # なければグローバル設定を使う
    if not urls and OLLAMA_INSTANCES:
        urls = list(OLLAMA_INSTANCES)

    # それでも空ならデフォルト1個
    if not urls:
        urls = [OLLAMA_DEFAULT_BASE_URL]

    backends = [_create_ollama_client(model=model, base_url=url) for url in urls]
    return RoundRobinLLMClient(backends)


def _create_openai_client(model: str, profile: dict) -> OpenAIClient:
    """
    OpenAI API 用クライアントを作るヘルパ。
    api_key は profile["api_key"] または profile["api_key_env"] の環境変数から取得。
    """
    base_url = profile.get("base_url") or "https://api.openai.com/v1"
    api_key = profile.get("api_key")

    api_key_env = profile.get("api_key_env")
    if api_key_env and not api_key:
        api_key = os.getenv(api_key_env)

    if not api_key:
        raise ValueError("OpenAI provider requires api_key or api_key_env in LLM_PROFILES")

    cfg = LLMConfig(
        provider="openai",
        model=model,
        base_url=base_url,
        api_key=api_key,
    )
    return OpenAIClient(cfg)


def create_llm_client(role: str = "scoring"):
    """
    役割名 (role) に応じて、適切な LLM クライアントを返すファクトリ。

    想定する LLM_PROFILES の例:

    LLM_PROFILES = {
        "scoring": {
            "provider": "ollama_lb",     # "ollama" / "ollama_lb" / "openai" など
            "model": "gpt-oss:20b",
            # "base_url": "...",         # 単体 ollama の場合
            # "base_urls": ["http://127.0.0.1:11434", "http://127.0.0.1:11435"],  # LB の場合
        },
        "translation": {
            "provider": "ollama",
            "model": "qwen3:8b",
        },
        ...
    }
    """
    if role not in LLM_PROFILES:
        raise KeyError(f"Unknown LLM role: {role}")

    profile = LLM_PROFILES[role]
    provider = profile["provider"]
    model = profile["model"]

    # 単体 Ollama
    if provider == "ollama":
        return _create_ollama_client(model=model, base_url=profile.get("base_url"))

    # 複数 Ollama をまとめてラウンドロビン
    if provider == "ollama_lb":
        return _create_ollama_lb_clients(model=model, profile=profile)

    # OpenAI API など外部プロバイダ
    if provider == "openai":
        return _create_openai_client(model=model, profile=profile)

    raise ValueError(f"Unknown LLM provider: {provider}")

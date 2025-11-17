# src/steam_report_grader/llm/factory.py
from .ollama_client import OllamaClient, OllamaConfig
from ..grading.absolute_scorer import AbsoluteScorer

def create_default_scorer() -> AbsoluteScorer:
    cfg = OllamaConfig(
        model="gpt-oss:20b",
        temperature=0.0,
        seed=42,
    )
    return AbsoluteScorer(OllamaClient(cfg))

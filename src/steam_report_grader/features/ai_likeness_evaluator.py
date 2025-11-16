# src/steam_report_grader/features/ai_likeness_evaluator.py
from __future__ import annotations
from typing import List, Dict
import json
import logging

from ..llm.ollama_client import OllamaClient, OllamaConfig
from ..llm.prompts import build_final_evaluation_prompt

logger = logging.getLogger(__name__)

class AILikenessEvaluator:
    def __init__(self, client: OllamaClient) -> None:
        self.client = client

    def evaluate_likeness(
        self,
        student_id: str,
        question: str,
        ai_sim_score: float,
        peer_sim_score: float,
        symbolic_score: float,
        answer_text: str,
    ) -> Dict[str, float]:
        """
        LLM に最終評価をさせ、AIらしさスコアを決定する。
        """
        # LLMに渡すためのプロンプトを生成
        prompt = build_final_evaluation_prompt(
            student_id=student_id,
            question=question,
            ai_sim_score=ai_sim_score,
            peer_sim_score=peer_sim_score,
            symbolic_score=symbolic_score,
            answer_text=answer_text,
        )

        try:
            llm_response = self.client.generate(prompt)
            parsed = self._safe_parse_json(llm_response)

            ai_likeness_score = float(parsed.get("ai_likeness_score", 0.0))
            ai_likeness_comment = str(parsed.get("ai_likeness_comment", ""))
            return {
                "ai_likeness_score": ai_likeness_score,
                "ai_likeness_comment": ai_likeness_comment,
            }
        except Exception as e:
            logger.warning("Error evaluating Likeness for %s: %s", student_id, e)
            return {
                "ai_likeness_score": 0.0,
                "ai_likeness_comment": "評価失敗",
            }

    def _safe_parse_json(self, text: str) -> Dict[str, any]:
        """
        受け取ったLLMの出力をJSONとしてパースする。
        - ```json ... ``` みたいなコードブロックも許容
        - 余計な前後テキストがあっても { ... } 部分だけ抜き出す
        """
        if not text:
            return {}

        raw = text.strip()

        # ```json ... ``` / ``` ... ``` を剥がす
        if raw.startswith("```"):
            # 1行目の ```xxx を削る
            lines = raw.splitlines()
            # 先頭の ```xxx は捨てる
            if len(lines) >= 2:
                # 末尾の ``` も削る
                if lines[-1].strip().startswith("```"):
                    lines = lines[1:-1]
                else:
                    lines = lines[1:]
                raw = "\n".join(lines).strip()

        # { ... } の範囲だけ抜き出す
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and start < end:
            json_str = raw[start : end + 1]
        else:
            json_str = raw

        try:
            return json.loads(json_str)
        except Exception as e:
            logger.warning(
                "Failed to parse JSON from LLM response after trimming: %s | raw head=%r",
                e,
                raw[:120],
            )
            return {}

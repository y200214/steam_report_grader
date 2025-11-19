# src/steam_report_grader/grading/absolute_scorer.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
import ast
import logging

from ..llm.base import LLMClient
from ..llm.prompts import build_scoring_prompt

from .rubric import QuestionRubric
from ..config import LLM_SCORING_MAX_TOKENS
logger = logging.getLogger(__name__)


@dataclass
class ScoreResult:
    student_id: str
    question_label: str
    score: float
    summary_bullets: List[str]
    detailed_explanation: str
    subscores: Dict[str, float]
    evidence: List[Dict[str, str]]
    raw_response: str


class AbsoluteScorer:
    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def score_answer(
        self,
        student_id: str,
        question_rubric: QuestionRubric,
        answer_text: str,
    ) -> ScoreResult:
        prompt = build_scoring_prompt(
            question_label=question_rubric.question_label,
            question_text=question_rubric.question_text,
            rubric_text=question_rubric.rubric_text,
            answer_text=answer_text,
            max_score=question_rubric.max_score,
        )

        llm_text = self.client.generate(
            prompt,
            max_tokens=LLM_SCORING_MAX_TOKENS,
        )
        logger.debug(
            "LLM raw response for %s %s: %s",
            student_id, question_rubric.question_label, llm_text
        )

        # LLM が変なものを返しても落ちないように、パースをがんばる
        parsed = self._safe_parse_json(llm_text)

        raw_score = parsed.get("score", 0.0)
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            logger.warning("Invalid score value from LLM: %r", raw_score)
            score = 0.0

        subscores = parsed.get("subscores", {}) or {}
        if not isinstance(subscores, dict):
            subscores = {}

        summary_bullets = parsed.get("summary_bullets", []) or []
        if not isinstance(summary_bullets, list):
            summary_bullets = [str(summary_bullets)]

        summary_bullets = [str(x) for x in summary_bullets]

        detailed_explanation = parsed.get("detailed_explanation", "") or ""
        if not isinstance(detailed_explanation, str):
            detailed_explanation = str(detailed_explanation)

        raw_evidence = parsed.get("evidence", []) or []
        if not isinstance(raw_evidence, list):
            raw_evidence = []

        evidence_list: List[Dict[str, str]] = []
        for ev in raw_evidence:
            if not isinstance(ev, dict):
                continue
            aspect = str(ev.get("aspect", "") or "")
            quote = str(ev.get("quote", "") or "")
            if not quote:
                continue
            evidence_list.append({"aspect": aspect, "quote": quote})

        return ScoreResult(
            student_id=student_id,
            question_label=question_rubric.question_label,
            score=score,
            summary_bullets=summary_bullets,
            detailed_explanation=detailed_explanation,
            subscores=subscores,
            evidence=evidence_list,
            raw_response=llm_text,
        )

    def _safe_parse_json(self, text: str) -> Dict[str, Any]:
        """
        LLM の出力から、できるだけ安全に dict を取り出す。
        - 最初の { 〜 最後の } までを抜き出す
        - ast.literal_eval で Python リテラルとして解釈（JSONより寛容）
        - それでもダメなら {} を返す
        """
        if not text:
            return {}

        text = text.strip()

        # { .. } の最外郭を探す
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and start < end:
            snippet = text[start : end + 1]
        else:
            snippet = text

        try:
            return ast.literal_eval(snippet)
        except Exception as e1:
            logger.warning("literal_eval failed once: %s", e1)

            # 全角引用符などを軽く置換して再トライ
            fixed = (
                snippet.replace("“", '"')
                       .replace("”", '"')
                       .replace("’", "'")
            )

            try:
                return ast.literal_eval(fixed)
            except Exception as e2:
                logger.warning("Failed to parse JSON-like text. Giving up. %s", e2)
                logger.debug("LLM response snippet (failed): %s", snippet)
                return {}

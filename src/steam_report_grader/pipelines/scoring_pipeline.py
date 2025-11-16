# src/steam_report_grader/pipelines/scoring_pipeline.py
from __future__ import annotations
from pathlib import Path
import logging
from typing import List, Dict, Any

import pandas as pd
import json 

from ..utils.logging_utils import setup_logging
from ..utils.progress import simple_progress
from ..llm.ollama_client import OllamaClient, OllamaConfig
from ..grading.rubric import load_all_rubrics
from ..grading.absolute_scorer import AbsoluteScorer, ScoreResult

logger = logging.getLogger(__name__)


def run_scoring(
    responses_excel_path: Path,
    rubric_dir: Path,
    output_path: Path,
    log_path: Path,
    model_name: str = "gpt-oss-20b",
) -> None:
    """
    匿名化された回答 Excel を読み込み、Q1〜Q5 を絶対評価。
    結果を CSV で保存する。
    """
    setup_logging(log_path)
    logger.info("Start scoring pipeline")

    responses_excel_path = Path(responses_excel_path)
    rubric_dir = Path(rubric_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(responses_excel_path, sheet_name="responses")
    logger.info("Loaded responses from %s (rows=%d)", responses_excel_path, len(df))

    questions = [col for col in df.columns if col.startswith("Q")]
    questions = sorted(questions, key=lambda x: int(x[1:]))  # "Q1" -> 1
    logger.info("Detected questions: %s", questions)

    rubrics = load_all_rubrics(rubric_dir, questions)

    client = OllamaClient(OllamaConfig(model=model_name))
    scorer = AbsoluteScorer(client)

    results: List[ScoreResult] = []

    for _, row in simple_progress(df.iterrows(), total=len(df), prefix="Scoring students: "):
        student_id = str(row["student_id"])
        for q_label in questions:
            answer = str(row.get(q_label, "") or "").strip()
            if not answer:
                logger.warning("Empty answer: %s %s", student_id, q_label)
                continue

            rubric = rubrics[q_label]
            try:
                res = scorer.score_answer(student_id, rubric, answer)
                results.append(res)
            except Exception as e:
                logger.exception("Failed to score %s %s: %s", student_id, q_label, e)

    # 結果を DataFrame に変換
    rows: List[Dict[str, Any]] = []
    for r in results:
        # ざっくりした「reason」としては detailed_explanation を優先し、
        # なければ summary_bullets をつなげる
        if r.detailed_explanation:
            reason_text = r.detailed_explanation
        elif r.summary_bullets:
            reason_text = " / ".join(r.summary_bullets)
        else:
            reason_text = ""

        base: Dict[str, Any] = {
            "student_id": r.student_id,
            "question": r.question_label,
            "score": r.score,
            "reason": reason_text,
            "summary_bullets": " • ".join(r.summary_bullets) if r.summary_bullets else "",
            "detailed_explanation": r.detailed_explanation,
            # evidence はそのままだと list[dict] なので JSON 文字列にして突っ込む
            "evidence": json.dumps(r.evidence, ensure_ascii=False),
            "raw_response": r.raw_response,
        }

        # subscores をフラットに展開
        for k, v in r.subscores.items():
            col = f"sub_{k}"
            base[col] = v

        rows.append(base)

    if not rows:
        logger.warning("No scores generated. Check logs.")
        return

    out_df = pd.DataFrame(rows)
    out_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info("Wrote scores to %s", output_path)

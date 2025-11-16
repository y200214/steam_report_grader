# src/steam_report_grader/pipelines/symbolic_features_pipeline.py
from __future__ import annotations
from pathlib import Path
import logging

from ..utils.logging_utils import setup_logging
from ..features.symbolic_features import calculate_symbolic_features
import pandas as pd

logger = logging.getLogger(__name__)


def run_symbolic_features(
    responses_excel: Path,
    output_csv: Path,
    log_path: Path,
) -> None:
    """
    匿名回答Excelから、記号的特徴量（太字頻度、見出し、箇条書き、接続詞）を計算し、
    出力するCSVを作成する。
    """
    setup_logging(log_path)
    logger.info("Start symbolic features pipeline")

    responses_excel = Path(responses_excel)
    output_csv = Path(output_csv)
    responses_df = pd.read_excel(responses_excel, sheet_name="responses")
    logger.info("Loaded responses for symbolic feature extraction: %d rows", len(responses_df))

    result_rows = []

    # Q1〜Q5を順に処理
    questions = [col for col in responses_df.columns if col.startswith("Q")]

    for _, row in responses_df.iterrows():
        student_id = str(row["student_id"])

        for q in questions:
            answer = str(row.get(q, "") or "").strip()

            if not answer:
                continue

            symbolic_score = calculate_symbolic_features(answer)

            result_rows.append(
                {
                    "student_id": student_id,
                    "question": q,
                    "symbolic_ai_score": symbolic_score,
                    "answer": answer,
                }
            )

    result_df = pd.DataFrame(result_rows)
    result_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    logger.info("Wrote symbolic features to %s (rows=%d)", output_csv, len(result_df))

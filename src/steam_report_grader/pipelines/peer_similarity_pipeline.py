# src/steam_report_grader/pipelines/peer_similarity_pipeline.py
from __future__ import annotations
from pathlib import Path
import logging

from ..utils.logging_utils import setup_logging
from ..features.peer_similarity import compute_peer_similarity_for_responses

logger = logging.getLogger(__name__)


def run_peer_similarity(
    responses_excel: Path,
    per_student_output_csv: Path,
    pair_output_csv: Path,
    log_path: Path,
) -> None:
    """
    匿名回答Excelから受験者同士の類似度を計算し、2つのCSVを出力する。
    """
    setup_logging(log_path)
    logger.info("Start peer similarity pipeline")

    per_student_df, pair_df = compute_peer_similarity_for_responses(responses_excel)

    per_student_output_csv = Path(per_student_output_csv)
    pair_output_csv = Path(pair_output_csv)
    per_student_output_csv.parent.mkdir(parents=True, exist_ok=True)
    pair_output_csv.parent.mkdir(parents=True, exist_ok=True)

    per_student_df.to_csv(per_student_output_csv, index=False, encoding="utf-8-sig")
    logger.info(
        "Wrote peer similarity (per student) to %s (rows=%d)",
        per_student_output_csv,
        len(per_student_df),
    )

    pair_df.to_csv(pair_output_csv, index=False, encoding="utf-8-sig")
    logger.info(
        "Wrote peer similarity (pairs) to %s (rows=%d)",
        pair_output_csv,
        len(pair_df),
    )

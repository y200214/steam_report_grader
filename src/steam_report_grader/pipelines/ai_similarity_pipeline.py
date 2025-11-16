# src/steam_report_grader/pipelines/ai_similarity_pipeline.py
from __future__ import annotations
from pathlib import Path
import logging

from ..utils.logging_utils import setup_logging
from ..features.ai_similarity import compute_ai_similarity_for_responses

logger = logging.getLogger(__name__)


def run_ai_similarity(
    responses_excel: Path,
    ai_reference_dir: Path,
    output_csv: Path,
    log_path: Path,
) -> None:
    """
    匿名回答Excel ＋ AI模範解答 をもとに、
    各 student_id × question の AI類似度を CSV で出力する。
    """
    setup_logging(log_path)
    logger.info("Start AI similarity pipeline")

    df = compute_ai_similarity_for_responses(
        responses_excel_path=responses_excel,
        ai_reference_dir=ai_reference_dir,
    )

    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    logger.info("Wrote AI similarity features to %s (rows=%d)", output_csv, len(df))

# src/steam_report_grader/pipelines/ai_report_pipeline.py
from __future__ import annotations
from pathlib import Path
import logging

import pandas as pd

from ..utils.logging_utils import setup_logging
from ..features.feature_aggregator import load_full_features
from ..io.excel_writer import write_ai_suspect_report_excel

logger = logging.getLogger(__name__)


def run_ai_report(
    responses_excel: Path,
    ai_similarity_csv: Path,
    peer_similarity_csv: Path,
    symbolic_features_csv: Path,
    ai_likeness_csv: Path,
    output_excel: Path,
    log_path: Path,
) -> None:
    """
    各特徴量をマージし、AI疑惑レポートExcelを出力する。
    """
    setup_logging(log_path)
    logger.info("Start AI report pipeline")

    full_df = load_full_features(
        responses_excel=responses_excel,
        ai_similarity_csv=ai_similarity_csv,
        peer_similarity_csv=peer_similarity_csv,
        symbolic_features_csv=symbolic_features_csv,
        ai_likeness_csv=ai_likeness_csv,
    )

    write_ai_suspect_report_excel(
        path=output_excel,
        full_features_df=full_df,
    )

    logger.info(
        "Wrote AI suspect report to %s (rows=%d)",
        output_excel,
        len(full_df),
    )

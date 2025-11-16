# src/steam_report_grader/pipelines/summary_pipeline.py
from __future__ import annotations
from pathlib import Path
import logging

from ..utils.logging_utils import setup_logging
from ..features.aggregate_scores import (
    load_absolute_scores,
    aggregate_per_student,
    attach_real_names,
)
from ..io.excel_writer import write_scores_summary_excel

logger = logging.getLogger(__name__)


def run_summary(
    absolute_scores_csv: Path,
    id_map_excel: Path,
    output_excel: Path,
    log_path: Path,
) -> None:
    """
    absolute_scores.csv -> absolute_scores_summary.xlsx を作る。
    """
    setup_logging(log_path)
    logger.info("Start summary pipeline")

    scores_df = load_absolute_scores(absolute_scores_csv)
    logger.info("Loaded absolute scores: %d rows", len(scores_df))

    summary_df = aggregate_per_student(scores_df)
    logger.info("Aggregated to %d students", len(summary_df))

    summary_with_names_df = attach_real_names(summary_df, id_map_excel)

    write_scores_summary_excel(
        path=output_excel,
        summary_with_names_df=summary_with_names_df,
        raw_scores_df=scores_df,
    )

    logger.info("Wrote summary excel to %s", output_excel)

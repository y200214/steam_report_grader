# src/steam_report_grader/pipelines/explanations_pipeline.py
from __future__ import annotations
from pathlib import Path
import logging
import pandas as pd

from ..utils.logging_utils import setup_logging
from ..io.excel_writer import write_score_explanations_excel

logger = logging.getLogger(__name__)


def run_explanations(
    absolute_scores_csv: Path,
    id_map_excel: Path,
    output_excel: Path,
    log_path: Path,
) -> None:
    setup_logging(log_path)
    logger.info("Start explanations pipeline")

    scores_df = pd.read_csv(absolute_scores_csv)
    id_df = pd.read_excel(id_map_excel, sheet_name="id_map")

    merged = scores_df.merge(id_df, on="student_id", how="left")

    # brief 用ビュー
    brief_cols = [
        "student_id", "real_name", "source_file",
        "question", "score", "brief"
    ]
    # evidence はまとめて1列に
    def combine_evidence(row):
        parts = []
        for i in range(1, 4):
            q = row.get(f"evidence_{i}_quote")
            a = row.get(f"evidence_{i}_aspect")
            if isinstance(q, str) and q.strip():
                if isinstance(a, str) and a.strip():
                    parts.append(f"[{a}]「{q}」")
                else:
                    parts.append(f"「{q}」")
        return "\n".join(parts)

    merged["key_evidence"] = merged.apply(combine_evidence, axis=1)
    brief_cols.append("key_evidence")
    brief_df = merged[brief_cols]

    # detailed 用ビュー
    detailed_cols = [
        "student_id", "real_name", "source_file",
        "question", "score", "detailed"
    ]
    # evidence 列も付けたいならここで追加
    detailed_df = merged[detailed_cols]

    write_score_explanations_excel(
        output_excel,
        brief_df=brief_df,
        detailed_df=detailed_df,
    )

    logger.info("Wrote explanations excel to %s", output_excel)

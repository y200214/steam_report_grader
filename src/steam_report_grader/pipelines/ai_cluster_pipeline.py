# src/steam_report_grader/pipelines/ai_cluster_pipeline.py
from __future__ import annotations
from pathlib import Path
import logging
from typing import List, Dict

import pandas as pd

from ..utils.logging_utils import setup_logging
from ..features.text_clustering import cluster_answers_for_question
from ..features.ai_cluster_eval import analyze_clusters_with_llm
from ..io.excel_writer import write_ai_cluster_report_excel

logger = logging.getLogger(__name__)


def run_ai_cluster(
    responses_excel: Path,
    rubric_dir: Path | None,
    output_excel: Path,
    log_path: Path,
    model_name: str = "gpt-oss-20b",
) -> None:
    """
    匿名回答Excelから、設問ごとにクラスタリングを行い、
    各クラスタの「AIテンプレ度」を評価してレポートを出力する。
    """
    setup_logging(log_path)
    logger.info("Start AI cluster pipeline")

    responses_excel = Path(responses_excel)
    output_excel = Path(output_excel)
    rubric_dir = Path(rubric_dir) if rubric_dir is not None else None

    df = pd.read_excel(responses_excel, sheet_name="responses")
    logger.info("Loaded responses: %d rows", len(df))

    questions = [c for c in df.columns if c.startswith("Q")]
    questions = sorted(questions, key=lambda x: int(x[1:]))

    cluster_rows: List[Dict] = []

    for q in questions:
        sub = df[["student_id", q]].copy()
        sub = sub.rename(columns={q: "answer"})

        results = cluster_answers_for_question(q, sub)
        for r in results:
            cluster_rows.append(
                {
                    "student_id": r.student_id,
                    "question": r.question,
                    "cluster_id": r.cluster_id,
                }
            )

    if not cluster_rows:
        logger.warning("No clusters generated.")
        return

    cluster_df = pd.DataFrame(cluster_rows)

    # クラスターごとの要約 & AIテンプレ度評価
    analyses = analyze_clusters_with_llm(
        responses_df=df,
        cluster_df=cluster_df,
        rubric_dir=str(rubric_dir) if rubric_dir else None,
        model_name=model_name,
    )

    if not analyses:
        logger.warning("No cluster analyses generated.")
        return

    analysis_rows: List[Dict] = []
    for a in analyses:
        analysis_rows.append(
            {
                "question": a.question,
                "cluster_id": a.cluster_id,
                "ai_template_likeness": a.ai_template_likeness,
                "summary": a.summary,
                "comment": a.comment,
                "raw_response": a.raw_response,
            }
        )

    cluster_analysis_df = pd.DataFrame(analysis_rows)

    write_ai_cluster_report_excel(
        path=output_excel,
        per_student_clusters_df=cluster_df,
        cluster_analysis_df=cluster_analysis_df,
    )

    logger.info("Wrote AI cluster report to %s", output_excel)

    # cluster_df と cluster_analysis_df を中間特徴として保存
    features_dir = Path("data/intermediate/features")
    features_dir.mkdir(parents=True, exist_ok=True)

    cluster_df.to_csv(
        features_dir / "ai_clusters_per_student.csv",
        index=False,
        encoding="utf-8-sig",
    )

    cluster_analysis_df.to_csv(
        features_dir / "ai_clusters_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
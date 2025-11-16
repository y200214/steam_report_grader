# src/steam_report_grader/features/aggregate_scores.py
from __future__ import annotations
from pathlib import Path
from typing import Tuple

import pandas as pd


def load_absolute_scores(path: Path) -> pd.DataFrame:
    path = Path(path)
    return pd.read_csv(path)


def aggregate_per_student(
    scores_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    absolute_scores.csv (縦持ち) -> 受験者ごとの横持ち DataFrame に変換する。
    想定カラム:
      - student_id
      - question (Q1, Q2, ...)
      - score
    """
    # 必要な列だけ取り出す
    df = scores_df[["student_id", "question", "score"]].copy()

    # ピボット: 行=student_id, 列=question, 値=score
    pivot = df.pivot_table(
        index="student_id",
        columns="question",
        values="score",
        aggfunc="mean",  # 念のため、同じ問が複数行あっても平均
    )

    # カラム名をフラットに
    pivot = pivot.reset_index()
    pivot.columns.name = None  # "question" を消す

    # total, mean を追加
    score_cols = [c for c in pivot.columns if c.startswith("Q")]
    pivot["total"] = pivot[score_cols].sum(axis=1)
    pivot["mean"] = pivot[score_cols].mean(axis=1)

    return pivot


def attach_real_names(
    summary_df: pd.DataFrame,
    id_map_excel_path: Path,
) -> pd.DataFrame:
    """
    steam_exam_id_map.xlsx と結合して real_name を付与する。
    """
    id_map_path = Path(id_map_excel_path)
    id_df = pd.read_excel(id_map_path, sheet_name="id_map")

    merged = summary_df.merge(id_df, on="student_id", how="left")

    # 列の並びを整理
    cols = ["student_id", "real_name", "source_file"]
    score_cols = [c for c in merged.columns if c.startswith("Q")]
    others = [c for c in merged.columns if c not in cols + score_cols]
    ordered_cols = cols + score_cols + others

    return merged[ordered_cols]

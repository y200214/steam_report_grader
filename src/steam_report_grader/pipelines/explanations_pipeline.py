# src/steam_report_grader/pipelines/explanations_pipeline.py
from __future__ import annotations

from pathlib import Path
import logging
import json  # ← 追加
import pandas as pd

from ..utils.logging_utils import setup_logging
from ..io.excel_writer import write_score_explanations_excel

logger = logging.getLogger(__name__)


def _normalize_explanation_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    スコアCSV側の列名ゆれをここで吸収する。

    正式カラム:
      - brief   : 簡易講評
      - detailed: 詳細講評

    レガシー互換:
      - reason, brief_explanation, detailed_explanation など
    """

    # --- brief を正とする ---
    if "brief" not in df.columns:
        if "brief_explanation" in df.columns:
            df["brief"] = df["brief_explanation"]
        elif "reason" in df.columns:
            df["brief"] = df["reason"]
        else:
            df["brief"] = ""

    # --- detailed を正とする ---
    if "detailed" not in df.columns:
        if "detailed_explanation" in df.columns:
            df["detailed"] = df["detailed_explanation"]
        else:
            df["detailed"] = ""

    return df



def _explode_evidence_columns(df: pd.DataFrame, max_items: int = 3) -> pd.DataFrame:
    """
    scores_df の 'evidence' 列(JSON文字列 or list[dict]) を
    evidence_1_quote / evidence_1_aspect / evidence_1_reason ... に展開する。

    すでに evidence_1_quote が存在する場合は何もしない。
    """
    if "evidence" not in df.columns:
        return df

    # 既に展開済みならそのまま使う
    if "evidence_1_quote" in df.columns:
        return df

    def parse_cell(cell):
        if cell is None or (isinstance(cell, float) and pd.isna(cell)):
            return []
        if isinstance(cell, list):
            return cell
        if isinstance(cell, str):
            try:
                return json.loads(cell)
            except Exception:
                return []
        return []

    parsed = df["evidence"].apply(parse_cell)

    for i in range(max_items):
        idx = i  # 0-based index

        def get_field(lst, key):
            if len(lst) > idx and isinstance(lst[idx], dict):
                return lst[idx].get(key, "") or ""
            return ""

        df[f"evidence_{i+1}_quote"] = parsed.apply(lambda lst: get_field(lst, "quote"))
        df[f"evidence_{i+1}_aspect"] = parsed.apply(lambda lst: get_field(lst, "aspect"))
        df[f"evidence_{i+1}_reason"] = parsed.apply(lambda lst: get_field(lst, "reason"))

    return df


def run_explanations(
    absolute_scores_csv: Path,
    id_map_excel: Path,
    output_excel: Path,
    log_path: Path,
) -> None:
    setup_logging(log_path)
    logger.info("Start explanations pipeline")

    # スコアCSV & IDマップ読み込み
    scores_df = pd.read_csv(absolute_scores_csv)
    id_df = pd.read_excel(id_map_excel, sheet_name="id_map")

    # 列名ゆれをここで吸収
    scores_df = _normalize_explanation_columns(scores_df)
    # evidence(JSON) → evidence_1_* などに展開
    scores_df = _explode_evidence_columns(scores_df, max_items=3)

    # student_id で名前などを結合
    merged = scores_df.merge(id_df, on="student_id", how="left")

    # -------- brief 用ビュー --------
    brief_cols = [
        "student_id",
        "real_name",
        "source_file",
        "question",
        "score",
        "brief",
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

    # -------- detailed 用ビュー --------
    detailed_cols = [
        "student_id",
        "real_name",
        "source_file",
        "question",
        "score",
        "detailed",
    ]
    detailed_df = merged[detailed_cols]

    # Excel 出力
    write_score_explanations_excel(
        output_excel,
        brief_df=brief_df,
        detailed_df=detailed_df,
    )

    logger.info("Wrote explanations excel to %s", output_excel)

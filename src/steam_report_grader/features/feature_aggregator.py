# src/steam_report_grader/features/feature_aggregator.py
from __future__ import annotations
from pathlib import Path
from typing import Tuple
import logging

import pandas as pd

logger = logging.getLogger(__name__)


def load_full_features(
    responses_excel: Path,
    ai_similarity_csv: Path,
    peer_similarity_csv: Path,
    symbolic_features_csv: Path,
    ai_likeness_csv: Path | None = None,
) -> pd.DataFrame:
    """
    各種特徴量を student_id x question 単位でマージする。

    - responses: student_id, Q1〜Q5（テキスト）
    - ai_similarity: student_id, question, sim_to_ai_max, sim_to_ai_mean, ...
    - peer_similarity: student_id, question, sim_to_others_max, most_similar_student_id, ...
    - symbolic_features: student_id, question, symbolic_ai_score
    - ai_likeness: student_id, question, ai_likeness_score, ai_likeness_comment

    戻り値:
      full_df: student_id, question, answer, 各種特徴量…
    """
    responses_excel = Path(responses_excel)
    ai_similarity_csv = Path(ai_similarity_csv)
    peer_similarity_csv = Path(peer_similarity_csv)
    symbolic_features_csv = Path(symbolic_features_csv)
    ai_likeness_csv = Path(ai_likeness_csv) if ai_likeness_csv else None

    # 回答
    resp_df = pd.read_excel(responses_excel, sheet_name="responses")
    # 縦持ちに変換: student_id, question, answer
    q_cols = [c for c in resp_df.columns if c.startswith("Q")]
    resp_long = resp_df.melt(
        id_vars=["student_id"],
        value_vars=q_cols,
        var_name="question",
        value_name="answer",
    )
    resp_long["student_id"] = resp_long["student_id"].astype(str)
    resp_long["question"] = resp_long["question"].astype(str)

    # 類似度系
    ai_sim_df = pd.read_csv(ai_similarity_csv)
    ai_sim_df["student_id"] = ai_sim_df["student_id"].astype(str)
    ai_sim_df["question"] = ai_sim_df["question"].astype(str)

    peer_df = pd.read_csv(peer_similarity_csv)
    # per-student版を使う想定
    if "sim_to_others_max" not in peer_df.columns:
        raise ValueError("peer_similarity_csv は per_student の方を指定してください。")
    peer_df["student_id"] = peer_df["student_id"].astype(str)
    peer_df["question"] = peer_df["question"].astype(str)

    sym_df = pd.read_csv(symbolic_features_csv)
    sym_df["student_id"] = sym_df["student_id"].astype(str)
    sym_df["question"] = sym_df["question"].astype(str)

    if ai_likeness_csv and ai_likeness_csv.exists():
        like_df = pd.read_csv(ai_likeness_csv)
        like_df["student_id"] = like_df["student_id"].astype(str)
        like_df["question"] = like_df["question"].astype(str)
    else:
        like_df = pd.DataFrame(columns=["student_id", "question", "ai_likeness_score", "ai_likeness_comment"])

    # マージ
    full = resp_long.merge(ai_sim_df, on=["student_id", "question"], how="left")
    full = full.merge(peer_df, on=["student_id", "question"], how="left")
    full = full.merge(sym_df, on=["student_id", "question"], how="left")
    full = full.merge(like_df, on=["student_id", "question"], how="left")

    # 見やすい順に並べ替え
    ordered_cols = [
        "student_id",
        "question",
        "answer",
        # AI模範
        "sim_to_ai_max",
        "sim_to_ai_mean",
        "best_ref_id",
        # peer
        "sim_to_others_max",
        "most_similar_student_id",
        "sim_to_others_mean",
        # symbolic
        "symbolic_ai_score",
        # final
        "ai_likeness_score",
        "ai_likeness_comment",
    ]
    # 存在する列だけにする
    existing_cols = [c for c in ordered_cols if c in full.columns]
    rest_cols = [c for c in full.columns if c not in existing_cols]
    full = full[existing_cols + rest_cols]

    return full

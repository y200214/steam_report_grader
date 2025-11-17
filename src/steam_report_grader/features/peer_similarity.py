# src/steam_report_grader/features/peer_similarity.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple

import logging
import pandas as pd

from ..preprocess.text_cleaning import normalize_text
from ..io.responses_loader import load_responses_and_questions
from ..config import PEER_SIMILARITY_NGRAM

logger = logging.getLogger(__name__)


def _ngram_shingles(text: str, n: int) -> set[str]:
    text = text.replace("\n", " ")
    text = " ".join(text.split())
    if len(text) < n:
        return {text} if text else set()
    return {text[i:i+n] for i in range(len(text) - n + 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    if union == 0:
        return 0.0
    return inter / union


@dataclass
class PeerSimilarityRow:
    student_id: str
    question: str
    peer_sim_max: float
    peer_most_similar_id: str
    peer_sim_mean: float


def compute_peer_similarity_for_responses(
    responses_excel_path: Path,
    n: int | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    匿名回答Excelから    匿名回答Excelから、受験者同士の類似度特徴量を計算する。
    n を指定しなければ config.PEER_SIMILARITY_NGRAM を使う。、受験者同士の類似度特徴量を計算する。

    戻り値:
    per_student_df:
        student_id, question, sim_to_others_max,
        most_similar_student_id, sim_to_others_mean
      pair_df:
        question, student_id_a, student_id_b, similarity
    """
    if n is None:
        n = PEER_SIMILARITY_NGRAM

    responses_excel_path = Path(responses_excel_path)
    df, questions = load_responses_and_questions(responses_excel_path)
    
    logger.info("Loaded responses for peer similarity: %d rows", len(df))


    per_student_rows: List[Dict] = []
    pair_rows: List[Dict] = []

    for q in questions:
        logger.info("Computing peer similarity for %s", q)
        sub = df[["student_id", q]].copy()
        sub = sub.rename(columns={q: "answer"})
        sub["answer"] = sub["answer"].fillna("").astype(str).str.strip()
        sub = sub[sub["answer"] != ""]
        if sub.empty:
            continue

        # n-gram 集合の事前計算
        shingles_map: Dict[str, set[str]] = {}
        for _, row in sub.iterrows():
            sid = str(row["student_id"])
            ans = normalize_text(row["answer"])
            shingles_map[sid] = _ngram_shingles(ans, n=n)

        sids = list(shingles_map.keys())
        n_students = len(sids)

        for i in range(n_students):
            sid_i = sids[i]
            sh_i = shingles_map[sid_i]
            sims_to_others: List[Tuple[str, float]] = []

            for j in range(n_students):
                sid_j = sids[j]
                if sid_i == sid_j:
                    continue
                sh_j = shingles_map[sid_j]
                sim = _jaccard(sh_i, sh_j)
                sims_to_others.append((sid_j, sim))

                # ペアは i<j のときだけ記録
                if i < j:
                    pair_rows.append(
                        {
                            "question": q,
                            "student_id_a": sid_i,
                            "student_id_b": sid_j,
                            "similarity": sim,
                        }
                    )

            if not sims_to_others:
                per_student_rows.append(
                    {
                        "student_id": sid_i,
                        "question": q,
                        "sim_to_others_max": 0.0,          
                        "most_similar_student_id": "",     
                        "sim_to_others_mean": 0.0,         
                    }
                )
                continue

            sid_best, sim_max = max(sims_to_others, key=lambda t: t[1])
            sim_mean = sum(s for _, s in sims_to_others) / len(sims_to_others)

            per_student_rows.append(
                {
                    "student_id": sid_i,
                    "question": q,
                    "sim_to_others_max": sim_max,         
                    "most_similar_student_id": sid_best,  
                    "sim_to_others_mean": sim_mean,       
                }
            )

    per_student_df = pd.DataFrame(per_student_rows)
    pair_df = pd.DataFrame(pair_rows)
    return per_student_df, pair_df

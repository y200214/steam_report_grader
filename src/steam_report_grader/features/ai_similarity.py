# src/steam_report_grader/features/ai_similarity.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import logging

import pandas as pd

from .ai_reference import load_ai_references, AIReferenceAnswer
from ..preprocess.text_cleaning import normalize_text  # 既存の前処理を流用
from ..io.responses_loader import load_responses_and_questions
from ..config import AI_SIMILARITY_NGRAM

logger = logging.getLogger(__name__)


def _ngram_shingles(text: str, n: int) -> set[str]:
    text = text.replace("\n", " ")
    text = " ".join(text.split())  # 連続スペースを1つに
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
class AISimilarity:
    student_id: str
    question: str
    ai_ref_sim_max: float
    ai_ref_sim_mean: float
    ai_ref_best_id: Optional[str]


def compute_similarity_to_ai(
    answer_text: str,
    ai_refs: list[AIReferenceAnswer],
    n: int | None = None,
) -> tuple[float, float, str | None]:
    if n is None:
        n = AI_SIMILARITY_NGRAM

    # ★AI参照が0件ならここで 0 扱いにして返す
    if not ai_refs:
        logger.warning(
            "compute_similarity_to_ai called with no AI references; "
            "returning 0.0 similarity."
        )
        return 0.0, 0.0, None

    norm_ans = normalize_text(answer_text)
    ans_shingles = _ngram_shingles(norm_ans, n=n)

    sims: list[tuple[AIReferenceAnswer, float]] = []
    for ref in ai_refs:
        ref_norm = normalize_text(ref.text)
        ref_shingles = _ngram_shingles(ref_norm, n=n)
        sim = _jaccard(ans_shingles, ref_shingles)
        sims.append((ref, sim))

    if not sims:
        return 0.0, 0.0, None

    sims_values = [s for _, s in sims]
    sim_max = max(sims_values)
    sim_mean = sum(sims_values) / len(sims_values)

    best_ref, _ = max(sims, key=lambda t: t[1])
    return sim_max, sim_mean, best_ref.ref_id


def compute_ai_similarity_for_responses(
    responses_excel_path: Path,
    ai_reference_dir: Path,
) -> pd.DataFrame:
    """
    steam_exam_responses.xlsx を入力として、
    各 student_id × Q について AI模範解答との類似度を計算し、
    DataFrame を返す。

    戻り値のカラム:
      - student_id
      - question
      - ai_ref_sim_max
      - ai_ref_sim_mean
      - ai_ref_best_id
    """
    responses_excel_path = Path(responses_excel_path)
    ai_reference_dir = Path(ai_reference_dir)

    df, questions = load_responses_and_questions(responses_excel_path)

    refs_by_q: Dict[str, List[AIReferenceAnswer]] = load_ai_references(
        ai_reference_dir, questions
    )

    rows = []
    for _, row in df.iterrows():
        student_id = str(row["student_id"])
        for q in questions:
            ans = str(row.get(q, "") or "").strip()
            if not ans:
                continue

            ai_refs = refs_by_q.get(q, [])
            sim_max, sim_mean, ai_ref_best_id = compute_similarity_to_ai(ans, ai_refs)

            rows.append(
                {
                    "student_id": student_id,
                    "question": q,
                    "sim_to_ai_max": sim_max,
                    "sim_to_ai_mean": sim_mean,
                    "ai_ref_best_id": ai_ref_best_id or "",
                }
            )


    result_df = pd.DataFrame(rows)
    return result_df

# src/steam_report_grader/features/text_clustering.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple

from pathlib import Path
import logging

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

from ..preprocess.text_cleaning import normalize_text

logger = logging.getLogger(__name__)


@dataclass
class ClusterResult:
    question: str
    student_id: str
    cluster_id: int


def _decide_n_clusters(n_students: int) -> int:
    """
    学生数からクラスタ数をざっくり決める。
    雑だけど実用的なルール：
      〜4人: 1クラスタ
      〜10人: 2クラスタ
      〜20人: 3クラスタ
      21人〜: 4クラスタ
    """
    if n_students <= 4:
        return 1
    if n_students <= 10:
        return 2
    if n_students <= 20:
        return 3
    return 4


def cluster_answers_for_question(
    question: str,
    df_responses: pd.DataFrame,
    max_clusters: int | None = None,
) -> List[ClusterResult]:
    """
    1つの設問について、学生の回答をクラスタリングする。

    df_responses: columns = ["student_id", "answer"]
    """
    texts = []
    student_ids = []

    for _, row in df_responses.iterrows():
        sid = str(row["student_id"])
        ans = str(row["answer"] or "").strip()
        if not ans:
            continue
        norm = normalize_text(ans)
        texts.append(norm)
        student_ids.append(sid)

    n_students = len(student_ids)
    if n_students == 0:
        return []

    n_clusters = _decide_n_clusters(n_students)
    if max_clusters is not None:
        n_clusters = min(n_clusters, max_clusters)
    n_clusters = max(1, min(n_clusters, n_students))

    logger.info(
        "Clustering %s: %d students into %d clusters",
        question, n_students, n_clusters
    )

    # 文字 n-gram ベースの TF-IDF
    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(3, 5),
        min_df=1,
    )
    X = vectorizer.fit_transform(texts)

    model = KMeans(
        n_clusters=n_clusters,
        n_init=10,
        random_state=42,
    )
    labels = model.fit_predict(X)

    results: List[ClusterResult] = []
    for sid, label in zip(student_ids, labels):
        results.append(
            ClusterResult(
                question=question,
                student_id=sid,
                cluster_id=int(label),
            )
        )

    return results

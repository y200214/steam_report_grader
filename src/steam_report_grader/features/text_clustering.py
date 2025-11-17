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
from ..config import (
    CLUSTER_STUDENTS_1,
    CLUSTER_STUDENTS_2,
    CLUSTER_STUDENTS_3,
    CLUSTER_DEFAULT_N_CLUSTERS,
    CLUSTER_CHAR_NGRAM_MIN,
    CLUSTER_CHAR_NGRAM_MAX,
    CLUSTER_KMEANS_N_INIT,
    CLUSTER_KMEANS_RANDOM_STATE,
)
logger = logging.getLogger(__name__)


@dataclass
class ClusterResult:
    question: str
    student_id: str
    cluster_id: int


def _decide_n_clusters(n_students: int) -> int:
    """
    学生数からクラスタ数をざっくり決める。
    閾値は config.py で変更可能。
    """
    if n_students <= CLUSTER_STUDENTS_1:
        return 1
    if n_students <= CLUSTER_STUDENTS_2:
        return 2
    if n_students <= CLUSTER_STUDENTS_3:
        return 3
    return CLUSTER_DEFAULT_N_CLUSTERS


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
    ngram_range=(CLUSTER_CHAR_NGRAM_MIN, CLUSTER_CHAR_NGRAM_MAX),
    min_df=1,
    )
    X = vectorizer.fit_transform(texts)

    model = KMeans(
        n_clusters=n_clusters,
        n_init=CLUSTER_KMEANS_N_INIT,
        random_state=CLUSTER_KMEANS_RANDOM_STATE,
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

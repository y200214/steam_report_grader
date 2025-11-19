import pandas as pd
import logging
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer

from ..utils.logging_utils import setup_logging


def run_relative_ranking(
    features_csv: Path,
    absolute_scores_csv: Path,
    ranking_csv: Path,
    log_path: Path,
):
    setup_logging(log_path)
    logger = logging.getLogger(__name__)
    logger.info("Start relative ranking pipeline")

    # 圧縮特徴データ読み込み
    df_feat = pd.read_csv(features_csv)

    # summary + quote を1つのテキストに統合
    df_feat["text"] = df_feat["summary"].fillna("") + " " + df_feat["quote1"].fillna("") + " " \
                      + df_feat["quote2"].fillna("") + " " + df_feat["quote3"].fillna("")

    # 受験者単位でテキストとスコアを集計
    student_texts = df_feat.groupby("student_id")["text"].apply(" ".join).to_dict()
    student_scores = df_feat.groupby("student_id")["normalized_score"].mean().to_dict()

    students = list(student_texts.keys())
    corpus = [student_texts[sid] for sid in students]

    # TF-IDFベクトル化
    tfidf = TfidfVectorizer().fit_transform(corpus)
    sims = (tfidf * tfidf.T).toarray()  # コサイン類似度行列

    # 類似度平均を計算（自己類似度を除く）
    mean_cosine = {}
    for i, sid in enumerate(students):
        sim_sum = sims[i].sum() - sims[i][i]
        count = len(students) - 1
        mean_cosine[sid] = (sim_sum / count) if count > 0 else 0.0

    # 相対スコア計算
    records = []
    for sid in students:
        mean_norm = student_scores.get(sid, 0.0)
        mean_sim = mean_cosine.get(sid, 0.0)
        relative_score = 0.5 * mean_norm + 0.5 * (1.0 - mean_sim)
        records.append((sid, relative_score))

    df_rel = pd.DataFrame(records, columns=["student_id", "relative_score"])
    df_rel["relative_rank"] = df_rel["relative_score"].rank(method="dense", ascending=False).astype(int)

    # 既存のranking.csvとマージ
    df_rank = pd.read_csv(ranking_csv)
    df_rank = df_rank.merge(df_rel, on="student_id", how="left")
    df_rank.to_csv(ranking_csv, index=False, encoding="utf-8-sig")
    logger.info("Merged relative scores into %s", ranking_csv)

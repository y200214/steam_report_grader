# src/steam_report_grader/pipelines/ai_likeness_pipeline.py
from __future__ import annotations
from pathlib import Path
import logging

from ..utils.logging_utils import setup_logging
from ..features.ai_likeness_evaluator import AILikenessEvaluator
from ..llm.ollama_client import OllamaClient, OllamaConfig
from ..io.excel_writer import write_ai_likeness_report_excel
import pandas as pd
from ..io.responses_loader import load_responses_excel

logger = logging.getLogger(__name__)

def run_ai_likeness(
    responses_excel: Path,
    ai_similarity_csv: Path,
    peer_similarity_csv: Path,
    symbolic_features_csv: Path,
    output_excel: Path,
    log_path: Path,
    model_name: str = "gpt-oss-20b",

    # ★ ここから追加引数（CLIと合わせる）
    likeness_csv: Path | None = None,
    mode: str = "all",
    targets_csv: Path | None = None,
) -> None:
    """
    AI模範解答との類似度、受験者同士の類似度、記号的特徴量を基に、
    最終的なAI疑惑スコア（ai_likeness_score）を計算し、レポートを出力する。

    ※ 現時点では mode / targets_csv はまだ中で使っていない。
       将来 GUI から部分再評価をするとき用の拡張フック。
    """
    setup_logging(log_path)
    logger.info("Start AI Likeness pipeline (mode=%s)", mode)

    responses_excel = Path(responses_excel)
    ai_similarity_csv = Path(ai_similarity_csv)
    peer_similarity_csv = Path(peer_similarity_csv)
    symbolic_features_csv = Path(symbolic_features_csv)
    output_excel = Path(output_excel)
    # ★ likeness_csv が指定されていなければデフォルトパスを使う
    likeness_csv = Path(likeness_csv) if likeness_csv else Path("data/intermediate/features/ai_likeness.csv")

    # データの読み込み
    ai_similarity_df = pd.read_csv(ai_similarity_csv)
    peer_similarity_df = pd.read_csv(peer_similarity_csv)
    symbolic_features_df = pd.read_csv(symbolic_features_csv)
    responses_df = load_responses_excel(responses_excel)


    # 型合わせ（student_id を str に寄せる）
    for df in (ai_similarity_df, peer_similarity_df, symbolic_features_df, responses_df):
        if "student_id" in df.columns:
            df["student_id"] = df["student_id"].astype(str)

    if "question" in ai_similarity_df.columns:
        ai_similarity_df["question"] = ai_similarity_df["question"].astype(str)
    if "question" in peer_similarity_df.columns:
        peer_similarity_df["question"] = peer_similarity_df["question"].astype(str)
    if "question" in symbolic_features_df.columns:
        symbolic_features_df["question"] = symbolic_features_df["question"].astype(str)

    # LLM クライアントの準備
    client = OllamaClient(OllamaConfig(model=model_name))
    evaluator = AILikenessEvaluator(client)

    results = []

    # 受験者ごとに最終評価を実行
    questions = list(ai_similarity_df["question"].unique())

    for _, row in responses_df.iterrows():
        student_id = str(row["student_id"])

        for q in questions:
            # 特徴量を取得（存在しない場合はスキップ）
            ai_row = ai_similarity_df[
                (ai_similarity_df["student_id"] == student_id) & (ai_similarity_df["question"] == q)
            ]
            peer_row = peer_similarity_df[
                (peer_similarity_df["student_id"] == student_id) & (peer_similarity_df["question"] == q)
            ]
            sym_row = symbolic_features_df[
                (symbolic_features_df["student_id"] == student_id) & (symbolic_features_df["question"] == q)
            ]

            if ai_row.empty or peer_row.empty or sym_row.empty:
                continue  # 特徴量が揃ってない場合はとりあえず無視

            ai_sim = float(ai_row["sim_to_ai_max"].values[0])
            peer_sim = float(peer_row["sim_to_others_max"].values[0])
            symbolic_score = float(sym_row["symbolic_ai_score"].values[0])
            answer_text = str(row.get(q, "") or "").strip()

            # AIテンプレ度を評価
            result = evaluator.evaluate_likeness(
                student_id=student_id,
                question=q,
                ai_sim_score=ai_sim,
                peer_sim_score=peer_sim,
                symbolic_score=symbolic_score,
                answer_text=answer_text,
            )

            results.append({
                "student_id": student_id,
                "question": q,
                "ai_likeness_score": result["ai_likeness_score"],
                "ai_likeness_comment": result["ai_likeness_comment"],
                "answer_text": answer_text,
            })

    # 結果をDataFrameに
    results_df = pd.DataFrame(results)

    # ★ 中間CSVとして保存（ai-report が読む用）
    likeness_csv.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(likeness_csv, index=False, encoding="utf-8-sig")
    logger.info("Wrote AI likeness features to %s", likeness_csv)

    # 結果をExcelに保存
    write_ai_likeness_report_excel(output_excel, results_df)
    logger.info("Wrote AI likeness report to %s", output_excel)


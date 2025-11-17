# src/steam_report_grader/pipelines/scoring_pipeline.py
from __future__ import annotations

from pathlib import Path
import logging
from typing import List, Dict, Any
from dataclasses import dataclass
import json

import pandas as pd

from ..utils.logging_utils import setup_logging
from ..llm.ollama_client import OllamaClient, OllamaConfig
from ..grading.rubric import load_all_rubrics
from ..grading.absolute_scorer import AbsoluteScorer, ScoreResult
from ..io.responses_loader import load_responses_and_questions
from concurrent.futures import ThreadPoolExecutor, as_completed
# from ..llm.factory import create_default_scorer  # ← 使わないならコメントアウト or 削除

logger = logging.getLogger(__name__)


@dataclass
class ScoringTask:
    student_id: str
    question_label: str
    answer_text: str
    rubric: Any


def _score_one_task(scorer: AbsoluteScorer, task: ScoringTask) -> ScoreResult:
    """
    1つの (受験者, 設問, 回答) を採点して ScoreResult を返すヘルパー。
    """
    return scorer.score_answer(task.student_id, task.rubric, task.answer_text)


def run_scoring(
    responses_excel_path: Path,
    rubric_dir: Path,
    output_path: Path,
    log_path: Path,
    model_name: str = "gpt-oss:20b",  # ← Ollama 側と揃える
    max_workers: int = 2,
    ollama_timeout: int | None = None,
) -> None:

    """
    匿名化された回答 Excel を読み込み、Q1〜Q5 を絶対評価。
    結果を CSV で保存する。
    """
    setup_logging(log_path)
    logger.info("Start scoring pipeline")

    responses_excel_path = Path(responses_excel_path)
    rubric_dir = Path(rubric_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df, questions = load_responses_and_questions(responses_excel_path)
    rubrics = load_all_rubrics(rubric_dir, questions)

    # scorer の生成（温度0・seed固定などは OllamaConfig のデフォルトで統一）
    config = OllamaConfig(model=model_name)
    if ollama_timeout is not None:
        config.timeout = ollama_timeout

    client = OllamaClient(config)
    scorer = AbsoluteScorer(client)


    cfg = client.config
    logger.info(
        "Using model=%s, temperature=%.2f, seed=%s",
        cfg.model,
        cfg.temperature,
        cfg.seed,
    )

    results: List[ScoreResult] = []

    # --- まずタスクを全部作る ---
    tasks: List[ScoringTask] = []
    for _, row in df.iterrows():
        student_id = str(row["student_id"])
        for q_label in questions:
            answer = str(row.get(q_label, "") or "").strip()
            if not answer:
                # 空欄は普通にスキップ。warning にするか info にするかは好み
                logger.debug("Empty answer: %s %s", student_id, q_label)
                continue

            rubric = rubrics[q_label]
            tasks.append(
                ScoringTask(
                    student_id=student_id,
                    question_label=q_label,
                    answer_text=answer,
                    rubric=rubric,
                )
            )

    logger.info("Total scoring tasks: %d", len(tasks))
    logger.info("Using %d workers", max_workers)

    # --- 並列で採点 ---
    max_workers = 2  # 必要に応じて設定化

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(_score_one_task, scorer, task): task
            for task in tasks
        }

        for i, future in enumerate(as_completed(future_to_task), start=1):
            task = future_to_task[future]
            try:
                res = future.result()
                results.append(res)
            except Exception as e:
                logger.exception(
                    "Failed to score %s %s: %s",
                    task.student_id,
                    task.question_label,
                    e,
                )

            if i % 10 == 0:
                logger.info("Scored %d / %d tasks", i, len(tasks))

    # 結果を DataFrame に変換
    rows: List[Dict[str, Any]] = []
    for r in results:
        # --- 簡易説明（brief） ---
        # 原則: summary_bullets をつないだもの
        if r.summary_bullets:
            brief_text = " / ".join(r.summary_bullets)
        elif r.detailed_explanation:
            # bullet がないときだけ詳細文を流用
            brief_text = r.detailed_explanation
        else:
            brief_text = ""

        # --- 詳細説明（detailed） ---
        detailed_text = r.detailed_explanation or ""

        base: Dict[str, Any] = {
            "student_id": r.student_id,
            "question": r.question_label,
            "score": r.score,

            # === 正式名称 ===
            "brief": brief_text,
            "detailed": detailed_text,

            # 箇条書きの元データ
            "summary_bullets": " • ".join(r.summary_bullets) if r.summary_bullets else "",

            # === 互換カラム（レガシー） ===
            # これらは読み取り専用扱いにしていく
            "reason": brief_text,                 # 簡易コメントとして互換
            "brief_explanation": brief_text,
            "detailed_explanation": detailed_text,

            # evidence は JSON 文字列で保存
            "evidence": json.dumps(r.evidence, ensure_ascii=False),

            "raw_response": r.raw_response,
        }

        # subscores 展開（今の実装に合わせて）
        for k, v in r.subscores.items():
            base[f"sub_{k}"] = v

        rows.append(base)


    if not rows:
        logger.warning("No scores generated. Check logs.")
        return

    out_df = pd.DataFrame(rows)
    out_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info("Wrote scores to %s", output_path)

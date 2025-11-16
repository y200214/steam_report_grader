# src/steam_report_grader/grading/rubric.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import logging

logger = logging.getLogger(__name__)


@dataclass
class QuestionRubric:
    question_label: str      # "Q1" など
    question_text: str       # 設問本文（必要なら）
    rubric_text: str         # 評価基準（自由記述）
    max_score: int = 5


def load_rubric_for_question(
    q_label: str,
    rubric_dir: Path,
    default_max_score: int = 5,
) -> QuestionRubric:
    """
    data/raw/rubric/Q1.txt みたいなファイルからルーブリックを読む。
    ファイルの中身は「設問説明 + 観点 + 配点の説明」を自由に書いてOK。
    よくあるやり方:
      - 先頭数行を設問文
      - その後を評価観点
    として扱う。
    """
    rubric_dir = Path(rubric_dir)
    path = rubric_dir / f"{q_label}.txt"

    if not path.exists():
        logger.warning("Rubric file not found for %s: %s", q_label, path)
        # とりあえず最低限動くようにする
        return QuestionRubric(
            question_label=q_label,
            question_text="",
            rubric_text=f"(ルーブリックファイル {path.name} が見つかりませんでした)",
            max_score=default_max_score,
        )

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        logger.warning("Rubric file is empty for %s: %s", q_label, path)

    # シンプルに: 最初の空行までを設問文、それ以降を評価基準、とする
    parts = text.split("\n\n", 1)
    if len(parts) == 2:
        question_text, rubric_body = parts
    else:
        question_text, rubric_body = "", text

    return QuestionRubric(
        question_label=q_label,
        question_text=question_text.strip(),
        rubric_text=rubric_body.strip(),
        max_score=default_max_score,
    )


def load_all_rubrics(
    rubric_dir: Path,
    questions: list[str],
    default_max_score: int = 5,
) -> Dict[str, QuestionRubric]:
    return {
        q: load_rubric_for_question(q, rubric_dir, default_max_score)
        for q in questions
    }

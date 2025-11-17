# src/steam_report_grader/io/responses_loader.py
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import logging
import pandas as pd

logger = logging.getLogger(__name__)


def load_responses_excel(path: Path | str) -> pd.DataFrame:
    """
    回答 Excel（steam_exam_responses.xlsx）の responses シートを読み込む共通関数。
    """
    path = Path(path)
    df = pd.read_excel(path, sheet_name="responses")
    logger.info("Loaded responses from %s (rows=%d)", path, len(df))
    return df


def detect_question_columns(df: pd.DataFrame, prefix: str = "Q") -> List[str]:
    """
    Q1, Q2, ... のような設問列を検出してソートして返す。
    """
    questions = [
        c for c in df.columns
        if isinstance(c, str) and c.startswith(prefix)
    ]

    def sort_key(col: str) -> int:
        suffix = col[len(prefix):]
        try:
            return int(suffix)
        except ValueError:
            return 10**9  # 数値に変換できないものは最後に

    questions = sorted(questions, key=sort_key)
    return questions


def load_responses_and_questions(
    path: Path | str,
    prefix: str = "Q",
) -> Tuple[pd.DataFrame, List[str]]:
    """
    回答シートと設問リストをまとめて取得するヘルパー。
    """
    df = load_responses_excel(path)
    questions = detect_question_columns(df, prefix=prefix)
    logger.info("Detected questions (%s*): %s", prefix, questions)
    return df, questions

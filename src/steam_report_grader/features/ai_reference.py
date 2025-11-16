# src/steam_report_grader/features/ai_reference.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class AIReferenceAnswer:
    question_label: str  # "Q1" など
    ref_id: str          # ファイル名 or 任意のID
    text: str


def load_ai_references(
    base_dir: Path,
    questions: List[str],
) -> Dict[str, List[AIReferenceAnswer]]:
    """
    data/raw/ai_reference/Q1/*.txt のような構造から、
    質問ごとの模範解答リストを読み込む。
    """
    base_dir = Path(base_dir)
    refs: Dict[str, List[AIReferenceAnswer]] = {}

    for q in questions:
        q_dir = base_dir / q
        if not q_dir.exists():
            logger.warning("AI reference dir not found for %s: %s", q, q_dir)
            refs[q] = []
            continue

        answers: List[AIReferenceAnswer] = []
        for path in sorted(q_dir.glob("*.txt")):
            text = path.read_text(encoding="utf-8").strip()
            if not text:
                continue
            answers.append(
                AIReferenceAnswer(
                    question_label=q,
                    ref_id=path.name,
                    text=text,
                )
            )
        refs[q] = answers
        logger.info("Loaded %d AI references for %s", len(answers), q)

    return refs

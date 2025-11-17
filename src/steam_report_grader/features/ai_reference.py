# src/steam_report_grader/features/ai_reference.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Iterable, Optional
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class AIReferenceAnswer:
    ref_id: str
    question: str
    text: str
    meta: Dict[str, Any] | None = None


def _load_ai_refs_for_question(question: str, base_dir: Path) -> List[AIReferenceAnswer]:
    q_dir = base_dir / question
    if not q_dir.exists():
        logger.info("No AI reference dir for %s", question)
        return []

    refs: List[AIReferenceAnswer] = []

    # --- Markdown 形式(.md) ---
    for path in sorted(q_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        ref_id = path.stem  # 例: "chatgpt_4_1_v1_Q1"
        refs.append(
            AIReferenceAnswer(
                ref_id=ref_id,
                question=question,
                text=text,
                meta={"source": "md_file"},
            )
        )

    # --- JSON 形式（将来用） ---
    for path in sorted(q_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        refs.append(
            AIReferenceAnswer(
                ref_id=data.get("ref_id", path.stem),
                question=question,
                text=data["text"],
                meta=data.get("meta", {"source": "json_file"}),
            )
        )

    logger.info("Loaded %d AI references for %s", len(refs), question)
    return refs


def load_ai_references(
    base_dir: Path,
    questions: Optional[Iterable[str]] = None,
) -> Dict[str, List[AIReferenceAnswer]]:
    """
    AI模範解答を {question: [AIReferenceAnswer, ...]} で返す。

    parameters
    ----------
    base_dir : Path
        AI参照のベースディレクトリ (例: data/raw/ai_reference)
    questions : Iterable[str] | None
        対象とする設問ラベル (["Q1", "Q2", ...])
        None の場合は base_dir 配下の Q* ディレクトリを自動検出する。
    """
    base_dir = Path(base_dir)
    refs_by_question: Dict[str, List[AIReferenceAnswer]] = {}

    if not base_dir.exists():
        logger.warning("AI reference base dir does not exist: %s", base_dir)
        return refs_by_question

    if questions is None:
        # Q1, Q2, ... ディレクトリを自動検出
        questions_iter = [
            p.name
            for p in sorted(base_dir.iterdir())
            if p.is_dir() and p.name.upper().startswith("Q")
        ]
    else:
        questions_iter = list(questions)

    for q in questions_iter:
        refs_by_question[q] = _load_ai_refs_for_question(q, base_dir)

    return refs_by_question


# 1問だけ読みたいとき用のエイリアス（必要なら）
load_ai_references_for_question = _load_ai_refs_for_question

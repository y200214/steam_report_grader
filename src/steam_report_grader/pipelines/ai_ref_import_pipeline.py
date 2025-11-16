# src/steam_report_grader/pipelines/ai_ref_import_pipeline.py
from __future__ import annotations
from pathlib import Path
import logging

from ..utils.logging_utils import setup_logging
from ..io.docx_markdown import docx_to_markdown_by_question

logger = logging.getLogger(__name__)


def run_import_ai_ref(
    source_docx: Path,
    tag: str,
    ai_ref_base_dir: Path,
    log_path: Path,
) -> None:
    """
    AI模範解答を貼り付けた Word (.docx) を読み込み、
    Câu 1: / Câu hỏi 1: / Q1 / Q 1 ... などで Q1〜Q5 に分割し、
    data/raw/ai_reference/Q1/〜 に Markdown 形式で保存する。
    """
    setup_logging(log_path)

    source_docx = Path(source_docx)
    ai_ref_base_dir = Path(ai_ref_base_dir)

    if not source_docx.exists():
        logger.error("Source docx not found: %s", source_docx)
        return

    logger.info("Import AI reference from %s with tag '%s'", source_docx, tag)

    q_markdowns = docx_to_markdown_by_question(source_docx, max_question=5)

    for q_label, text in q_markdowns.items():
        if not text.strip():
            logger.info("No content for %s, skipping", q_label)
            continue

        out_dir = ai_ref_base_dir / q_label
        out_dir.mkdir(parents=True, exist_ok=True)

        # 例: gptoss_20251116_Q1.md
        out_path = out_dir / f"{tag}_{q_label}.md"
        out_path.write_text(text, encoding="utf-8")

        logger.info("Wrote AI ref for %s to %s", q_label, out_path)

    logger.info("AI reference import finished")

# src/steam_report_grader/pipelines/ai_ref_import_all_pipeline.py
from __future__ import annotations
from pathlib import Path
import logging

from ..utils.logging_utils import setup_logging
from ..utils.tag_generator import filename_to_tag
from .ai_ref_import_pipeline import run_import_ai_ref

logger = logging.getLogger(__name__)


def run_import_all_ai_ref(
    source_dir: Path,
    ai_ref_base_dir: Path,
    log_path: Path,
) -> None:
    """
    source_dir 内の .docx をすべて処理し、
    各ファイルごとに import-ai-ref を適用する。
    """
    setup_logging(log_path)
    source_dir = Path(source_dir)
    ai_ref_base_dir = Path(ai_ref_base_dir)

    files = sorted(source_dir.glob("*.docx"))

    if not files:
        logger.warning("No .docx files found in %s", source_dir)
        return

    logger.info("Found %d AI reference source files", len(files))

    for path in files:
        tag = filename_to_tag(path)
        logger.info("Processing %s (tag=%s)", path.name, tag)

        run_import_ai_ref(
            source_docx=path,
            tag=tag,
            ai_ref_base_dir=ai_ref_base_dir,
            log_path=log_path,
        )

    logger.info("All AI reference sources imported successfully.")

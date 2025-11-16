# src/steam_report_grader/pipelines/preprocess_pipeline.py
from pathlib import Path
import logging
from typing import List

from ..utils.logging_utils import setup_logging
from ..utils.id_generator import generate_student_id
from ..io.docx_reader import extract_text_from_docx, extract_name
from ..preprocess.text_cleaning import normalize_text
from ..preprocess.question_parser import extract_answers
from ..preprocess.anonymizer import build_anonymous_records
from ..io.excel_writer import write_responses_excel, write_id_map_excel


def run_preprocess(
    docx_dir: Path,
    output_excel_dir: Path,
    log_path: Path,
) -> None:
    """
    docx_dir 以下の .docx をすべて読み込み、
    - Q1〜Q5 抽出
    - 名前抽出
    - student_id 付与
    - 匿名化 Excel 出力
    - 対応表 Excel 出力
    まで行う。
    """
    setup_logging(log_path)
    logger = logging.getLogger(__name__)

    docx_dir = Path(docx_dir)
    output_excel_dir = Path(output_excel_dir)

    files = sorted(docx_dir.glob("*.docx"))
    if not files:
        logger.warning("No .docx files found in %s", docx_dir)
        return

    logger.info("Found %d .docx files in %s", len(files), docx_dir)

    per_file_answers: List[dict] = []
    for idx, path in enumerate(files, start=1):
        logger.info("Processing file %d/%d: %s", idx, len(files), path.name)
        try:
            raw_text = extract_text_from_docx(path)
            norm_text = normalize_text(raw_text)
            name = extract_name(norm_text)
            answers = extract_answers(norm_text)

            student_id = generate_student_id(idx)
            per_file_answers.append(
                {
                    "student_id": student_id,
                    "file": path.name,
                    "name": name,
                    "answers": answers,
                }
            )
        except Exception as e:
            logger.exception("Failed to process %s: %s", path, e)

    records, id_map_rows = build_anonymous_records(per_file_answers)

    # 出力パス
    responses_path = output_excel_dir / "steam_exam_responses.xlsx"
    id_map_path = output_excel_dir / "steam_exam_id_map.xlsx"

    write_responses_excel(responses_path, records)
    write_id_map_excel(id_map_path, id_map_rows)

    logger.info("Wrote responses to %s", responses_path)
    logger.info("Wrote id map to %s", id_map_path)

# src/steam_report_grader/preprocess/anonymizer.py
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class StudentRecord:
    student_id: str
    real_name: str | None
    source_file: str
    answers: Dict[str, str]


def build_anonymous_records(
    per_file_answers: List[dict],
) -> tuple[List[StudentRecord], List[dict]]:
    """
    per_file_answers: 
      [{"index": 1, "file": "xxx.docx", "name": "...", "answers": {...}}, ...]
    を受け取って、
    - 匿名化した StudentRecord のリスト
    - ID ↔ 本名 の対応表用 dict のリスト
    を返す。
    """
    records: List[StudentRecord] = []
    id_map: List[dict] = []

    for item in per_file_answers:
        student_id = item["student_id"]
        name = item.get("name")
        source = item["file"]
        answers = item["answers"]

        records.append(
            StudentRecord(
                student_id=student_id,
                real_name=name,
                source_file=source,
                answers=answers,
            )
        )

        id_map.append(
            {
                "student_id": student_id,
                "real_name": name or "",
                "source_file": source,
            }
        )

    return records, id_map

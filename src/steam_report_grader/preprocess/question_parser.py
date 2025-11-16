# src/steam_report_grader/preprocess/question_parser.py
from __future__ import annotations
import re
from typing import Dict, Optional

QUESTION_COUNT = 5

def _build_answer_pattern(qnum: int, next_qnum: Optional[int]) -> re.Pattern:
    """
    'Phần trả lời câu hỏi {qnum}:' から次の 'Câu {next_qnum}:' まで、など。
    表記ゆれに少し強くする。
    """
    # 'Phần trả lời câu hỏi 1:' のゆれを吸収
    base = rf"Phần\s+trả\s+lời\s+câu\s+hỏi\s*{qnum}\s*:?"

    if next_qnum is not None:
        # 次の設問開始候補
        next_cau = rf"C[ÂÂA]u\s*{next_qnum}\s*:?"        # Câu 2:, CÂU 2:
        next_ans = rf"Phần\s+trả\s+lời\s+câu\s+hỏi\s*{next_qnum}\s*:?"
        pattern = rf"{base}\s*(.*?)(?={next_cau}|{next_ans}|$)"
    else:
        pattern = rf"{base}\s*(.*)$"

    return re.compile(pattern, flags=re.DOTALL | re.IGNORECASE)


def _fallback_split_by_cau(text: str, qnum: int, next_qnum: Optional[int]) -> Optional[str]:
    """
    'Câu {qnum}:' ～ 'Câu {next_qnum}:' の範囲で fallback 抽出。
    """
    this_cau = re.compile(rf"C[ÂÂA]u\s*{qnum}\s*:", flags=re.IGNORECASE)
    m = this_cau.search(text)
    if not m:
        return None
    start = m.end()

    if next_qnum is not None:
        next_cau = re.compile(rf"C[ÂÂA]u\s*{next_qnum}\s*:", flags=re.IGNORECASE)
        m2 = next_cau.search(text, start)
        end = m2.start() if m2 else len(text)
    else:
        end = len(text)

    answer = text[start:end].strip()
    return answer or None


def extract_answers(text: str) -> Dict[str, str]:
    """
    テキスト全体から Q1〜Q5 の回答を辞書で返す。
    表記ゆれをある程度吸収する。
    """
    answers: Dict[str, str] = {}

    for q in range(1, QUESTION_COUNT + 1):
        next_q = q + 1 if q < QUESTION_COUNT else None

        pattern = _build_answer_pattern(q, next_q)
        m = pattern.search(text)
        answer: Optional[str] = None
        if m:
            answer = m.group(1).strip()

        # パターンで取れなかったら fallback
        if not answer:
            answer = _fallback_split_by_cau(text, q, next_q)

        answers[f"Q{q}"] = answer or ""

    return answers

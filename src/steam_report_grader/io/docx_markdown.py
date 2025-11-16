# src/steam_report_grader/io/docx_markdown.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional
import re

from docx import Document

from ..preprocess.text_cleaning import normalize_text


def paragraph_to_markdown(para) -> str:
    """
    1つの段落を Markdown テキストに変換する。
    - 太字: ** ... **
    - それ以外: そのまま
    """
    parts: List[str] = []
    for run in para.runs:
        text = run.text
        if not text:
            continue
        if run.bold:
            parts.append(f"**{text}**")
        else:
            parts.append(text)
    line = "".join(parts).strip()
    return line


import re

class QuestionSplitter:
    def __init__(self, max_question: int = 5) -> None:
        self.max_question = max_question

    def detect_question_label(self, line: str) -> Optional[str]:
        # アクセントや大文字小文字の揺れをざっくり吸収
        s = line.lower()
        # ベトナム語の「câu」のアクセントを取るのは大変なので、
        # とりあえず "câu" と "cau" 両方見る
        s = s.replace("câu", "cau")

        for q in range(1, self.max_question + 1):
            label = f"Q{q}"
            # 代表的なパターンを全部 OR
            patterns = [
                rf"cau\s+h[oô]i\s+{q}",  # cau hoi 1 / câu hỏi 1
                rf"cau\s+{q}",          # cau 1 / câu 1
                rf"\bq\s*{q}\b",        # Q1 / Q 1
            ]
            for p in patterns:
                if re.search(p, s):
                    return label
        return None


    def split_paragraphs(self, paragraphs: List[str]) -> Dict[str, List[str]]:
        """
        paragraphs: すでに Markdown 化された 1行ずつのリスト。
        戻り値: {"Q1": [...], "Q2": [...]} のような辞書。
        """
        buffers: Dict[str, List[str]] = {f"Q{i}": [] for i in range(1, self.max_question + 1)}
        current_label: Optional[str] = None

        for line in paragraphs:
            if not line.strip():
                continue

            q_label = self.detect_question_label(line)
            if q_label:
                current_label = q_label
                # 区切り行自体は解答に含めないことにする（含めたければここで append）
                continue

            if current_label:
                buffers[current_label].append(line)

        # 空 Q はそのまま空リスト
        return buffers


def docx_to_markdown_by_question(path: Path, max_question: int = 5) -> Dict[str, str]:
    """
    .docx を読み込み、Q1〜Q5の模範解答を Markdown 文字列として返す。
    返り値: {"Q1": "...", "Q2": "..."} （中身が空文字のこともある）
    """
    path = Path(path)
    doc = Document(path)

    # パラグラフを Markdown 1行に変換
    md_lines: List[str] = []
    for para in doc.paragraphs:
        line = paragraph_to_markdown(para)
        if line:
            md_lines.append(line)

    splitter = QuestionSplitter(max_question=max_question)
    buffers = splitter.split_paragraphs(md_lines)

    result: Dict[str, str] = {}
    for q in range(1, max_question + 1):
        label = f"Q{q}"
        lines = buffers.get(label, [])
        # normalize_text で軽く整形（改行など）
        joined = "\n\n".join(lines)
        result[label] = normalize_text(joined) if joined else ""

    return result

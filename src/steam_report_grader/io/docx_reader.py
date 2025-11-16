# src/steam_report_grader/io/docx_reader.py
from pathlib import Path
import zipfile
import re
from typing import Optional

def extract_text_from_docx(path: Path) -> str:
    """
    .docx の中身 (word/document.xml) からテキストをざっくり抽出。
    完全な XML パースではなく、タグ除去ベース。
    """
    path = Path(path)
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")

    # 改行タグを先に仮の改行に寄せてもいいが、簡易にはタグ全部削除
    text = re.sub(r"<[^>]+>", "", xml)
    return text


def extract_name(text: str) -> Optional[str]:
    """
    ベトナム語フォーマット想定:
    'Họ và tên: XXXXX Số thứ tự:' の間を名前として抜く。
    """
    m = re.search(r"Họ và tên:\s*(.*?)Số thứ tự:", text, flags=re.DOTALL)
    if not m:
        return None
    name = m.group(1).strip()
    return name or None

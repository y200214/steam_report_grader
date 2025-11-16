# src/steam_report_grader/utils/tag_generator.py
import re
from pathlib import Path

def filename_to_tag(path: Path) -> str:
    """
    'ChatGPT 4.1 v1.docx' → 'chatgpt_41_v1'
    'Gemini2.5 pro v2.docx' → 'gemini25_pro_v2'
    """
    name = path.stem  # 拡張子なし
    name = name.lower()
    name = re.sub(r"[^\w]+", "_", name)   # 英数字以外 → _
    name = re.sub(r"_+", "_", name)       # 連続_ → 1つ
    return name.strip("_")

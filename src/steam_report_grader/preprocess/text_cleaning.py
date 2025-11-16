# src/steam_report_grader/preprocess/text_cleaning.py
import unicodedata
import re

def normalize_text(raw: str) -> str:
    """
    docx から抜いた生テキストを、解析しやすい形に前処理する。
    - Unicode 正規化 (NFKC)
    - 改行コード統一
    - 制御文字の除去
    - 余計なスペースの整理（ただし問の境界が壊れない程度）
    """
    if raw is None:
        return ""

    # Unicode 正規化
    text = unicodedata.normalize("NFKC", raw)

    # 改行を統一
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 制御文字除去（タブは残してもいいが、ここでは消す）
    text = "".join(ch for ch in text if ch == "\n" or ch >= " ")

    # 連続スペースを1個に（ただし改行はそのまま）
    text = re.sub(r"[ \t]+", " ", text)

    # 行頭行末のスペース削る
    text = "\n".join(line.strip() for line in text.split("\n"))

    return text.strip()

# src/steam_report_grader/features/symbolic_features.py
import re
from typing import List
import numpy as np
from ..config import (
    SYMB_WEIGHT_BOLD,
    SYMB_WEIGHT_HEADING,
    SYMB_WEIGHT_LINE,
    SYMB_WEIGHT_BULLET,
    SYMB_WEIGHT_CONNECTIVE,
    SYMB_WEIGHT_SENT_LEN,
    SYMB_SENT_LEN_SCALE,
    SYMB_MAX_SCORE,
)

# 太字頻度（**...**）
def count_bold(text: str) -> int:
    return text.count("**")

# 見出し（#）
def count_headings(text: str) -> int:
    return text.count("#")

# 区切り線（---）
def count_horizontal_lines(text: str) -> int:
    return text.count("---")

# 箇条書き（- や *）
def count_bullets(text: str) -> int:
    return text.count("- ") + text.count("* ")

# 接続詞の頻度（例: さらに、また）
def count_connectives(text: str) -> int:
    connectives = ["また", "さらに", "加えて", "つまり", "例えば", "そのため"]
    return sum(text.count(connective) for connective in connectives)

# 文長の均一性（平均文長 / 文数）
def calculate_average_sentence_length(text: str) -> float:
    sentences = re.split(r'[。！]', text)  # 日本語の文区切り
    sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
    if len(sentence_lengths) == 0:
        return 0
    return np.mean(sentence_lengths)

# symbolic_ai_score を計算
def calculate_symbolic_features(text: str) -> float:
    bold_count = count_bold(text)
    heading_count = count_headings(text)
    line_count = count_horizontal_lines(text)
    bullet_count = count_bullets(text)
    connective_count = count_connectives(text)
    avg_sentence_length = calculate_average_sentence_length(text)

    # 評価基準を調整してスコア化
    score = (
        bold_count * SYMB_WEIGHT_BOLD
        + heading_count * SYMB_WEIGHT_HEADING
        + line_count * SYMB_WEIGHT_LINE
        + bullet_count * SYMB_WEIGHT_BULLET
        + connective_count * SYMB_WEIGHT_CONNECTIVE
        + (avg_sentence_length / SYMB_SENT_LEN_SCALE) * SYMB_WEIGHT_SENT_LEN
    )

    return min(score, SYMB_MAX_SCORE)
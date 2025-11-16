# src/steam_report_grader/features/symbolic_features.py
import re
from typing import List
import numpy as np

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
        bold_count * 0.3
        + heading_count * 0.2
        + line_count * 0.1
        + bullet_count * 0.1
        + connective_count * 0.2
        + (avg_sentence_length / 10) * 0.1  # 文長が安定してるとAIっぽい
    )
    
    # 最大スコアは1.0に調整
    return min(score, 1.0)

# src/steam_report_grader/config/__init__.py

"""
GUI からいじるための「数値パラメータ置き場」。

- 質問数（Q1〜Q?）
- 類似度計算の n-gram 長さ
- クラスタリングのしきい値・パラメータ
- 記号的特徴の重み
- AI疑惑フラグにする閾値

などをここに集約しておく。
"""

# -------------------------
# 質問数（Q1〜Q? まであるか）
# -------------------------
# 例: 5 にすると Q1〜Q5 までが有効になる
QUESTION_COUNT: int = 5


# -------------------------
# 類似度用 n-gram 長
# -------------------------
# AI模範解答との類似度で使う文字 n-gram の長さ
AI_SIMILARITY_NGRAM: int = 3

# 受験者どうしの類似度で使う文字 n-gram の長さ
PEER_SIMILARITY_NGRAM: int = 3


# -------------------------
# クラスタリングのルールとパラメータ
# -------------------------
# 受験者数からクラスタ数を決めるしきい値
#   〜 CLUSTER_STUDENTS_1 人 → 1クラスタ
#   〜 CLUSTER_STUDENTS_2 人 → 2クラスタ
#   〜 CLUSTER_STUDENTS_3 人 → 3クラスタ
#   それ以上                → CLUSTER_DEFAULT_N_CLUSTERS クラスタ
CLUSTER_STUDENTS_1: int = 4
CLUSTER_STUDENTS_2: int = 10
CLUSTER_STUDENTS_3: int = 20
CLUSTER_DEFAULT_N_CLUSTERS: int = 4

# TF-IDF で使う文字 n-gram の範囲
# 例: (3, 5) なら 3〜5 文字の連続した文字列を特徴量として見る
CLUSTER_CHAR_NGRAM_MIN: int = 3
CLUSTER_CHAR_NGRAM_MAX: int = 5

# KMeans のパラメータ
# n_init: 初期値を変えて何回試すか（多いほど安定するが重い）
# random_state: ランダムシード（同じ値なら結果が再現しやすい）
CLUSTER_KMEANS_N_INIT: int = 10
CLUSTER_KMEANS_RANDOM_STATE: int = 42


# -------------------------
# 記号的特徴の重み
# -------------------------
# symbolic_features.calculate_symbolic_features() が使う重みづけ

# 太字 (**...**) 一つあたりの重み
SYMB_WEIGHT_BOLD: float = 0.3
# 見出し (# ...) 一つあたりの重み
SYMB_WEIGHT_HEADING: float = 0.2
# 区切り線 (---) 一つあたりの重み
SYMB_WEIGHT_LINE: float = 0.1
# 箇条書き (- や •) 一つあたりの重み
SYMB_WEIGHT_BULLET: float = 0.1
# 接続詞 ("しかし", "一方で" など) の重み
SYMB_WEIGHT_CONNECTIVE: float = 0.2
# 文の平均長さに対する重み
SYMB_WEIGHT_SENT_LEN: float = 0.1

# 文長をスコア化するとき、どれくらいで割るか（スケール調整）
SYMB_SENT_LEN_SCALE: float = 10.0

# 記号的特徴スコアの最大値（これ以上はクリップ）
SYMB_MAX_SCORE: float = 1.0


# -------------------------
# AI疑惑フラグにする閾値
# -------------------------
# ai_likeness_max がこの値以上なら「AIっぽい」とフラグを立てる
AI_SUSPECT_THRESHOLD: float = 0.7

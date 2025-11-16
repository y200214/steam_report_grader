# src/steam_report_grader/llm/cluster_prompts.py
from __future__ import annotations
from textwrap import dedent
from typing import List


def build_cluster_summary_and_ai_template_prompt(
    question_label: str,
    question_text: str,
    rubric_text: str,
    sample_answers: List[str],
) -> str:
    """
    クラスター内の代表的な回答群を渡して、
    - クラスター要約
    - AIテンプレ度
    を評価させるプロンプト。
    """
    # サンプルを区切って渡す
    joined_answers = "\n\n---\n\n".join(sample_answers)

    prompt = f"""
    あなたは教育評価と文章スタイル分析の専門家です。
    以下は同じ設問に対する複数の学生の回答です。
    これらは「似たスタイルの回答」を集めたクラスターです。

    [設問番号]
    {question_label}

    [設問]
    {question_text.strip()}

    [ルーブリックの概要]
    {rubric_text.strip()[:800]}

    [クラスター内の受験者回答サンプル]
    {joined_answers}

    タスク:
    1. このクラスターの回答が、どのような特徴を持つか要約してください。
       - 内容面（何を書いているか）
       - 構造面（段落構成・論理展開）
       - 文体面（丁寧さ、語彙、定型表現など）

    2. このクラスターの文章が「生成AI（ChatGPTやGeminiなど）が書いたテンプレート的な回答」に
       どの程度似ているか、0.0〜1.0 でスコアを付けてください。
       - 1.0 に近いほど「AIテンプレっぽい」
       - 0.0 に近いほど「人間らしくバラつきがある」

    3. 「なぜそのスコアにしたのか」を、教師が理解しやすい形で説明してください。

    出力は以下の JSON 形式「だけ」を返してください。説明文や余計な文章は一切書かないでください。

    {{
      "summary": "このクラスターの特徴の要約",
      "ai_template_likeness": 数値,
      "comment": "AIテンプレっぽさに関する説明"
    }}
    """
    return dedent(prompt).strip()

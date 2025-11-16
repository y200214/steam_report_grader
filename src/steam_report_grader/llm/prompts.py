# src/steam_report_grader/llm/prompts.py
from __future__ import annotations
from textwrap import dedent

def build_scoring_prompt(
    question_label: str,
    question_text: str,
    rubric_text: str,
    answer_text: str,
    max_score: int = 5,
) -> str:
    """
    絶対評価用プロンプト。
    出力は JSON 固定にして後処理しやすくする。
    """
    prompt = f"""
        あなたはSTEAM教育の専門家であり、評価に関しても専門家です。
        以下の設問とルーブリックに基づいて、受験者の回答を厳密に採点してください。

        [設問番号]
        {question_label}

        [設問]
        {question_text.strip()}

        [ルーブリック]
        {rubric_text.strip()}

        [受験者の回答]
        {answer_text.strip()}

        指示:
        1. ルーブリックに基づいて 0〜{max_score} 点で採点してください。
        2. 評価の観点ごとにサブスコアを付けてください。
        3. 次の2種類の説明を作成してください:
          - summary_bullets: 最大3〜4件の箇条書き。簡潔に「なぜこの点数なのか」がわかるように。
          - detailed_explanation: 200〜400字程度で、評価の理由を丁寧に説明する長文。
        4. evidence には、評価の根拠となる受験者の回答からの短い引用を入れてください。
          - その回答において重要であると考え、評価に影響した箇所
          - 1件あたり20〜30文字程度
          - その引用がどの観点に対応するかを aspect に書いてください。
        5. 出力は必ず次の JSON 形式だけを出力し、それ以外の文章は一切書かないでください。
        6．出力は **Python の dict リテラル** 形式で、以下のキーを含めてください。
       - キー名はダブルクォートでもシングルクォートでも構いません。
       - 文字列中でダブルクォート（"）を使わないでください（代わりにシングルクォートを使ってください）。
        出力フォーマット:
        {{
          "score": 数値,
          "subscores": {{
            "観点1": 数値,
            "観点2": 数値
          }},
          "summary_bullets": [
            "箇条書き1",
            "箇条書き2"
          ],
          "detailed_explanation": "長文の説明",
          "evidence": [
            {{
              "aspect": "観点名",
              "quote": "受験者の回答からの短い引用"
            }}
          ]
        }}
        """
    return dedent(prompt).strip()

def build_final_evaluation_prompt(
    student_id: str,
    question: str,
    ai_sim_score: float,
    peer_sim_score: float,
    symbolic_score: float,
    answer_text: str,
) -> str:
    """
    最終的な AI疑惑スコアを算出するためのプロンプト
    """
    prompt = f"""
    あなたは教育評価とAIテンプレ検出の専門家です。
    以下は、学生の解答に関するいくつかの特徴量です。
    これらの情報を基に、AIが書いた可能性のある解答かどうかを0〜1のスコアで判断し、その理由を説明してください。
    出力は必ず次の JSON 形式「だけ」を返してください。
    [学生ID]
    {student_id}

    [設問]
    {question}

    [回答]
    {answer_text.strip()}

    [特徴量]
    - AI模範解答との類似度（ai_similarity_score）: {ai_sim_score:.2f}
    - 受験者同士の類似度（peer_similarity_score）: {peer_sim_score:.2f}
    - 記号的特徴スコア（symbolic_score）: {symbolic_score:.2f}

    1. 上記の特徴を総合的に評価して、この学生の解答が「生成AIによるテンプレート的な解答」である可能性を
       0.0（全くAIっぽくない）から1.0（完全にAIっぽい）でスコア化してください。
    2. そのスコアの理由を、以下の観点で説明してください：
       - 構造化（序論・本論・結論が整いすぎている）
       - 定型表現（AIがよく使う表現、ポジティブバイアス）
       - 文体の均一性（文の長さ、語彙の使用など）
       - 具体例の典型的すぎる点（他の学生と似た内容）
    出力は必ず次の JSON 形式「だけ」を返してください。
    出力:
    {{
      "ai_likeness_score": 数値,
      "ai_likeness_comment": "評価理由"
    }}
    """
    return dedent(prompt).strip()
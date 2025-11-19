import pandas as pd
import logging
from pathlib import Path

from ..llm.ollama_pool import get_ollama_client
from ..utils.logging_utils import setup_logging
from ..io.responses_loader import load_responses_excel, detect_question_columns
import ast

def safe_parse_json(text: str) -> dict:
    try:
        return ast.literal_eval(text)
    except Exception:
        return {}


def run_relative_features(
    responses_excel_path: Path,
    absolute_scores_csv: Path,
    output_path: Path,
    model_name: str,
    llm_provider: str,
    log_path: Path,
):
    setup_logging(log_path)
    logger = logging.getLogger(__name__)
    logger.info("Start relative features pipeline")

    df_resp = load_responses_excel(responses_excel_path)
    questions = detect_question_columns(df_resp, prefix="Q")
    df_scores = pd.read_csv(absolute_scores_csv)
    max_scores = df_scores.groupby("question")["score"].max().to_dict()

    # 2GPU対応の Ollama クライアントを取得（model_name は今は使わず共通設定）
    client = get_ollama_client()
    logger.info(
        "Using relative-features LLM via 2-GPU pool (requested model_name=%s)",
        model_name,
    )
    records = []

    # 進捗管理用のざっくり総数（スキップ分は含まれるので目安）
    total = len(df_resp) * len(questions)
    done = 0

    for _, row in df_resp.iterrows():
        sid = str(row["student_id"])
        for q in questions:
            ans = str(row.get(q, "") or "").strip()
            if not ans:
                continue
            score_row = df_scores[(df_scores.student_id == sid) & (df_scores.question == q)]
            if score_row.empty:
                continue
            score = float(score_row.iloc[0]["score"])
            max_sc = max_scores.get(q, 0)
            normalized = (score / max_sc) if max_sc > 0 else 0.0

            prompt = f"""
            以下の学生の回答について、要約と3つの重要な引用をJSON形式で出力してください。

            回答: {ans}

            出力形式:
            {{
              'summary': '要約文 (日本語)',
              'quotes': ['引用1', '引用2', '引用3']
            }}
            """
            llm_text = client.generate(prompt, temperature=0.0)
            clean_text = llm_text.strip().replace("```json", "").replace("```", "").strip()
            data = safe_parse_json(clean_text)

            summary = data.get("summary", "")
            quotes = data.get("quotes", []) or []
            quotes = [str(q) for q in quotes] + [""] * 3
            q1, q2, q3 = (quotes + ["", "", ""])[:3]

            records.append({
                "student_id": sid,
                "question": q,
                "normalized_score": normalized,
                "summary": summary,
                "quote1": q1,
                "quote2": q2,
                "quote3": q3,
            })

    if records:
        out_df = pd.DataFrame(records)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        out_df.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info("Wrote relative features to %s (%d rows)", output_path, len(out_df))
    else:
        logger.warning("No features generated; check inputs.")

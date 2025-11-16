# src/steam_report_grader/features/ai_cluster_eval.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any
import json
import logging

import pandas as pd

from ..llm.ollama_client import OllamaClient, OllamaConfig
from ..llm.cluster_prompts import build_cluster_summary_and_ai_template_prompt
from ..grading.rubric import load_all_rubrics

logger = logging.getLogger(__name__)


@dataclass
class ClusterAnalysis:
    question: str
    cluster_id: int
    ai_template_likeness: float
    summary: str
    comment: str
    raw_response: str


def analyze_clusters_with_llm(
    responses_df: pd.DataFrame,
    cluster_df: pd.DataFrame,
    rubric_dir: str | None,
    model_name: str = "gpt-oss-20b",
) -> List[ClusterAnalysis]:
    """
    cluster_df: columns = ["student_id", "question", "cluster_id"]
    responses_df: sheet "responses" 全体を想定
    rubric_dir: Q1〜Q5 の rubric txt を置いた dir。None の場合は question_text, rubric_text を空にする。
    """
    client = OllamaClient(OllamaConfig(model=model_name))

    questions = sorted(cluster_df["question"].unique(), key=lambda x: int(x[1:]))

    if rubric_dir:
        from pathlib import Path
        rubrics = load_all_rubrics(Path(rubric_dir), questions)
    else:
        rubrics = {}

    analyses: List[ClusterAnalysis] = []

    for q in questions:
        sub_cluster = cluster_df[cluster_df["question"] == q]
        if sub_cluster.empty:
            continue

        # 回答抽出用
        # responses_df は列: student_id, Q1..Q5
        for cluster_id in sorted(sub_cluster["cluster_id"].unique()):
            sub_c = sub_cluster[sub_cluster["cluster_id"] == cluster_id]
            if sub_c.empty:
                continue

            # このクラスタの student_id たち
            sids = sub_c["student_id"].astype(str).tolist()

            # 回答の抽出
            answers = []
            col_q = q  # "Q1" など
            for sid in sids:
                row = responses_df[responses_df["student_id"] == sid]
                if row.empty:
                    continue
                ans = str(row.iloc[0][col_q] or "").strip()
                if ans:
                    answers.append(ans)

            if not answers:
                continue

            # サンプルは多すぎるとプロンプトが長くなるので、最大10件くらいにする
            sample_answers = answers[:10]

            rubric = rubrics.get(q)
            question_label = q
            if rubric:
                question_text = rubric.question_text or ""
                rubric_text = rubric.rubric_text or ""
            else:
                question_text = ""
                rubric_text = ""

            prompt = build_cluster_summary_and_ai_template_prompt(
                question_label=question_label,
                question_text=question_text,
                rubric_text=rubric_text,
                sample_answers=sample_answers,
            )

            try:
                llm_text = client.generate(prompt)
                parsed = _safe_parse_json(llm_text)
                summary = str(parsed.get("summary", "") or "")
                likeness = float(parsed.get("ai_template_likeness", 0.0))
                comment = str(parsed.get("comment", "") or "")

                analyses.append(
                    ClusterAnalysis(
                        question=q,
                        cluster_id=int(cluster_id),
                        ai_template_likeness=likeness,
                        summary=summary,
                        comment=comment,
                        raw_response=llm_text,
                    )
                )

            except Exception as e:
                logger.exception(
                    "Failed to analyze cluster %s %s: %s", q, cluster_id, e
                )

    return analyses


def _safe_parse_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and start < end:
        json_str = text[start : end + 1]
    else:
        json_str = text

    try:
        return json.loads(json_str)
    except Exception as e:
        logger.warning("Failed to parse JSON from LLM response: %s", e)
        return {}

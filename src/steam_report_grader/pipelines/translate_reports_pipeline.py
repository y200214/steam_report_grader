# src/steam_report_grader/pipelines/translate_reports_pipeline.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import json
import logging

import pandas as pd
from textwrap import dedent

from ..utils.logging_utils import setup_logging
from ..llm.ollama_client import OllamaClient, OllamaConfig

logger = logging.getLogger(__name__)

# 対象ファイル → { シート名 → 翻訳したいカラム一覧 }
TRANSLATION_TARGETS: Dict[str, Dict[str, List[str]]] = {
    # 採点理由（score_explanations.xlsx）
    "score_explanations.xlsx": {
        # brief シートの key_evidence だけ翻訳
        "brief": ["key_evidence"],
    },
    # AI類似度レポート（ai_likeness_report.xlsx）
    "ai_likeness_report.xlsx": {
        "ai_likeness": ["answer_text", "ai_likeness_comment"],
    },
    # AI疑惑レポート（ai_suspect_report.xlsx）
    "ai_suspect_report.xlsx": {
        "suspected": [
            "answer_text",
            "answer_text_x",
            "answer_text_y",
            "ai_likeness_comment",
        ],
        "full_features": [
            "answer_text",
            "answer_text_x",
            "answer_text_y",
            "ai_likeness_comment",
        ],
    },
}


def _build_translation_prompt(fields: Dict[str, str]) -> str:
    """
    1行分の複数フィールドをまとめて翻訳するためのプロンプトを組み立てる。
    - すでに日本語の部分はなるべくそのまま
    - ベトナム語・英語などは自然な日本語へ翻訳
    """
    json_text = json.dumps(fields, ensure_ascii=False, indent=2)
    prompt = f"""
    あなたは日本語が得意なプロの翻訳者です。

    次の JSON オブジェクトの各値は、日本語・ベトナム語・英語、
    またはそれらの混在で書かれた短いテキストです。

    - すでに自然な日本語で書かれている部分は、意味を変えずにそのまま残すか、
      軽く整える程度にしてください。
    - 日本語以外の部分（ベトナム語・英語など）は、自然で読みやすい日本語に翻訳してください。
    - 数字・記号・数式・固有名詞は、できるだけ元の形を保ってください。
    - キー名（フィールド名）は絶対に変更しないでください。

    入力 JSON:
    {json_text}

    出力フォーマット:
    - 上記と同じキーを持つ JSON オブジェクト「だけ」を返してください。
    - 余計な説明文やコードブロック（```json など）は書かないでください。
    """
    return dedent(prompt).strip()


def _parse_json_like(text: str) -> Dict[str, str]:
    """
    LLM からの出力をできるだけ頑張って JSON として解釈する。
    - ```json ... ``` や ``` ... ``` で囲まれていても対応
    - { ... } の最外郭だけ抜き出して json.loads
    """
    if not text:
        return {}

    raw = text.strip()

    # ```json ... ``` / ``` ... ``` を剥がす
    if raw.startswith("```"):
        lines = raw.splitlines()
        if len(lines) >= 2:
            # 先頭行 ```xxx を削る
            if lines[-1].strip().startswith("```"):
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            raw = "\n".join(lines).strip()

    # { ... } の範囲だけ抜き出す
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and start < end:
        json_str = raw[start : end + 1]
    else:
        json_str = raw

    try:
        data = json.loads(json_str)
        if isinstance(data, dict):
            # キーも値も str にそろえる
            return {str(k): "" if v is None else str(v) for k, v in data.items()}
        return {}
    except Exception as e:
        logger.warning(
            "Failed to parse JSON from translation response: %s | raw head=%r",
            e,
            raw[:120],
        )
        return {}


def _translate_dataframe(
    df: pd.DataFrame,
    target_columns: List[str],
    client: OllamaClient,
) -> pd.DataFrame:
    """
    指定されたカラムに対して *_ja カラムを追加し、翻訳結果を入れる。
    - 元の列はそのまま残す（上書きしない）
    """
    if df.empty:
        return df

    # 実際に存在するカラムだけ対象にする
    cols = [c for c in target_columns if c in df.columns]
    if not cols:
        return df

    # 出力用の *_ja カラムを用意
    for col in cols:
        out_col = f"{col}_ja"
        if out_col not in df.columns:
            df[out_col] = pd.NA

    for idx, row in df.iterrows():
        fields: Dict[str, str] = {}
        for col in cols:
            val = row[col]
            if pd.isna(val):
                fields[col] = ""
            else:
                fields[col] = str(val)

        # すべて空なら翻訳しない
        if not any(v for v in fields.values()):
            continue

        prompt = _build_translation_prompt(fields)
        llm_text = client.generate(prompt)
        translated = _parse_json_like(llm_text)

        if not translated:
            continue

        for col in cols:
            out_col = f"{col}_ja"
            if col in translated and translated[col]:
                df.at[idx, out_col] = translated[col]

    return df


def run_translate_reports(
    output_dir: Path,
    model_name: str = "gpt-oss:20b",
    log_path: Path | str = Path("logs/app.log"),
    inplace: bool = False,
) -> None:
    """
    採点後に生成された Excel レポート群を日本語化する後処理パイプライン。

    - score_explanations.xlsx
        - sheet 'brief' の key_evidence → key_evidence_ja
    - ai_likeness_report.xlsx
        - sheet 'ai_likeness' の answer_text, ai_likeness_comment
          → answer_text_ja, ai_likeness_comment_ja
    - ai_suspect_report.xlsx
        - sheet 'suspected', 'full_features' の
          answer_text, answer_text_x, answer_text_y, ai_likeness_comment
          → *_ja 列
    """
    setup_logging(log_path)
    logger.info(
        "Start translate-reports pipeline (output_dir=%s, model=%s, inplace=%s)",
        output_dir,
        model_name,
        inplace,
    )

    output_dir = Path(output_dir)

    config = OllamaConfig(model=model_name)
    client = OllamaClient(config)

    for filename, sheet_map in TRANSLATION_TARGETS.items():
        src_path = output_dir / filename
        if not src_path.exists():
            logger.info("Skip %s (not found)", src_path)
            continue

        logger.info("Translating %s", src_path)

        xls = pd.ExcelFile(src_path)
        new_sheets: Dict[str, pd.DataFrame] = {}

        # 翻訳対象シートを処理
        for sheet_name, cols in sheet_map.items():
            if sheet_name not in xls.sheet_names:
                logger.warning(
                    "Sheet %s not found in %s; skipping that sheet",
                    sheet_name,
                    filename,
                )
                continue

            df = pd.read_excel(xls, sheet_name=sheet_name)
            df = _translate_dataframe(df, cols, client)
            new_sheets[sheet_name] = df

        # 残りのシートはそのままコピー
        for sheet_name in xls.sheet_names:
            if sheet_name in new_sheets:
                continue
            df = pd.read_excel(xls, sheet_name=sheet_name)
            new_sheets[sheet_name] = df

        # 出力先パス決定
        if inplace:
            dst_path = src_path
        else:
            dst_path = src_path.with_name(src_path.stem + "_ja" + src_path.suffix)

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        with pd.ExcelWriter(dst_path, engine="openpyxl") as writer:
            for sheet_name, df in new_sheets.items():
                df.to_excel(writer, index=False, sheet_name=sheet_name)

        logger.info("Wrote translated report to %s", dst_path)

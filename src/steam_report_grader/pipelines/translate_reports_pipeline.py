# src/steam_report_grader/pipelines/translate_reports_pipeline.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import json
import logging
from textwrap import dedent

import pandas as pd

from ..utils.logging_utils import setup_logging
from ..llm.ollama_pool import get_ollama_client
from ..config import (
    LLM_TRANSLATION_TIMEOUT,
    LLM_TRANSLATION_MAX_TOKENS,
    OLLAMA_DEFAULT_MODEL,
)

logger = logging.getLogger(__name__)


# どの Excel / シート / 列を翻訳するかの定義
TRANSLATION_TARGETS: Dict[str, Dict[str, List[str]]] = {
    # 採点理由（score_explanations.xlsx）
    "excel/score_explanations.xlsx": {
        # brief シートの key_evidence だけ翻訳
        "brief": ["key_evidence"],
    },
    # AI類似度レポート（ai_likeness_report.xlsx）
    "excel/ai_likeness_report.xlsx": {
        "ai_likeness": ["answer_text", "ai_likeness_comment"],
    },
    # AI疑惑レポート（ai_suspect_report.xlsx）
    "excel/ai_suspect_report.xlsx": {
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
    # 最終レポート（final_report.xlsx）
    "final/final_report.xlsx": {
        "by_student_question": ["ai_likeness_comment"],
    },
}


def _build_translation_prompt(text: str) -> str:
    """
    単一テキストを自然な日本語に翻訳させるだけのシンプルなプロンプト。
    """
    text = text or ""
    prompt = f"""
You are an excellent Japanese translator.
Please translate the following English text (or text in any other language) into natural, easy-to-read Japanese.

* Do not add any unnecessary explanations or prefaces.
* Your output must contain *only* the translated Japanese text.
* If the original text includes bullet points or line breaks, preserve that structure as much as possible.


Text to translate:
    {text}
    """
    return dedent(prompt).strip()


def _translate_dataframe(
    df: pd.DataFrame,
    target_columns: List[str],
    client,
) -> pd.DataFrame:
    """
    指定されたカラムに対して、元の列を日本語訳で上書きする。

    - ja 版の Excel は別ファイル（*_ja.xlsx）として出力される前提
    - なので元のベトナム語/英語は ja ファイル内には残さない
    """
    if df.empty:
        return df

    # 実際に存在するカラムだけ対象にする
    cols = [c for c in target_columns if c in df.columns]
    if not cols:
        return df

    for idx, row in df.iterrows():
        for col in cols:
            val = row[col]
            if pd.isna(val):
                continue

            src_text = str(val).strip()
            if not src_text:
                continue

            prompt = _build_translation_prompt(src_text)
            try:
                translated = client.generate(prompt)
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "LLM translation failed at row=%d, col=%s: %s",
                    idx,
                    col,
                    e,
                )
                continue

            df.at[idx, col] = (translated or "").strip()

    return df


def _parse_json_like(text: str, expected_keys: List[str]) -> Dict[str, str]:
    """
    LLM が返したテキストから JSON を抜き出して parse する。
    - 正常な JSON のとき → そのまま dict で返す
    - 失敗したとき     → テキスト全体を使ったフォールバックに切り替える
    """
    raw = (text or "").strip()
    if not raw:
        return {}

    # ```json ... ``` を剥がす
    if raw.startswith("```"):
        lines = raw.splitlines()
        if len(lines) >= 2:
            if lines[-1].strip().startswith("```"):
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            raw = "\n".join(lines).strip()

    # { ... } の範囲だけ抜き出す（余計な前後が付いていても対応）
    json_str = raw
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and start < end:
        json_str = raw[start : end + 1]

    # まずはちゃんと JSON として読めるか試す
    try:
        data = json.loads(json_str)
        if isinstance(data, dict):
            return {k: ("" if v is None else str(v)) for k, v in data.items()}
    except Exception as e:  # noqa: BLE001
        # JSON として読めなかったときはフォールバックに任せる
        logger.debug("Failed to parse translation JSON: %s", e)

    # 単一列なら「全文＝その列の訳」でいい
    if len(expected_keys) == 1:
        return {expected_keys[0]: raw}

    # 複数列なら、行ごとに順番に割り当てるだけのシンプル戦略
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    out: Dict[str, str] = {}
    for i, key in enumerate(expected_keys):
        out[key] = lines[i] if i < len(lines) else ""

    return out


def run_translate_reports(
    output_dir: Path,
    model_name: str = "gpt-oss:20b",
    llm_provider: str = "ollama",
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
        "Start translate-reports pipeline (output_dir=%s, provider=%s, model=%s, inplace=%s)",
        output_dir,
        llm_provider,
        model_name,
        inplace,
    )

    output_dir = Path(output_dir)

    # 2GPU対応の Ollama クライアント（プール）を取得
    client = get_ollama_client()
    logger.info(
        "Using translation LLM via 2-GPU pool (model=%s, timeout=%s)",
        OLLAMA_DEFAULT_MODEL,
        LLM_TRANSLATION_TIMEOUT,
    )

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

            df = xls.parse(sheet_name=sheet_name)

            # 対象列が存在しない場合はスキップ
            actual_cols = [c for c in cols if c in df.columns]
            if not actual_cols:
                logger.info(
                    "No target columns in sheet %s of %s; skipping",
                    sheet_name,
                    filename,
                )
                new_sheets[sheet_name] = df
                continue

            logger.info(
                "Translating sheet %s of %s (columns=%s)",
                sheet_name,
                filename,
                actual_cols,
            )

            # *_ja 列を準備
            for col in actual_cols:
                ja_col = f"{col}_ja"
                if ja_col not in df.columns:
                    df[ja_col] = ""

            # 各行ごとに JSON を投げて翻訳
            total_rows = len(df)
            done_rows = 0

            for idx, row in df.iterrows():
                fields: Dict[str, str] = {}
                for col in actual_cols:
                    val = row[col]
                    if pd.isna(val):
                        fields[col] = ""
                    else:
                        fields[col] = str(val)

                # すべて空なら翻訳しない
                if not any(v for v in fields.values()):
                    continue

                done_rows += 1
                remaining = total_rows - done_rows
                logger.info(
                    "[translate] %s[%s] %d/%d (remaining=%d)",
                    filename,
                    sheet_name,
                    done_rows,
                    total_rows,
                    remaining,
                )

                prompt = _build_translation_prompt(fields)
                try:
                    llm_text = client.generate(
                        prompt,
                        max_tokens=LLM_TRANSLATION_MAX_TOKENS,
                    )
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "LLM translation failed at %s[%d]: %s",
                        sheet_name,
                        idx,
                        e,
                    )
                    continue

                translated = _parse_json_like(llm_text, expected_keys=actual_cols)

                # *_ja 列に書き込み
                for col in actual_cols:
                    ja_col = f"{col}_ja"
                    if col in translated:
                        df.at[idx, ja_col] = translated[col]

            new_sheets[sheet_name] = df

        # 翻訳対象以外のシートはそのままコピー
        for sheet_name in xls.sheet_names:
            if sheet_name not in new_sheets:
                new_sheets[sheet_name] = xls.parse(sheet_name=sheet_name)

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

    logger.info("Finished translate-reports pipeline")

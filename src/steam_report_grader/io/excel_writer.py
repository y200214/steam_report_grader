# src/steam_report_grader/io/excel_writer.py
from pathlib import Path
from typing import List
import pandas as pd
from openpyxl.utils import get_column_letter
from typing import Optional
import pandas as pd
from ..preprocess.anonymizer import StudentRecord

def write_responses_excel(path: Path, records: List[StudentRecord]) -> None:
    """
    匿名化した回答一覧を Excel に書き出す。
    - 1行 = 1受験者
    - 列 = student_id, Q1〜Q5
    - wrap_text と列幅調整
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for rec in records:
        row = {"student_id": rec.student_id}
        row.update(rec.answers)
        rows.append(row)

    df = pd.DataFrame(rows)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="responses")

        ws = writer.sheets["responses"]

        # wrap_text & 列幅
        for col_cells in ws.columns:
            col_letter = get_column_letter(col_cells[0].column)
            max_len = 0
            for cell in col_cells:
                if cell.value is None:
                    continue
                cell.alignment = cell.alignment.copy(wrap_text=True)
                text = str(cell.value)
                max_len = max(max_len, min(len(text), 80))  # 上限決めておく
            ws.column_dimensions[col_letter].width = max(15, max_len * 0.8)


def write_id_map_excel(path: Path, id_map_rows: List[dict]) -> None:
    """
    student_id ↔ real_name ↔ source_file の対応表。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(id_map_rows)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="id_map")

def write_scores_summary_excel(
    path: Path,
    summary_with_names_df: pd.DataFrame,
    raw_scores_df: Optional[pd.DataFrame] = None,
) -> None:
    """
    受験者ごとのスコアサマリと、元の absolute_scores を
    1つの Excel ファイルに書き出す。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        summary_with_names_df.to_excel(writer, index=False, sheet_name="scores")

        if raw_scores_df is not None:
            raw_scores_df.to_excel(writer, index=False, sheet_name="details")

def write_ai_cluster_report_excel(
    path: Path,
    per_student_clusters_df: pd.DataFrame,
    cluster_analysis_df: pd.DataFrame,
) -> None:
    """
    AIテンプレ検出用のクラスタレポートをExcelに出力。
    - sheet "clusters": 各受験者×設問のクラスタID + AIテンプレ度（クラスタをjoin）
    - sheet "cluster_summary": 各クラスタの要約とAIテンプレ度
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # join: per_student_clusters_df (student_id, question, cluster_id)
    #       + cluster_analysis_df (question, cluster_id, ai_template_likeness, ...)
    merged = per_student_clusters_df.merge(
        cluster_analysis_df,
        on=["question", "cluster_id"],
        how="left",
        suffixes=("", "_cluster"),
    )

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        merged.to_excel(writer, index=False, sheet_name="clusters")
        cluster_analysis_df.to_excel(writer, index=False, sheet_name="cluster_summary")

def write_score_explanations_excel(
    path: Path,
    brief_df: pd.DataFrame,
    detailed_df: pd.DataFrame,
) -> None:
    """
    受験者ごとの採点理由を、人間が読みやすい形で Excel に出力する。
    - brief シート: 短い箇条書き＋キー引用
    - detailed シート: 詳細な説明テキスト
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        brief_df.to_excel(writer, index=False, sheet_name="brief")
        detailed_df.to_excel(writer, index=False, sheet_name="detailed")


def write_ai_likeness_report_excel(
    path: Path,
    likeness_df: pd.DataFrame,
) -> None:
    """
    ai_likeness の結果をそのまま1シートに出す簡易版。
    （本番では ai-report で full_features 版も出す）
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        likeness_df.to_excel(writer, index=False, sheet_name="ai_likeness")


def write_ai_suspect_report_excel(
    path: Path,
    full_features_df: pd.DataFrame,
) -> None:
    """
    AI疑惑レポートをExcelで出力する。
    - sheet 'suspected': ai_likeness_score 降順にソートした上位（怪しさ順）
    - sheet 'full_features': 全特徴量そのまま
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # 怪しさ順で並べたビュー
    if "ai_likeness_score" in full_features_df.columns:
        suspected_df = full_features_df.sort_values(
            ["ai_likeness_score"],
            ascending=[False],
            na_position="last",
        )
    else:
        suspected_df = full_features_df.copy()

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        suspected_df.to_excel(writer, index=False, sheet_name="suspected")
        full_features_df.to_excel(writer, index=False, sheet_name="full_features")

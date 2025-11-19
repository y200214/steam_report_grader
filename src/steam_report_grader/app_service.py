from __future__ import annotations

import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)

from .config import DEFAULT_SCORING_MODEL
@dataclass
class FullPipelineResult:
    """
    GUI からフルパイプラインを回したときの、ざっくりした結果情報。
    """
    project_root: Path
    final_report_dir: Path
    last_command: list[str]


def _run_cli(
    project_root: Path,
    args: Sequence[str],
) -> None:
    """
    `python -m src.steam_report_grader.cli <args...>` を
    指定した作業ディレクトリで実行するヘルパー。

    例:
        _run_cli(root, ["preprocess"])
        _run_cli(root, ["score", "--model", "gpt-oss:20b"])
    """
    cmd = [sys.executable, "-m", "src.steam_report_grader.cli", *args]

    logger.info("Running command: %s", " ".join(cmd))
    completed = subprocess.run(
        cmd,
        cwd=project_root,
        check=False,
    )

    if completed.returncode != 0:
        # GUI 側でエラー表示しやすいように、例外にして投げる
        raise RuntimeError(
            f"CLI command failed with exit code {completed.returncode}: "
            + " ".join(cmd)
        )


def run_full_pipeline(
    project_root: Path,
    model_name: str = DEFAULT_SCORING_MODEL,
) -> FullPipelineResult:
    """
    GUI から呼ぶ用の「全部入り」パイプライン。

    前提:
        - `project_root` が steam_report_grader のルートディレクトリ
          (pyproject.toml / src ディレクトリがある場所)
        - CLI サブコマンドは、あなたが普段叩いているものと同じ挙動をする

    実行順:
        1. preprocess        # Word → 匿名Excel
        2. score             # 絶対評価
        3. summary           # 集計
        4. explain           # 説明付き Excel
        5. import-all-ai-ref # AI模範解答インポート
        6. ai-similarity     # AI模範解答との類似度
        7. ai-cluster        # AIテンプレ検出クラスタ分析
        8. peer-similarity   # 受験者同士の類似度
        9. symbolic-features # 記号的特徴抽出
       10. ai-likeness       # AI疑惑スコア
       11. ai-report         # 総合レポート（中間）
       12. final-report      # 最終総合レポート出力

    戻り値:
        FullPipelineResult (最終レポート出力ディレクトリなど)
    """
    project_root = Path(project_root).resolve()

    # 1. 前処理：Word → 匿名Excel
    _run_cli(project_root, ["preprocess"])

    # 2. 採点（絶対評価）
    _run_cli(project_root, ["score", "--model", model_name])

    # 3. 集計
    _run_cli(project_root, ["summary"])

    # 4. 説明付きExcel作成
    _run_cli(project_root, ["explain"])

    # 5. AI模範解答投入
    _run_cli(project_root, ["import-all-ai-ref"])

    # 6. AI模範解答との類似度
    _run_cli(project_root, ["ai-similarity"])

    # 7. AIテンプレ検出クラスタ分析
    _run_cli(project_root, ["ai-cluster", "--model", model_name])

    # 8. 受験者同士の類似度
    _run_cli(project_root, ["peer-similarity"])

    # 9. 記号的特徴を抽出
    _run_cli(project_root, ["symbolic-features"])

    # 10. AI疑惑スコア
    _run_cli(project_root, ["ai-likeness", "--model", model_name])

    # 11. 総合レポート（中間）
    _run_cli(project_root, ["ai-report"])

    # 12. 最終総合レポート
    scores_csv = Path("data/intermediate/features/absolute_scores.csv")
    id_map = Path("data/outputs/excel/steam_exam_id_map.xlsx")
    output_dir = Path("data/outputs/final")
    log_path = Path("logs/final_report.log")

    _run_cli(
        project_root,
        [
            "final-report",
            "--scores-csv",
            str(scores_csv),
            "--id-map",
            str(id_map),
            "--output-dir",
            str(output_dir),
            "--log-path",
            str(log_path),
        ],
    )

    return FullPipelineResult(
        project_root=project_root,
        final_report_dir=project_root / output_dir,
        last_command=[
            "final-report",
            "--scores-csv",
            str(scores_csv),
            "--id-map",
            str(id_map),
            "--output-dir",
            str(output_dir),
            "--log-path",
            str(log_path),
        ],
    )

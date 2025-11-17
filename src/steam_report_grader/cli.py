# src/steam_report_grader/cli.py
from pathlib import Path
import argparse
from .pipelines.summary_pipeline import run_summary
from .pipelines.preprocess_pipeline import run_preprocess
from .pipelines.scoring_pipeline import run_scoring
from .pipelines.explanations_pipeline import run_explanations
from .pipelines.ai_similarity_pipeline import run_ai_similarity
from .pipelines.ai_ref_import_pipeline import run_import_ai_ref
from .pipelines.ai_ref_import_all_pipeline import run_import_all_ai_ref
from .pipelines.ai_cluster_pipeline import run_ai_cluster
from .pipelines.peer_similarity_pipeline import run_peer_similarity
from .pipelines.symbolic_features_pipeline import run_symbolic_features
from .pipelines.ai_likeness_pipeline import run_ai_likeness
from .pipelines.ai_report_pipeline import run_ai_report
from .pipelines.final_report_pipeline import run_final_report
from .utils.audit_logger import log_audit_record
from .pipelines.translate_reports_pipeline import run_translate_reports

def main():
    parser = argparse.ArgumentParser(
        description="STEAM レポート処理ツール"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # === preprocess ===
    p_pre = subparsers.add_parser("preprocess", help="Word から Excel に変換する")
    p_pre.add_argument(
        "--docx-dir",
        type=Path,
        default=Path("data/raw/docx"),
        help="Word ファイルが入っているディレクトリ",
    )
    p_pre.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/outputs/excel"),
        help="Excel を出力するディレクトリ",
    )
    p_pre.add_argument(
        "--log-path",
        type=Path,
        default=Path("logs/app.log"),
        help="ログファイルのパス",
    )

    # === score ===
    p_score = subparsers.add_parser("score", help="Excel から絶対評価を行う")
    p_score.add_argument(
        "--responses",
        type=Path,
        default=Path("data/outputs/excel/steam_exam_responses.xlsx"),
        help="匿名化された回答 Excel ファイル",
    )
    p_score.add_argument(
        "--rubric-dir",
        type=Path,
        default=Path("data/raw/rubric"),
        help="ルーブリックテキストを置いたディレクトリ",
    )
    p_score.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/intermediate/features/absolute_scores.csv"),
        help="採点結果 CSV の出力先",
    )
    p_score.add_argument(
        "--log-path",
        type=Path,
        default=Path("logs/app.log"),
        help="ログファイルのパス",
    )
    p_score.add_argument(
        "--model",
        type=str,
        default="gpt-oss:20b",
        help="Ollama で使うモデル名（例: gpt-oss:20b）",
    )

    p_score.add_argument(
        "--workers",
        type=int,
        default=2,
        help="並列で採点するワーカー数（ThreadPoolExecutor の max_workers）",
    )
    p_score.add_argument(
        "--ollama-timeout",
        type=int,
        default=120,
        help="Ollamaのタイムアウト秒数（秒）",
    )

    p_ex = subparsers.add_parser("explain", help="採点理由を人が読みやすい形で出力する")
    p_ex.add_argument(
        "--scores-csv",
        type=Path,
        default=Path("data/intermediate/features/absolute_scores.csv"),
        help="絶対評価結果の CSV ファイル",
    )
    p_ex.add_argument(
        "--id-map",
        type=Path,
        default=Path("data/outputs/excel/steam_exam_id_map.xlsx"),
        help="student_id と real_name の対応表 Excel",
    )
    p_ex.add_argument(
        "--output-excel",
        type=Path,
        default=Path("data/outputs/excel/score_explanations.xlsx"),
        help="説明付きExcelの出力先",
    )
    p_ex.add_argument(
        "--log-path",
        type=Path,
        default=Path("logs/app.log"),
        help="ログファイルのパス",
    )

    # === summary ===
    p_sum = subparsers.add_parser("summary", help="採点結果を集計してExcelに出力する")
    p_sum.add_argument(
        "--scores-csv",
        type=Path,
        default=Path("data/intermediate/features/absolute_scores.csv"),
        help="絶対評価結果の CSV ファイル",
    )
    p_sum.add_argument(
        "--id-map",
        type=Path,
        default=Path("data/outputs/excel/steam_exam_id_map.xlsx"),
        help="student_id と real_name の対応表 Excel",
    )
    p_sum.add_argument(
        "--output-excel",
        type=Path,
        default=Path("data/outputs/excel/absolute_scores_summary.xlsx"),
        help="集計結果を出力する Excel ファイル",
    )
    p_sum.add_argument(
        "--log-path",
        type=Path,
        default=Path("logs/app.log"),
        help="ログファイルのパス",
    )

    # === ai-similarity ===
    p_ai = subparsers.add_parser(
        "ai-similarity",
        help="AI模範解答との類似度特徴量を計算する",
    )
    p_ai.add_argument(
        "--responses",
        type=Path,
        default=Path("data/outputs/excel/steam_exam_responses.xlsx"),
        help="匿名化された回答 Excel",
    )
    p_ai.add_argument(
        "--ai-ref-dir",
        type=Path,
        default=Path("data/raw/ai_reference"),
        help="AI模範解答テキストのベースディレクトリ",
    )
    p_ai.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/intermediate/features/ai_similarity.csv"),
        help="類似度特徴量の出力先 CSV",
    )
    p_ai.add_argument(
        "--log-path",
        type=Path,
        default=Path("logs/app.log"),
        help="ログファイルのパス",
    )
    # === import-ai-ref ===
    p_imp = subparsers.add_parser(
        "import-ai-ref",
        help="AI模範解答を貼ったWordファイルからQごとのMarkdownを生成する",
    )
    p_imp.add_argument(
        "--source",
        type=Path,
        required=True,
        help="AI模範解答を貼り付けた .docx ファイル",
    )
    p_imp.add_argument(
        "--tag",
        type=str,
        required=True,
        help="この模範解答セットに付けるタグ（例: gptoss_20251116）",
    )
    p_imp.add_argument(
        "--ai-ref-dir",
        type=Path,
        default=Path("data/raw/ai_reference"),
        help="AI模範解答を保存するベースディレクトリ",
    )
    p_imp.add_argument(
        "--log-path",
        type=Path,
        default=Path("logs/app.log"),
        help="ログファイルのパス",
    )
    # === import-all-ai-ref ===
    p_impall = subparsers.add_parser(
        "import-all-ai-ref",
        help="ai_reference_sources 内の .docx をすべて Markdown に変換して保存する",
    )
    p_impall.add_argument(
        "--source-dir",
        type=Path,
        default=Path("data/raw/ai_reference"),
        help="AI模範解答 Word ファイル群を置いたディレクトリ",
    )
    p_impall.add_argument(
        "--ai-ref-dir",
        type=Path,
        default=Path("data/raw/ai_reference"),
        help="Markdown を保存するベースディレクトリ",
    )
    p_impall.add_argument(
        "--log-path",
        type=Path,
        default=Path("logs/app.log"),
        help="ログファイルのパス",
    )
    # === ai-cluster ===
    p_aic = subparsers.add_parser(
        "ai-cluster",
        help="回答をクラスタリングし、AIテンプレ度を分析する",
    )
    p_aic.add_argument(
        "--responses",
        type=Path,
        default=Path("data/outputs/excel/steam_exam_responses.xlsx"),
        help="匿名化された回答 Excel",
    )
    p_aic.add_argument(
        "--rubric-dir",
        type=Path,
        default=Path("data/raw/rubric"),
        help="ルーブリックテキストのディレクトリ（Q1.txt〜）",
    )
    p_aic.add_argument(
        "--output-excel",
        type=Path,
        default=Path("data/outputs/excel/ai_cluster_report.xlsx"),
        help="AIテンプレ分析レポートの出力先",
    )
    p_aic.add_argument(
        "--log-path",
        type=Path,
        default=Path("logs/app.log"),
        help="ログファイルのパス",
    )
    p_aic.add_argument(
        "--model",
        type=str,
        default="gpt-oss-20b",
        help="クラスタ分析に使う LLM モデル名（Ollama）",
    )
    # === peer-similarity ===
    p_peer = subparsers.add_parser(
        "peer-similarity",
        help="受験者同士の類似度（コピペ・AIテンプレ疑惑）特徴量を計算する",
    )
    p_peer.add_argument(
        "--responses",
        type=Path,
        default=Path("data/outputs/excel/steam_exam_responses.xlsx"),
        help="匿名化された回答 Excel",
    )
    p_peer.add_argument(
        "--per-student-output",
        type=Path,
        default=Path("data/intermediate/features/peer_similarity_per_student.csv"),
        help="1受験者ごとの類似度特徴量CSV",
    )
    p_peer.add_argument(
        "--pair-output",
        type=Path,
        default=Path("data/intermediate/features/peer_similarity_pairs.csv"),
        help="受験者ペアごとの類似度CSV",
    )

    p_peer.add_argument(
        "--log-path",
        type=Path,
        default=Path("logs/app.log"),
        help="ログファイルのパス",
    )
    # === symbolic-features ===
    p_symbolic = subparsers.add_parser(
        "symbolic-features",
        help="記号的特徴量（太字・見出し・箇条書き・接続詞など）を抽出する",
    )
    p_symbolic.add_argument(
        "--responses",
        type=Path,
        default=Path("data/outputs/excel/steam_exam_responses.xlsx"),
        help="匿名化された回答 Excel",
    )
    p_symbolic.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/intermediate/features/symbolic_features.csv"),
        help="記号的特徴量を出力するCSVファイル",
    )
    p_symbolic.add_argument(
        "--log-path",
        type=Path,
        default=Path("logs/app.log"),
        help="ログファイルのパス",
    )
    # === ai-likeness ===
    p_likeness = subparsers.add_parser(
        "ai-likeness",
        help="AI疑惑スコア（ai_likeness_score）を計算し、レポートを作成する",
    )
    p_likeness.add_argument(
        "--responses",
        type=Path,
        default=Path("data/outputs/excel/steam_exam_responses.xlsx"),
        help="匿名化された回答 Excel",
    )
    p_likeness.add_argument(
        "--ai-similarity-csv",
        type=Path,
        default=Path("data/intermediate/features/ai_similarity.csv"),
        help="AI模範解答との類似度特徴量CSV",
    )
    p_likeness.add_argument(
        "--peer-similarity-csv",
        type=Path,
        default=Path("data/intermediate/features/peer_similarity_per_student.csv"),
        help="受験者同士の類似度（per student）CSV",
    )
    p_likeness.add_argument(
        "--symbolic-features-csv",
        type=Path,
        default=Path("data/intermediate/features/symbolic_features.csv"),
        help="記号的特徴量CSV",
    )
    p_likeness.add_argument(
        "--output-excel",
        type=Path,
        default=Path("data/outputs/excel/ai_likeness_report.xlsx"),
        help="AI疑惑スコアを出力するExcelファイル",
    )
    p_likeness.add_argument(
        "--likeness-csv",
        type=Path,
        default=Path("data/intermediate/features/ai_likeness.csv"),
        help="AI疑惑スコアの中間結果CSV（再評価用）",
    )
    p_likeness.add_argument(
        "--mode",
        type=str,
        choices=["all", "missing", "failed", "selected"],
        default="missing",
        help="再評価モード: all=全件, missing=未評価のみ, failed=失敗のみ, selected=指定行のみ",
    )
    p_likeness.add_argument(
        "--targets-csv",
        type=Path,
        help="mode=selected のときに再評価したい (student_id,question) の一覧CSV",
    )
    p_likeness.add_argument(
        "--log-path",
        type=Path,
        default=Path("logs/app.log"),
        help="ログファイルのパス",
    )
    p_likeness.add_argument(
        "--model",
        type=str,
        default="gpt-oss:20b",
        help="AIテンプレ評価に使用するLLMモデル",
    )
    # === ai-report ===
    p_air = subparsers.add_parser(
        "ai-report",
        help="AI疑惑レポートExcelを生成する（フル特徴量付き）",
    )
    p_air.add_argument(
        "--responses",
        type=Path,
        default=Path("data/outputs/excel/steam_exam_responses.xlsx"),
        help="匿名化された回答 Excel",
    )
    p_air.add_argument(
        "--ai-similarity-csv",
        type=Path,
        default=Path("data/intermediate/features/ai_similarity.csv"),
        help="AI模範解答との類似度特徴量CSV",
    )
    p_air.add_argument(
        "--peer-similarity-csv",
        type=Path,
        default=Path("data/intermediate/features/peer_similarity_per_student.csv"),
        help="受験者同士の類似度（per student）CSV",
    )
    p_air.add_argument(
        "--symbolic-features-csv",
        type=Path,
        default=Path("data/intermediate/features/symbolic_features.csv"),
        help="記号的特徴量CSV",
    )
    p_air.add_argument(
        "--ai-likeness-csv",
        type=Path,
        default=Path("data/intermediate/features/ai_likeness.csv"),
        help="AIテンプレ最終スコアのCSV（ai-likenessパイプラインで保存しておく）",
    )
    p_air.add_argument(
        "--output-excel",
        type=Path,
        default=Path("data/outputs/excel/ai_suspect_report.xlsx"),
        help="AI疑惑レポートの出力先 Excel",
    )
    p_air.add_argument(
        "--log-path",
        type=Path,
        default=Path("logs/app.log"),
        help="ログファイルのパス",
    )

    # === final-report ===
    p_final = subparsers.add_parser(
        "final-report",
        help="ranking.csv と feedback_{id}.md を生成する",
    )
    p_final.add_argument(
        "--scores-csv",
        type=Path,
        default=Path("data/intermediate/features/absolute_scores.csv"),
        help="絶対評価結果の CSV ファイル",
    )
    p_final.add_argument(
        "--id-map",
        type=Path,
        default=Path("data/outputs/excel/steam_exam_id_map.xlsx"),
        help="student_id と real_name の対応表 Excel",
    )
    p_final.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/outputs/final"),
        help="ranking.csv / feedback_*.md を出力するディレクトリ",
    )
    p_final.add_argument(
        "--log-path",
        type=Path,
        default=Path("logs/app.log"),
        help="ログファイルのパス",
    )

    # === translate-reports ===
    p_trans = subparsers.add_parser(
        "translate-reports",
        help="採点・AI疑惑レポートのテキストを日本語に翻訳する後処理",
    )
    p_trans.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/outputs/excel"),
        help="score_explanations.xlsx や ai_*_report.xlsx が置いてあるディレクトリ",
    )
    p_trans.add_argument(
        "--model",
        type=str,
        default="gpt-oss:20b",
        help="翻訳に使うモデル名（Ollama のタグ）",
    )
    p_trans.add_argument(
        "--log-path",
        type=Path,
        default=Path("logs/app.log"),
        help="ログファイルのパス",
    )
    p_trans.add_argument(
        "--inplace",
        action="store_true",
        help="元の Excel を上書きする（デフォルトは *_ja.xlsx を新規作成）",
    )

    args = parser.parse_args()

    if args.command == "preprocess":
        run_preprocess(
            docx_dir=args.docx_dir,
            output_excel_dir=args.output_dir,
            log_path=args.log_path,
        )
        log_audit_record(
            command="preprocess",
            args=vars(args),
        )        
    elif args.command == "score":
        run_scoring(
            responses_excel_path=args.responses,
            rubric_dir=args.rubric_dir,
            output_path=args.output_csv,
            log_path=args.log_path,
            model_name=str(args.model),
            max_workers=args.workers,
            ollama_timeout=args.ollama_timeout,
        )

        log_audit_record(
            command="score",
            args=vars(args),
            extra={
                "llm": {
                    "model": args.model,
                    "temperature": 0.0,
                    "seed": 42,
                }
            },
        )
    elif args.command == "summary":
        run_summary(
            absolute_scores_csv=args.scores_csv,
            id_map_excel=args.id_map,
            output_excel=args.output_excel,
            log_path=args.log_path,
        )
        log_audit_record(
            command="summary",
            args=vars(args),
        )

    elif args.command == "explain": 
        run_explanations(
            absolute_scores_csv=args.scores_csv,
            id_map_excel=args.id_map,
            output_excel=args.output_excel,
            log_path=args.log_path,
        )    
        log_audit_record(
            command="explain",
            args=vars(args),
        )        
    elif args.command == "ai-similarity":
        run_ai_similarity(
            responses_excel=args.responses,
            ai_reference_dir=args.ai_ref_dir,
            output_csv=args.output_csv,
            log_path=args.log_path,
        )
        log_audit_record(
            command="ai-similarity",
            args=vars(args),
        )           
    elif args.command == "import-ai-ref":
        run_import_ai_ref(
            source_docx=args.source,
            tag=args.tag,
            ai_ref_base_dir=args.ai_ref_dir,
            log_path=args.log_path,
        )
        log_audit_record(
            command="import-ai-ref",
            args=vars(args),
        )            
    elif args.command == "import-all-ai-ref":
        run_import_all_ai_ref(
            source_dir=args.source_dir,
            ai_ref_base_dir=args.ai_ref_dir,
            log_path=args.log_path,
        )
        log_audit_record(
            command="import-all-ai-ref",
            args=vars(args),
        )            
    elif args.command == "ai-cluster":
        run_ai_cluster(
            responses_excel=args.responses,
            rubric_dir=args.rubric_dir,
            output_excel=args.output_excel,
            log_path=args.log_path,
            model_name=str(args.model),
        )
        log_audit_record(
            command="ai-cluster",
            args=vars(args),
        )            
    elif args.command == "peer-similarity":
        run_peer_similarity(
            responses_excel=args.responses,
            per_student_output_csv=args.per_student_output,
            pair_output_csv=args.pair_output,
            log_path=args.log_path,
        )
        log_audit_record(
            command="peer-similarity",
            args=vars(args),
        )            
    elif args.command == "symbolic-features":
        run_symbolic_features(
            responses_excel=args.responses,
            output_csv=args.output_csv,
            log_path=args.log_path,
        )
        log_audit_record(
            command="symbolic-features",
            args=vars(args),
        )            
    elif args.command == "ai-likeness":
        run_ai_likeness(
            responses_excel=args.responses,
            ai_similarity_csv=args.ai_similarity_csv,
            peer_similarity_csv=args.peer_similarity_csv,
            symbolic_features_csv=args.symbolic_features_csv,
            output_excel=args.output_excel,
            log_path=args.log_path,
            model_name=str(args.model),
            likeness_csv=args.likeness_csv,
            mode=args.mode,
            targets_csv=args.targets_csv,
        )
        log_audit_record(
            command="ai-likeness",
            args=vars(args),
            extra={
                "llm": {
                    "model": args.model,
                    "temperature": 0.0,
                    "seed": 42,
                }
            },
        )
    elif args.command == "ai-report":
        run_ai_report(
            responses_excel=args.responses,
            ai_similarity_csv=args.ai_similarity_csv,
            peer_similarity_csv=args.peer_similarity_csv,
            symbolic_features_csv=args.symbolic_features_csv,
            ai_likeness_csv=args.ai_likeness_csv,
            output_excel=args.output_excel,
            log_path=args.log_path,
        )
        log_audit_record(
            command="ai-report",
            args=vars(args),
        )            
    elif args.command == "final-report":
        run_final_report(
            absolute_scores_csv=args.scores_csv,
            id_map_excel=args.id_map,
            ranking_csv_path=args.output_dir / "ranking.csv",
            feedback_dir=args.output_dir / "feedback",
            log_path=args.log_path,
        )
        log_audit_record(
            command="final-report",
            args=vars(args),
        )

    elif args.command == "translate-reports":
        run_translate_reports(
            output_dir=args.output_dir,
            model_name=str(args.model),
            log_path=args.log_path,
            inplace=args.inplace,
        )
        log_audit_record(
            command="translate-reports",
            args=vars(args),
            extra={
                "llm": {
                    "model": args.model,
                    "temperature": 0.0,
                    "seed": 42,
                }
            },
        )
if __name__ == "__main__":
    main()

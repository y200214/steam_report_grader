実行の流れ
前処理：Word → 匿名Excel
python -m src.steam_report_grader.cli preprocess
採点（絶対評価）	
python -m src.steam_report_grader.cli score --model gpt-oss:20b
集計
python -m src.steam_report_grader.cli summary
説明付きExcel作成
python -m src.steam_report_grader.cli explain
AI模範解答投入
python -m src.steam_report_grader.cli import-all-ai-ref
AI模範解答との類似度
python -m src.steam_report_grader.cli ai-similarity
AIテンプレ検出クラスタ分析
python -m src.steam_report_grader.cli ai-cluster --model gpt-oss:20b
受験者同士の類似度
python -m src.steam_report_grader.cli peer-similarity
記号的特徴を抽出
python -m src.steam_report_grader.cli symbolic-features
最終的なAI疑惑スコア
python -m src.steam_report_grader.cli ai-likeness --model gpt-oss:20b

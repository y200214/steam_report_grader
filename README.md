---

# 自動採点システム 命名規約 & データフロー仕様


## 全体フロー概要

コマンドと入出力の対応はざっくり以下：

```text
1. 前処理（docx → 匿名Excel）
   python -m src.steam_report_grader.cli preprocess

2. 絶対評価（採点）
   python -m src.steam_report_grader.cli score --model gpt-oss:20b

3. 集計・説明付きExcel
   python -m src.steam_report_grader.cli summary
   python -m src.steam_report_grader.cli explain

4. AI参照・疑惑系
   python -m src.steam_report_grader.cli import-all-ai-ref
   python -m src.steam_report_grader.cli ai-similarity
   python -m src.steam_report_grader.cli ai-cluster --model gpt-oss:20b
   python -m src.steam_report_grader.cli peer-similarity
   python -m src.steam_report_grader.cli symbolic-features
   python -m src.steam_report_grader.cli ai-likeness --model gpt-oss:20b
   python -m src.steam_report_grader.cli ai-report

5. 最終レポート（成績＋AI疑惑＋個別フィードバック）
   python -m src.steam_report_grader.cli final-report
```
GPU0 → http://localhost:11434
GPU1 → http://localhost:11435

"docker compose up -d"でサーバー起動
---

## 1. コア命名規約（カラム名）

### 1-1. ID・メタ情報

| 概念      | カラム名          | 説明                              |
| ------- | ------------- | ------------------------------- |
| 匿名受験者ID | `student_id`  | 匿名化された受験者ID（`S001` など）          |
| 設問      | `question`    | `"Q1"`, `"Q2"` などの設問ラベル         |
| 元ファイル名  | `source_file` | 元の Word/Excel ファイル名             |
| 実名      | `real_name`   | 受験者の実名（`id_map.xlsx` から復元）      |
| 素点      | `score`       | 設問ごとの絶対評価スコア（数値）                |
| サブスコア   | `sub_<key>`   | ルーブリック観点ごとのスコア（例: `sub_説明の明確さ`） |

> **ルール：**
> DataFrame / CSV のカラム名は必ずこれに合わせる。
> Python 内の変数名（`question_label` など）は多少違ってもよいが、DataFrame には最終的に `student_id` / `question` を使う。

---

### 1-2. 講評（説明テキスト）

**正式カラム**

| 概念         | カラム名              | 由来                                  |
| ---------- | ----------------- | ----------------------------------- |
| 簡易コメント（短め） | `brief`           | 箇条書き要約を結合したものが基本                    |
| 詳細コメント（長め） | `detailed`        | モデルが返す長文の説明                         |
| 箇条書き要約     | `summary_bullets` | 箇条書きの要素を `" / "` や `" • "` で結合した文字列 |

**レガシー/互換カラム（読むだけ）**

| カラム名                   | 意味             | 扱い               |
| ---------------------- | -------------- | ---------------- |
| `reason`               | もともと講評として使っていた | 現在は `brief` のコピー |
| `brief_explanation`    | 簡易説明           | `brief` と互換      |
| `detailed_explanation` | 詳細説明           | `detailed` と互換   |

> **ルール：**
>
> * 新規の処理・表示は **`brief` / `detailed` を使う**
> * `reason` / `*_explanation` は「旧CSVを読み取るための互換用」として残している
> * 書き出し側（`scoring_pipeline`）は `brief` / `detailed` を主に書き、互換のために上記にコピーを入れる

---

### 1-3. 回答本文

| 概念   | カラム名          | 備考                             |
| ---- | ------------- | ------------------------------ |
| 回答本文 | `answer`      | 既存の一部パイプラインで使用                 |
| 回答本文 | `answer_text` | 新規ではこちらを推奨。`ai_likeness` などで使用 |

> **方針：**
> 将来的には **`answer_text` に統一**していく。
> 今は `answer` と `answer_text` の両方が存在するため、`feature_aggregator` などで吸収する。

---

### 1-4. 類似度系（AI参照・peer）

**AI模範解答との類似度**

| カラム名             | 説明          |
| ---------------- | ----------- |
| `sim_to_ai_max`  | AI参照との最大類似度 |
| `sim_to_ai_mean` | AI参照との平均類似度 |
| `ai_ref_best_id` | 最も近いAI参照のID |

**受験者同士（peer）類似度**

| カラム名                      | 説明                      |
| ------------------------- | ----------------------- |
| `sim_to_others_max`       | 他の受験者との最大類似度            |
| `sim_to_others_mean`      | 他の受験者との平均類似度            |
| `most_similar_student_id` | 最も似ている受験者の `student_id` |


---

### 1-5. 記号的特徴・テンプレ・AI疑惑

**記号的特徴**

| カラム名                | 説明                  |
| ------------------- | ------------------- |
| `symbolic_ai_score` | 記号的に見たときの「AIっぽさ」スコア |

**クラスタ・テンプレ度**

| カラム名                   | 説明                 |
| ---------------------- | ------------------ |
| `ai_template_likeness` | クラスタごとの「AIテンプレっぽさ」 |
| `summary` / `comment`  | クラスタの要約とコメント（内部用）  |

> 外部向けに出すときは `cluster_summary` / `cluster_comment` などにリネームすると混乱しにくい。

**AI疑惑（ai-likeness）**

*per question（受験者×設問）*

| カラム名                  | 説明                |
| --------------------- | ----------------- |
| `ai_likeness_score`   | その設問のAIっぽさ（統合スコア） |
| `ai_likeness_comment` | そのスコアに対するコメント     |
| `answer_text`         | その設問の回答本文         |

*per student（final_report での集約）*

| カラム名               | 説明                              |
| ------------------ | ------------------------------- |
| `ai_likeness_mean` | 受験者ごとの `ai_likeness_score` の平均  |
| `ai_likeness_max`  | 受験者ごとの `ai_likeness_score` の最大値 |
| `ai_suspect_flag`  | 「怪しい」と判定されたかどうか（0/1）            |

---

## 2. 各パイプラインと出力ファイル

### 2-1. 前処理：`preprocess`

**コマンド**

```bash
python -m src.steam_report_grader.cli preprocess
```

**主な処理**

* docx 形式の答案ファイルを読み込み
* 各受験者・各設問の回答を抽出
* 匿名IDを振る
* 回答Excelと ID マップを出力

**入力**

* `data/inputs/docx/*.docx` など

**出力**

1. 回答Excel
   `data/outputs/excel/steam_exam_responses.xlsx`

   | カラム名         | 説明         |
   | ------------ | ---------- |
   | `student_id` | 匿名ID       |
   | `Q1`〜`Qn`    | 各設問の回答テキスト |

2. IDマップ
   `data/outputs/excel/steam_exam_id_map.xlsx`（`id_map` シート）

   | カラム名          | 説明           |
   | ------------- | ------------ |
   | `student_id`  | 匿名ID         |
   | `real_name`   | 実名           |
   | `source_file` | 元 Word ファイル名 |

---

### 2-2. 絶対評価：`score`

**コマンド**

```bash
python -m src.steam_report_grader.cli score --model gpt-oss:20b
```

**主な処理**

* `steam_exam_responses.xlsx` を読み込み
* 各設問ごとに LLM に回答を渡して採点
* スレッドプール（例: max_workers=4）で並列化
* 簡易／詳細講評・エビデンス・サブスコアを含む `absolute_scores.csv` を出力

**入力**

* 回答Excel：`data/outputs/excel/steam_exam_responses.xlsx`
* ルーブリック：`data/inputs/rubrics/*.yaml` など

**出力**

* 絶対評価結果：`data/intermediate/features/absolute_scores.csv`

  主要カラム：

  | カラム名                   | 説明                     |
  | ---------------------- | ---------------------- |
  | `student_id`           | 受験者ID                  |
  | `question`             | 設問ラベル（`"Q1"` など）       |
  | `score`                | 絶対評価スコア                |
  | `brief`                | 簡易講評（通常は bullet 要約を結合） |
  | `detailed`             | 詳細講評（長文）               |
  | `summary_bullets`      | 箇条書き要約（文字列）            |
  | `reason`               | `brief` のコピー（互換用）      |
  | `brief_explanation`    | 同上                     |
  | `detailed_explanation` | `detailed` のコピー（互換用）   |
  | `evidence`             | 引用・根拠の JSON 文字列        |
  | `raw_response`         | LLM の生の返答              |
  | `sub_*`                | ルーブリック観点別スコア           |

---

### 2-3. 説明付きExcel：`explain`

**コマンド**

```bash
python -m src.steam_report_grader.cli explain
```

**主な処理**

1. `absolute_scores.csv` を読み込む
2. 列名を正規化：

   * `brief` / `detailed` が無ければ `reason` / `*_explanation` から補完
3. `evidence` JSON を展開し、`evidence_1_quote` などの列に展開
4. `id_map.xlsx` と `student_id` で結合
5. 2つのビューを作成：

   * **briefビュー**：簡易講評 + 主要 evidence まとめ
   * **detailedビュー**：詳細講評
6. `excel_writer.write_score_explanations_excel` で Excel 出力

**出力**

* 説明付きスコアExcel：`data/outputs/excel/absolute_scores_explanations.xlsx`（例）

  * シート `brief`：

    | カラム名           | 説明                 |
    | -------------- | ------------------ |
    | `student_id`   | 受験者ID              |
    | `real_name`    | 実名                 |
    | `source_file`  | 元ファイル名             |
    | `question`     | 設問                 |
    | `score`        | スコア                |
    | `brief`        | 簡易講評               |
    | `key_evidence` | evidence から組み立てた要約 |

  * シート `detailed`：

    | カラム名          | 説明     |
    | ------------- | ------ |
    | `student_id`  | 受験者ID  |
    | `real_name`   | 実名     |
    | `source_file` | 元ファイル名 |
    | `question`    | 設問     |
    | `score`       | スコア    |
    | `detailed`    | 詳細講評   |

---

### 2-4. 類似度系：AI参照 & peer

#### AI参照との類似度：`ai-similarity`

**出力**：`data/intermediate/features/ai_similarity.csv`

| カラム名             | 説明            |
| ---------------- | ------------- |
| `student_id`     | 受験者ID         |
| `question`       | 設問            |
| `sim_to_ai_max`  | AI参照との最大類似度   |
| `sim_to_ai_mean` | AI参照との平均類似度   |
| `ai_ref_best_id` | 最も類似したAI参照のID |

---

#### 受験者同士の類似度：`peer-similarity`

**出力**：`data/intermediate/features/peer_similarity_per_student.csv`

| カラム名                      | 説明                      |
| ------------------------- | ----------------------- |
| `student_id`              | 受験者ID                   |
| `question`                | 設問                      |
| `sim_to_others_max`       | 他の受験者との最大類似度            |
| `most_similar_student_id` | 最も似ている受験者の `student_id` |
| `sim_to_others_mean`      | 他の受験者との平均類似度            |

---

#### 記号的特徴：`symbolic-features`

**出力**：`data/intermediate/features/symbolic_features.csv`

| カラム名                | 説明                           |
| ------------------- | ---------------------------- |
| `student_id`        | 受験者ID                        |
| `question`          | 設問                           |
| `symbolic_ai_score` | 記号的な AIっぽさのスコア               |
| `answer`            | 回答本文（今後 `answer_text` へ統一予定） |

---

### 2-5. AI疑惑統合：`ai-likeness`

**コマンド**

```bash
python -m src.steam_report_grader.cli ai-likeness --model gpt-oss:20b
```

**主な処理**

* `ai_similarity`, `peer_similarity`, `symbolic_features`, 回答Excel などを統合
* 各受験者×設問ごとに

  * AI参照類似度
  * peer 類似度
  * 記号的特徴
    をまとめて LLM に渡し、「AIっぽさ」を判定させる
* スコアとコメントを `ai_likeness.csv` として出力

**出力**：`data/intermediate/features/ai_likeness.csv`

| カラム名                  | 説明        |
| --------------------- | --------- |
| `student_id`          | 受験者ID     |
| `question`            | 設問        |
| `ai_likeness_score`   | AIっぽさのスコア |
| `ai_likeness_comment` | 判定理由のコメント |
| `answer_text`         | 回答本文      |

---

### 2-6. 最終レポート：`final-report`

**コマンド**

```bash
python -m src.steam_report_grader.cli final-report \
  --scores-csv data/intermediate/features/absolute_scores.csv \
  --id-map data/outputs/excel/steam_exam_id_map.xlsx \
  --output-dir data/outputs/final \
  --log-path logs/final_report.log
```

**主な処理**

1. `absolute_scores.csv` + `id_map.xlsx` から
   1行=1受験者の `final_df` を構築

   * `total_score`, `mean_score`, `rank` を計算
2. `ai_likeness.csv` を per student に集約して `final_df` にマージ

   * `ai_likeness_mean`, `ai_likeness_max`, `ai_suspect_flag`
3. `ranking.csv` と `final_report.xlsx` を出力
4. 各受験者ごとに md / docx のフィードバックを生成

**出力1：`ranking.csv`**

`data/outputs/final/ranking.csv`

| カラム名               | 説明               |
| ------------------ | ---------------- |
| `student_id`       | 受験者ID            |
| `real_name`        | 実名               |
| `source_file`      | 元ファイル名           |
| `total_score`      | 総合点              |
| `mean_score`       | 平均点              |
| `num_questions`    | 解答した設問数          |
| `rank`             | 順位（総合点降順）        |
| `ai_likeness_mean` | AI疑惑スコア平均        |
| `ai_likeness_max`  | AI疑惑スコア最大値       |
| `ai_suspect_flag`  | AI疑惑フラグ（閾値以上で 1） |
| `score_Q*` など      | 各設問の得点（あれば）      |

**出力2：`final_report.xlsx`**

`data/outputs/final/final_report.xlsx`

* シート `ranking`
  → `ranking.csv` と同じ内容

* シート `by_student_question`

  | カラム名                  | 説明                |
  | --------------------- | ----------------- |
  | `student_id`          | 受験者ID             |
  | `real_name`           | 実名                |
  | `source_file`         | 元ファイル名            |
  | `question`            | 設問                |
  | `score`               | 設問ごとのスコア          |
  | `brief`               | 簡易講評（短め）          |
  | `detailed`            | 詳細講評（長め）          |
  | `ai_likeness_score`   | 設問ごとのAI疑惑スコア      |
  | `ai_likeness_comment` | その設問のAI疑惑に関するコメント |

**出力3：個別フィードバック（md / docx）**

* `data/outputs/final/feedback/md/feedback_{student_id}.md`
* `data/outputs/final/feedback/docx/feedback_{student_id}.docx`

構成（md版）：

```markdown
# {real_name} さん (ID: {student_id})

- 総合点: {total_score}
- 順位: {rank} / {num_students}

## Q1 の講評（{score} 点）

### 講評（簡易）
{brief}

### 講評（詳細）
{detailed}

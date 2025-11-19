import sys
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import scrolledtext, messagebox

import requests


# ─────────────────────────
# パイプライン定義（コマンド名だけ）
# ─────────────────────────
PIPELINE_STEPS: list[list[str]] = [
    ["preprocess"],
    ["score"],
    ["relative-features", "--log-path", "logs/relative_features.log"],
    ["relative-ranking", "--log-path", "logs/relative_ranking.log"],
    ["summary"],
    ["explain"],
    ["import-all-ai-ref"],
    ["ai-similarity"],
    ["ai-cluster"],
    ["peer-similarity"],
    ["symbolic-features"],
    ["ai-likeness"],
    ["ai-report"],
    [
        "final-report",
        "--scores-csv",
        "data/intermediate/features/absolute_scores.csv",
        "--id-map",
        "data/outputs/excel/steam_exam_id_map.xlsx",
        "--output-dir",
        "data/outputs/final",
        "--log-path",
        "logs/final_report.log",
    ],
    ["translate-reports"],
]

# 推奨モデル（存在すればこれを優先的に使う）
RECOMMENDED_SCORING_MODEL = "gpt-oss:20b"
RECOMMENDED_TRANS_MODEL = "gemma3:12b"


class SteamReportGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("STEAM Report Grader GUI")

        # プロジェクトルート = この run_gui.py があるディレクトリ
        self.project_root = Path(__file__).resolve().parent

        # 実行フラグ
        self._running = False

        # 利用可能モデル一覧（起動時に Ollama から取得）
        self.available_models: list[str] = []

        # ── LLM / モデル選択 UI ──────────────────────
        top_frame = tk.Frame(root)
        top_frame.pack(pady=4)

        # Provider
        tk.Label(top_frame, text="LLM Provider:").grid(row=0, column=0, sticky="w")
        self.llm_provider_var = tk.StringVar(value="ollama")
        tk.Entry(top_frame, textvariable=self.llm_provider_var, width=12).grid(
            row=0, column=1, sticky="w"
        )

        # 採点 / AI疑惑 用モデル
        tk.Label(top_frame, text="採点 / AI疑惑モデル:").grid(row=1, column=0, sticky="w")
        self.scoring_model_var = tk.StringVar(value="")
        self.scoring_model_menu = tk.OptionMenu(top_frame, self.scoring_model_var, "")
        self.scoring_model_menu.grid(row=1, column=1, sticky="w")

        # 翻訳 用モデル
        tk.Label(top_frame, text="翻訳モデル:").grid(row=2, column=0, sticky="w")
        self.trans_model_var = tk.StringVar(value="")
        self.trans_model_menu = tk.OptionMenu(top_frame, self.trans_model_var, "")
        self.trans_model_menu.grid(row=2, column=1, sticky="w")

        # モデル再読込ボタン
        self.reload_button = tk.Button(
            top_frame,
            text="Ollamaモデル再読込",
            command=self.on_reload_models_clicked,
        )
        self.reload_button.grid(row=1, column=2, rowspan=2, padx=8)

        # ── 開始ステップ選択 ────────────────────
        self.start_from_var = tk.IntVar(value=1)
        start_frame = tk.Frame(root)
        start_frame.pack(pady=4)

        tk.Label(start_frame, text="開始ステップ (1〜{}):".format(len(PIPELINE_STEPS))).pack(
            side=tk.LEFT
        )

        tk.Spinbox(
            start_frame,
            from_=1,
            to=len(PIPELINE_STEPS),
            textvariable=self.start_from_var,
            width=5,
        ).pack(side=tk.LEFT, padx=4)

        # ── 実行ボタン ─────────────────────────
        self.run_button = tk.Button(
            root,
            text="全部まとめて実行",
            command=self.on_run_all_clicked,
            width=30,
        )
        self.run_button.pack(pady=8)

        # ── ログ表示 ───────────────────────────
        self.log_widget = scrolledtext.ScrolledText(root, width=100, height=30)
        self.log_widget.pack(padx=8, pady=4)

        # ステータスバー
        self.status_var = tk.StringVar(value="待機中")
        status_bar = tk.Label(root, textvariable=self.status_var, anchor="w")
        status_bar.pack(fill=tk.X, padx=4, pady=2)

        # 起動時に一度モデル一覧読み込み
        self.reload_models(initial=True)

    # ─────────────────────────
    # Ollama モデル取得 & OptionMenu 更新
    # ─────────────────────────
    def fetch_ollama_models(self) -> list[str]:
        """
        Ollama の /api/tags からモデル一覧を取得。
        失敗したら空リストを返す。
        """
        base_url = "http://127.0.0.1:11434"
        try:
            resp = requests.get(base_url.rstrip("/") + "/api/tags", timeout=3)
            resp.raise_for_status()
            data = resp.json()
            models = [m.get("name") for m in data.get("models", []) if m.get("name")]
            models = sorted(set(models))
            return models
        except Exception as e:  # noqa: BLE001
            self.append_log(f"[WARN] Ollamaモデル一覧の取得に失敗しました: {e}")
            return []

    def reload_models(self, initial: bool = False) -> None:
        models = self.fetch_ollama_models()

        if not models:
            # 何も取れなかった時のフォールバック
            if not initial and self.available_models:
                # すでに前回取得したものがあるなら維持
                self.append_log("[INFO] 前回取得したモデル一覧を継続利用します。")
                models = self.available_models
            else:
                self.append_log(
                    "[INFO] Ollamaモデルが取得できなかったため、デフォルト候補を使用します。"
                )
                # フォールバックにも推奨モデルを含めておく
                models = ["gpt-oss:20b", "qwen3:8b", "qwen3:30b"]

        # 重複なし & ソート
        models = sorted(set(models))

        # 推奨モデルを先頭に寄せる（存在する場合だけ）
        def reorder_with_preferences(
            items: list[str],
            preferred: list[str],
        ) -> list[str]:
            ordered: list[str] = []
            for p in preferred:
                if p in items and p not in ordered:
                    ordered.append(p)
            for m in items:
                if m not in ordered:
                    ordered.append(m)
            return ordered

        models = reorder_with_preferences(
            models,
            [RECOMMENDED_SCORING_MODEL, RECOMMENDED_TRANS_MODEL],
        )

        self.available_models = models

        # OptionMenu の中身を更新
        def update_menu(
            menu_widget: tk.OptionMenu,
            var: tk.StringVar,
            preferred_default: str | None = None,
        ) -> None:
            menu = menu_widget["menu"]
            menu.delete(0, "end")

            for m in self.available_models:
                menu.add_command(
                    label=m,
                    command=lambda v=m: var.set(v),
                )

            cur = var.get().strip()

            # 初回起動時: 推奨モデルが存在すればそれをセット
            if initial and preferred_default and preferred_default in self.available_models:
                var.set(preferred_default)
                return

            # それ以外: 現在値がまだ有効ならそれを維持
            if cur in self.available_models:
                var.set(cur)
                return

            # どれもダメなら先頭
            var.set(self.available_models[0])

        update_menu(
            self.scoring_model_menu,
            self.scoring_model_var,
            preferred_default=RECOMMENDED_SCORING_MODEL,
        )
        update_menu(
            self.trans_model_menu,
            self.trans_model_var,
            preferred_default=RECOMMENDED_TRANS_MODEL,
        )

        self.append_log(
            "[INFO] 利用可能なモデル: " + ", ".join(self.available_models)
        )

    def on_reload_models_clicked(self) -> None:
        self.reload_models(initial=False)

    # ─────────────────────────
    # コマンド生成
    # ─────────────────────────
    def build_commands(self) -> list[list[str]]:
        """
        GUI の設定値から、実際に叩く CLI コマンド列を組み立てる。
        """
        commands: list[list[str]] = []
        provider = self.llm_provider_var.get().strip() or "ollama"
        score_model = self.scoring_model_var.get().strip()
        trans_model = self.trans_model_var.get().strip()

        for step in PIPELINE_STEPS:
            base = step[0]
            args = step[1:]

            cmd: list[str] = [base]
            cmd.extend(args)

            # LLM を使うコマンドに --model / --llm-provider を付与
            if base in {"score", "ai-cluster", "ai-likeness"}:
                cmd.extend(
                    [
                        "--model",
                        score_model,
                        "--llm-provider",
                        provider,
                    ]
                )
            elif base == "translate-reports":
                cmd.extend(
                    [
                        "--model",
                        trans_model,
                        "--llm-provider",
                        provider,
                    ]
                )

            commands.append(cmd)

        return commands

    # ─────────────────────────
    # ログ出力
    # ─────────────────────────
    def append_log(self, text: str) -> None:
        self.log_widget.insert(tk.END, text + "\n")
        self.log_widget.see(tk.END)

    def set_status(self, text: str) -> None:
        self.status_var.set(text)

    # ─────────────────────────
    # 実行スレッド
    # ─────────────────────────
    def run_pipeline_thread(self, start_index: int) -> None:
        """
        バックグラウンドで CLI を順番に実行する。
        """
        try:
            commands = self.build_commands()
            total = len(commands)
            # 1-based → 0-based に正規化
            idx = max(1, min(start_index, total)) - 1

            for i in range(idx, total):
                step_cmd = commands[i]
                step_name = step_cmd[0]

                # ステータスバー用
                self.set_status(f"実行中: [{i+1}/{total}] {step_name}")

                # ログ用ヘッダ（昔と同じ [i/n] 形式）
                step_label = f"[{i+1}/{total}] {' '.join(step_cmd)}"
                self.append_log(f"\n=== {step_label} ===")

                # 実際に叩くコマンド
                full_cmd = [
                    sys.executable,
                    "-m",
                    "src.steam_report_grader.cli",
                ] + step_cmd

                proc = subprocess.Popen(
                    full_cmd,
                    cwd=self.project_root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )

                assert proc.stdout is not None
                for line in proc.stdout:
                    self.append_log(line.rstrip("\n"))

                ret = proc.wait()
                if ret != 0:
                    self.append_log(f"[ERROR] コマンドが異常終了しました (exit={ret})")
                    messagebox.showerror(
                        "エラー",
                        f"コマンドが異常終了しました:\n{' '.join(full_cmd)}\nexit={ret}",
                    )
                    break

            self.set_status("完了")
        finally:
            self._running = False
            self.run_button.config(state=tk.NORMAL)

    # ─────────────────────────
    # ボタンハンドラ
    # ─────────────────────────
    def on_run_all_clicked(self) -> None:
        if self._running:
            return

        try:
            start_index = int(self.start_from_var.get())
        except Exception:
            start_index = 1

        self._running = True
        self.run_button.config(state=tk.DISABLED)
        self.set_status("実行中...")

        t = threading.Thread(
            target=self.run_pipeline_thread,
            args=(start_index,),
            daemon=True,
        )
        t.start()


def main() -> None:
    root = tk.Tk()
    app = SteamReportGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

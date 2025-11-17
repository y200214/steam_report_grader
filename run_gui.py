import sys
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import scrolledtext, messagebox


# ─────────────────────────
# 設定：実行する CLI コマンド列
# ─────────────────────────
# いつも PowerShell で叩いてるのと同じ順番
COMMANDS: list[list[str]] = [
    ["preprocess"],
    ["score", "--model", "gpt-oss:20b"],
    ["summary"],
    ["explain"],
    ["import-all-ai-ref"],
    ["ai-similarity"],
    ["ai-cluster", "--model", "gpt-oss:20b"],
    ["peer-similarity"],
    ["symbolic-features"],
    ["ai-likeness", "--model", "gpt-oss:20b"],
    ["ai-report"],
    ["translate-reports", "--model", "gpt-oss:20b"],
    [
        "final-report",
        "--scores-csv", "data/intermediate/features/absolute_scores.csv",
        "--id-map", "data/outputs/excel/steam_exam_id_map.xlsx",
        "--output-dir", "data/outputs/final",
        "--log-path", "logs/final_report.log",
    ],
]


# ─────────────────────────
# CLI 呼び出しヘルパー
# ─────────────────────────
def run_cli_subcommand(
    project_root: Path,
    subcommand_args: list[str],
) -> tuple[int, str]:
    """
    例:
        run_cli_subcommand(root, ["preprocess"])
        run_cli_subcommand(root, ["score", "--model", "gpt-oss:20b"])
    戻り値:
        (returncode, stdout+stderr の文字列)
    """
    cmd = [sys.executable, "-m", "src.steam_report_grader.cli", *subcommand_args]

    result = subprocess.run(
        cmd,
        cwd=project_root,
        text=True,
        capture_output=True,
    )

    output = f"$ {' '.join(cmd)}\n"
    output += result.stdout
    if result.stderr:
        output += "\n[stderr]\n" + result.stderr

    return result.returncode, output


# ─────────────────────────
# GUI 関連
# ─────────────────────────
class SteamReportGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("STEAM Report Grader GUI (簡易版)")

        # プロジェクトルート = この run_gui.py があるディレクトリ
        self.project_root = Path(__file__).resolve().parent

        # ボタン
        self.run_button = tk.Button(
            root,
            text="全部まとめて実行",
            command=self.on_run_all_clicked,
            width=30,
        )
        self.run_button.pack(pady=8)
        self.start_from_var = tk.IntVar(value=1)
        start_frame = tk.Frame(root)
        start_frame.pack(pady=4)

        tk.Label(start_frame, text="開始ステップ:").pack(side=tk.LEFT)

        tk.Spinbox(
            start_frame,
            from_=1,
            to=len(COMMANDS),
            textvariable=self.start_from_var,
            width=5,
        ).pack(side=tk.LEFT, padx=4)

        # ログ表示エリア
        self.log_widget = scrolledtext.ScrolledText(
            root,
            wrap=tk.WORD,
            width=100,
            height=30,
        )
        self.log_widget.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # ステータスラベル
        self.status_var = tk.StringVar(value="待機中")
        self.status_label = tk.Label(root, textvariable=self.status_var)
        self.status_label.pack(pady=(0, 8))

        self._running = False

        # ログ表示エリア
        self.log_widget = scrolledtext.ScrolledText(
            root,
            wrap=tk.WORD,
            width=100,
            height=30,
        )
        self.log_widget.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # ステータスラベル
        self.status_var = tk.StringVar(value="待機中")
        self.status_label = tk.Label(root, textvariable=self.status_var)
        self.status_label.pack(pady=(0, 8))

        self._running = False

    def append_log(self, text: str) -> None:
        self.log_widget.insert(tk.END, text + "\n")
        self.log_widget.see(tk.END)  # 常に末尾にスクロール

    def set_status(self, text: str) -> None:
        self.status_var.set(text)

    def on_run_all_clicked(self) -> None:
        if self._running:
            return

        self._running = True
        self.run_button.config(state=tk.DISABLED)
        self.set_status("実行中...")

        start_index = int(self.start_from_var.get())
        if not (1 <= start_index <= len(COMMANDS)):
            messagebox.showerror("エラー", "開始ステップの値が不正です。")
            self._running = False
            self.run_button.config(state=tk.NORMAL)
            self.set_status("待機中")
            return

        # バックグラウンドスレッドで CLI を順に叩く
        thread = threading.Thread(
            target=self._run_all_commands,
            args=(start_index,),
            daemon=True,
        )
        thread.start()


    def _run_all_commands(self, start_index: int = 1) -> None:
        try:
            # COMMANDS[start_index-1:] だけを回す
            for i, args in enumerate(COMMANDS[start_index-1:], start=start_index):
                step_label = f"[{i}/{len(COMMANDS)}] {' '.join(args)}"
                self.root.after(
                    0, lambda s=step_label: self.append_log(f"\n=== {s} ===")
                )

                code, out = run_cli_subcommand(self.project_root, args)

                # ログ追加
                self.root.after(0, lambda o=out: self.append_log(o))

                if code != 0:
                    # 失敗したのでここで止める
                    msg = f"コマンドがエラーで終了しました (exit code={code}): {' '.join(args)}"
                    self.root.after(
                        0,
                        lambda m=msg: messagebox.showerror("エラー", m),
                    )
                    self.root.after(
                        0,
                        lambda: self.set_status("エラーで停止しました"),
                    )
                    return

            # 全ステップ成功
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "完了", "全ステップの実行が完了しました。"
                ),
            )
            self.root.after(0, lambda: self.set_status("完了"))
        finally:
            # ボタンを元に戻す
            self._running = False
            self.root.after(0, lambda: self.run_button.config(state=tk.NORMAL))


def main() -> None:
    root = tk.Tk()
    app = SteamReportGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

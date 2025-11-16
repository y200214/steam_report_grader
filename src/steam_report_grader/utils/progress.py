# src/steam_report_grader/utils/progress.py
from contextlib import contextmanager
from typing import Iterable, Iterator
import sys

def simple_progress(iterable: Iterable, total: int | None = None, prefix: str = "") -> Iterator:
    """
    依存ライブラリを増やしたくないので、超シンプルな進捗表示。
    """
    if total is None:
        try:
            total = len(iterable)  # type: ignore[arg-type]
        except Exception:
            total = None

    for i, item in enumerate(iterable, start=1):
        if total:
            msg = f"{prefix}{i}/{total}\r"
        else:
            msg = f"{prefix}{i}\r"
        sys.stdout.write(msg)
        sys.stdout.flush()
        yield item
    sys.stdout.write("\n")

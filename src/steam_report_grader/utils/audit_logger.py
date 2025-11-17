# src/steam_report_grader/utils/audit_logger.py
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional
from datetime import datetime
from zoneinfo import ZoneInfo

def _to_serializable(obj: Any) -> Any:
    """
    auditログに突っ込むための簡易シリアライザ。
    dataclass → dict、それ以外はそのまま or 文字列化。
    """
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, Mapping):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_serializable(v) for v in obj]
    return str(obj)


def log_audit_record(
    command: str,
    args: Optional[Mapping[str, Any]] = None,
    extra: Optional[Mapping[str, Any]] = None,
    status: str = "success",
    audit_path: Path | str = Path("data/outputs/audit_log.jsonl"),
) -> None:
    """
    1コマンドぶんの実行情報を audit_log.jsonl に1行追記する。

    - command: 実行したサブコマンド名 (例: "score", "ai-likeness", "final-report")
    - args: CLI 引数 (dict にして渡す)
    - extra: LLM設定など追加メタ情報
    - status: "success" / "error" など
    """
    audit_path = Path(audit_path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    record: dict[str, Any] = {
        "timestamp": datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds"),
        "command": command,
        "status": status,
    }

    if args is not None:
        record["args"] = _to_serializable(dict(args))

    if extra is not None:
        record["extra"] = _to_serializable(dict(extra))

    with audit_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

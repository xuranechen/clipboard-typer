"""输入历史记录：保存最近 N 条输入摘要，不存敏感内容。"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

HISTORY_PATH = Path("history.json")
MAX_HISTORY = 50
PREVIEW_LEN = 80


@dataclass
class HistoryEntry:
    preview: str = ""
    length: int = 0
    timestamp: float = field(default_factory=time.time)


def load_history(path: Path = HISTORY_PATH) -> list[HistoryEntry]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [HistoryEntry(**item) for item in data]


def save_history(entries: list[HistoryEntry], path: Path = HISTORY_PATH) -> None:
    path.write_text(
        json.dumps([asdict(e) for e in entries], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def add_history(text: str, entries: list[HistoryEntry]) -> list[HistoryEntry]:
    """添加一条历史记录。只保存前 PREVIEW_LEN 个字符作为摘要。"""
    preview = text.strip().replace("\r\n", "\n").replace("\r", "\n")
    preview = preview[:PREVIEW_LEN].replace("\n", "↵")
    if not preview:
        return entries
    entry = HistoryEntry(preview=preview, length=len(text), timestamp=time.time())
    entries.insert(0, entry)
    if len(entries) > MAX_HISTORY:
        entries = entries[:MAX_HISTORY]
    return entries


def clear_history(path: Path = HISTORY_PATH) -> None:
    save_history([], path)

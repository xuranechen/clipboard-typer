"""版本信息模块。

本地开发时使用默认值，CI 构建时由 GitHub Actions 注入。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# CI 构建时通过环境变量注入，本地开发时使用默认值
import os

VERSION = os.environ.get("CLIPBOARD_TYPER_VERSION", "0.6.0-dev")
BUILD_DATE = os.environ.get("CLIPBOARD_TYPER_BUILD_DATE", "")
COMMIT_SHA = os.environ.get("CLIPBOARD_TYPER_COMMIT_SHA", "")


def get_version_string() -> str:
    """返回显示用的版本字符串。"""
    ver = VERSION.lstrip("v")
    if ver != "dev" and not ver.endswith("-dev"):
        return ver
    if ver.endswith("-dev"):
        sha = _get_git_sha()
        return f"{ver}-{sha}"
    sha = _get_git_sha()
    date = _get_build_date()
    return f"dev-{date}-{sha}"


def get_full_info() -> str:
    """返回完整的版本+构建信息。"""
    parts = [get_version_string()]
    if BUILD_DATE:
        parts.append(f"构建于 {BUILD_DATE}")
    if COMMIT_SHA:
        parts.append(f"commit {COMMIT_SHA[:7]}")
    return " | ".join(parts)


def _get_git_sha() -> str:
    if COMMIT_SHA:
        return COMMIT_SHA[:7]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd=Path(__file__).resolve().parent.parent,
        )
        if result.returncode == 0:
            return result.stdout.strip()[:7]
    except Exception:
        pass
    return "unknown"


def _get_build_date() -> str:
    if BUILD_DATE:
        return BUILD_DATE
    try:
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d")
    except Exception:
        pass
    return ""

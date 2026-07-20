from __future__ import annotations

import os
import platform


def platform_hint() -> str:
    system = platform.system().lower()
    if system == "windows":
        return "Windows：如果目标程序以管理员权限运行，本工具也可能需要管理员权限。"
    if system == "darwin":
        return "macOS：需要授予辅助功能和输入监控权限。"
    if system == "linux":
        session = os.environ.get("XDG_SESSION_TYPE", "").lower()
        if session == "wayland":
            return "Linux Wayland：可能限制键盘模拟，建议切换到 X11。"
        return "Linux：X11 通常可用，Wayland 可能受限。"
    return "当前平台未专门适配，请先在普通文本窗口测试。"

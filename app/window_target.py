"""窗口枚举、选择、激活与坐标拾取。"""

from __future__ import annotations

import time
import threading
from collections.abc import Callable
from dataclasses import dataclass

import pyautogui
import pygetwindow


@dataclass
class WindowInfo:
    hwnd: int
    title: str
    left: int
    top: int
    width: int
    height: int


@dataclass
class ClickPosition:
    """相对于目标窗口左上角的坐标。"""
    x: int
    y: int


def list_windows(min_width: int = 50, min_height: int = 50) -> list[WindowInfo]:
    """枚举当前桌面所有可见窗口。"""
    results: list[WindowInfo] = []
    for win in pygetwindow.getAllWindows():
        if not win.title or not win.title.strip():
            continue
        if win.width < min_width or win.height < min_height:
            continue
        try:
            results.append(WindowInfo(
                hwnd=win._hWnd,
                title=win.title,
                left=win.left,
                top=win.top,
                width=win.width,
                height=win.height,
            ))
        except Exception:
            continue
    return results


def find_window(title_keyword: str) -> WindowInfo | None:
    """按标题关键字查找第一个匹配的窗口。"""
    keyword = title_keyword.strip().lower()
    if not keyword:
        return None
    for info in list_windows():
        if keyword in info.title.lower():
            return info
    return None


def activate_window(info: WindowInfo) -> None:
    """激活并前台化窗口。"""
    wins = pygetwindow.getWindowsWithTitle(info.title)
    if not wins:
        raise RuntimeError(f"未找到窗口：{info.title}")
    win = wins[0]
    try:
        win.activate()
    except Exception:
        win.minimize()
        time.sleep(0.1)
        win.restore()
    time.sleep(0.3)


def click_at_window_position(info: WindowInfo, pos: ClickPosition) -> None:
    """在窗口内相对坐标位置执行鼠标左键点击。"""
    screen_x = info.left + pos.x
    screen_y = info.top + pos.y
    pyautogui.click(screen_x, screen_y)


def pick_position_relative_to_window(
    info: WindowInfo,
    callback: Callable[[ClickPosition], None],
    on_status: Callable[[str], None] | None = None,
    delay_seconds: int = 3,
) -> None:
    """倒计时后读取鼠标位置，计算相对目标窗口的坐标。"""
    def _worker() -> None:
        for remaining in range(delay_seconds, 0, -1):
            if on_status:
                on_status(f"{remaining} 秒后拾取坐标，请将鼠标移到目标位置...")
            time.sleep(1)
        x, y = pyautogui.position()
        rel_x = x - info.left
        rel_y = y - info.top
        rel_x = max(0, min(rel_x, info.width))
        rel_y = max(0, min(rel_y, info.height))
        callback(ClickPosition(rel_x, rel_y))
        if on_status:
            on_status(f"已拾取坐标：({rel_x}, {rel_y})")

    threading.Thread(target=_worker, daemon=True).start()

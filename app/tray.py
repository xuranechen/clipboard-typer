"""系统托盘管理。"""

from __future__ import annotations

import threading
from collections.abc import Callable

import pystray
from PIL import Image, ImageDraw


def create_tray_icon(on_show: Callable[[], None], on_quit: Callable[[], None]) -> pystray.Icon:
    """创建系统托盘图标。"""
    image = _create_default_image()
    menu = pystray.Menu(
        pystray.MenuItem("显示主窗口", on_show, default=True),
        pystray.MenuItem("退出", on_quit),
    )
    icon = pystray.Icon("ClipboardTyper", image, "Clipboard Typer", menu)
    return icon


def run_tray(icon: pystray.Icon) -> threading.Thread:
    """在后台线程运行托盘图标。"""
    thread = threading.Thread(target=icon.run, daemon=True)
    thread.start()
    return thread


def _create_default_image() -> Image.Image:
    """生成一个简单的默认图标。"""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([8, 8, 56, 56], radius=8, fill=(52, 120, 246, 255))
    draw.text((18, 16), "CT", fill=(255, 255, 255, 255))
    return img

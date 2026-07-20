from __future__ import annotations

import threading
import time
from collections.abc import Callable

import pyautogui

from app.config import AppConfig

ProgressCallback = Callable[[int, int], None]
StatusCallback = Callable[[str], None]


class ClipboardTyper:
    def __init__(self, config: AppConfig):
        self.config = config
        self.stop_event = threading.Event()
        self.typing = False

    def update_config(self, config: AppConfig) -> None:
        self.config = config

    def stop(self) -> None:
        self.stop_event.set()

    def preprocess(self, text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        allowed = []
        for ch in text:
            if ch in {"\n", "\t"} or ch >= " ":
                allowed.append(ch)
        return "".join(allowed)

    def type_text(
        self,
        text: str,
        progress_callback: ProgressCallback | None = None,
        status_callback: StatusCallback | None = None,
    ) -> bool:
        if self.typing:
            raise RuntimeError("正在输入中")

        self.stop_event.clear()
        processed = self.preprocess(text)
        total = len(processed)
        self.typing = True
        started = time.monotonic()
        try:
            delay_seconds = self.config.start_delay_ms // 1000
            for remaining in range(delay_seconds, 0, -1):
                if self.stop_event.is_set():
                    _status(status_callback, "已停止")
                    return False
                _status(status_callback, f"{remaining} 秒后开始，请切换到目标窗口")
                time.sleep(1)

            leftover_ms = self.config.start_delay_ms % 1000
            if leftover_ms:
                time.sleep(leftover_ms / 1000)

            _status(status_callback, f"正在输入 0 / {total}")
            char_delay = self._effective_char_delay() / 1000
            line_delay = self._effective_line_delay() / 1000

            for index, ch in enumerate(processed, start=1):
                if self.stop_event.is_set():
                    _status(status_callback, f"已停止 {index - 1} / {total}")
                    return False
                self._type_char(ch)
                if progress_callback:
                    progress_callback(index, total)
                _status(status_callback, f"正在输入 {index} / {total}")
                time.sleep(line_delay if ch == "\n" else char_delay)

            elapsed = time.monotonic() - started
            _status(status_callback, f"输入完成，用时 {elapsed:.1f} 秒")
            return True
        finally:
            self.typing = False

    def _type_char(self, ch: str) -> None:
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                if ch == "\n":
                    pyautogui.press("enter")
                elif ch == "\t":
                    if self.config.tab_policy == "tab":
                        pyautogui.press("tab")
                    elif self.config.tab_policy == "spaces":
                        pyautogui.write(" " * self.config.tab_spaces)
                else:
                    pyautogui.write(ch)
                return
            except Exception as exc:
                last_error = exc
                time.sleep(0.05 * (attempt + 1))
        raise RuntimeError(f"键盘输入失败：{last_error}") from last_error

    def _effective_char_delay(self) -> int:
        if self.config.input_mode == "fast":
            return max(0, min(self.config.char_delay_ms, 5))
        if self.config.input_mode == "slow":
            return max(self.config.char_delay_ms, 100)
        if self.config.input_mode == "line":
            return self.config.char_delay_ms
        return self.config.char_delay_ms

    def _effective_line_delay(self) -> int:
        if self.config.input_mode == "fast":
            return max(0, min(self.config.line_delay_ms, 20))
        if self.config.input_mode == "slow":
            return max(self.config.line_delay_ms, 250)
        if self.config.input_mode == "line":
            return max(self.config.line_delay_ms, 500)
        return self.config.line_delay_ms


def _status(callback: StatusCallback | None, message: str) -> None:
    if callback:
        callback(message)

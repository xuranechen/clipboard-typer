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
        self.line_continue_event = threading.Event()
        self.typing = False

    def update_config(self, config: AppConfig) -> None:
        self.config = config

    def stop(self) -> None:
        self.stop_event.set()
        self.line_continue_event.set()

    def continue_next_line(self) -> None:
        self.line_continue_event.set()

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
            step_mode = self.config.input_mode == "step_by_step"
            adaptive = self.config.input_mode == "adaptive"
            if step_mode:
                self.line_continue_event.clear()
            retry_count = 0
            success_streak = 0

            for index, ch in enumerate(processed, start=1):
                if self.stop_event.is_set():
                    _status(status_callback, f"已停止 {index - 1} / {total}")
                    return False
                retries_before = self._type_char_with_retries(ch)
                if retries_before > 0:
                    retry_count += retries_before
                    success_streak = 0
                    if adaptive:
                        char_delay = min(char_delay * 1.5, 2.0)
                        line_delay = min(line_delay * 1.5, 3.0)
                        _status(status_callback, f"正在输入 {index} / {total} (自动放慢 {char_delay*1000:.0f}ms)")
                else:
                    success_streak += 1
                    if adaptive and success_streak > 20 and char_delay > self._effective_char_delay() / 1000:
                        char_delay = max(char_delay * 0.9, self._effective_char_delay() / 1000)
                        line_delay = max(line_delay * 0.9, self._effective_line_delay() / 1000)
                if progress_callback:
                    progress_callback(index, total)
                if ch == "\n" and step_mode:
                    _status(status_callback, f"已输入第 {index} / {total} 字符，等待确认继续...")
                    self.line_continue_event.clear()
                    self.line_continue_event.wait()
                    if self.stop_event.is_set():
                        _status(status_callback, f"已停止 {index} / {total}")
                        return False
                else:
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

    def _type_char_with_retries(self, ch: str) -> int:
        """输入单个字符，返回重试次数。用于 adaptive 模式。"""
        retries = 0
        last_error: Exception | None = None
        for attempt in range(3):
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
                return retries
            except Exception as exc:
                last_error = exc
                retries += 1
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

from __future__ import annotations

import pyperclip


class ClipboardError(RuntimeError):
    pass


def read_clipboard_text() -> str:
    try:
        text = pyperclip.paste()
    except pyperclip.PyperclipException as exc:
        raise ClipboardError(str(exc)) from exc
    if text is None:
        return ""
    return str(text)


def clear_clipboard() -> None:
    try:
        pyperclip.copy("")
    except pyperclip.PyperclipException as exc:
        raise ClipboardError(str(exc)) from exc

from __future__ import annotations

from collections.abc import Callable

from pynput import keyboard


class HotkeyManager:
    def __init__(self, hotkey: str, on_trigger: Callable[[], None], on_stop: Callable[[], None] | None = None):
        self.hotkey = hotkey
        self.on_trigger = on_trigger
        self.on_stop = on_stop
        self.listener: keyboard.GlobalHotKeys | None = None
        self.esc_listener: keyboard.Listener | None = None

    def start(self, enable_esc: bool = True) -> None:
        self.stop()
        combo = _to_pynput_hotkey(self.hotkey)
        self.listener = keyboard.GlobalHotKeys({combo: self.on_trigger})
        self.listener.start()
        if enable_esc and self.on_stop:
            self.esc_listener = keyboard.Listener(on_press=self._on_press)
            self.esc_listener.start()

    def stop(self) -> None:
        if self.listener:
            self.listener.stop()
            self.listener = None
        if self.esc_listener:
            self.esc_listener.stop()
            self.esc_listener = None

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        if key == keyboard.Key.esc and self.on_stop:
            self.on_stop()


def _to_pynput_hotkey(hotkey: str) -> str:
    parts = [part.strip().lower() for part in hotkey.replace("+", " ").split() if part.strip()]
    mapped = []
    for part in parts:
        if part in {"ctrl", "control"}:
            mapped.append("<ctrl>")
        elif part == "alt":
            mapped.append("<alt>")
        elif part == "shift":
            mapped.append("<shift>")
        elif part in {"cmd", "win", "super"}:
            mapped.append("<cmd>")
        else:
            mapped.append(part)
    return "+".join(mapped) or "<ctrl>+<alt>+v"

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

CONFIG_PATH = Path("config.json")


@dataclass
class AppConfig:
    start_delay_ms: int = 3000
    char_delay_ms: int = 50
    line_delay_ms: int = 150
    tab_policy: str = "spaces"
    tab_spaces: int = 4
    max_length: int = 10000
    confirm_before_type: bool = True
    show_preview: bool = True
    password_mode: bool = False
    clear_preview_after_type: bool = False
    clear_clipboard_after_type: bool = False
    hotkey: str = "ctrl+alt+v"
    enable_hotkey: bool = False
    esc_to_stop: bool = True
    input_mode: str = "normal"
    target_window_title: str = ""
    click_x: int = -1
    click_y: int = -1
    auto_activate_window: bool = False


PRESETS: dict[str, dict[str, int | str]] = {
    "local_fast": {"char_delay_ms": 5, "line_delay_ms": 20, "input_mode": "fast"},
    "vnc_stable": {"char_delay_ms": 50, "line_delay_ms": 150, "input_mode": "normal"},
    "web_console_slow": {"char_delay_ms": 80, "line_delay_ms": 200, "input_mode": "slow"},
    "ipmi_kvm_ultra_slow": {"char_delay_ms": 150, "line_delay_ms": 350, "input_mode": "slow"},
}


def load_config(path: Path = CONFIG_PATH) -> AppConfig:
    if not path.exists():
        config = AppConfig()
        save_config(config, path)
        return config
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        config = AppConfig()
        save_config(config, path)
        return config
    config = validate_config(data)
    save_config(config, path)
    return config


def save_config(config: AppConfig, path: Path = CONFIG_PATH) -> None:
    path.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")


def validate_config(data: dict[str, Any]) -> AppConfig:
    names = {field.name for field in fields(AppConfig)}
    cleaned = {key: value for key, value in data.items() if key in names}
    config = AppConfig(**cleaned)

    config.start_delay_ms = _clamp_int(config.start_delay_ms, 0, 60000, 3000)
    config.char_delay_ms = _clamp_int(config.char_delay_ms, 0, 5000, 50)
    config.line_delay_ms = _clamp_int(config.line_delay_ms, 0, 10000, 150)
    config.tab_spaces = _clamp_int(config.tab_spaces, 0, 16, 4)
    config.max_length = _clamp_int(config.max_length, 1, 1_000_000, 10000)
    config.click_x = _clamp_int(config.click_x, -1, 50000, -1)
    config.click_y = _clamp_int(config.click_y, -1, 50000, -1)

    if config.tab_policy not in {"spaces", "tab", "ignore"}:
        config.tab_policy = "spaces"
    if config.input_mode not in {"fast", "normal", "slow", "line"}:
        config.input_mode = "normal"
    if not str(config.hotkey).strip():
        config.hotkey = "ctrl+alt+v"
    return config


def apply_preset(config: AppConfig, preset_name: str) -> AppConfig:
    values = asdict(config)
    values.update(PRESETS.get(preset_name, {}))
    return validate_config(values)


def _clamp_int(value: Any, minimum: int, maximum: int, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))

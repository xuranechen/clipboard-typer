from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from app.clipboard import ClipboardError, clear_clipboard, read_clipboard_text
from app.config import AppConfig, PRESETS, apply_preset, load_config, save_config, validate_config
from app.hotkey import HotkeyManager
from app.logger import setup_logger
from app.platform_utils import platform_hint
from app.typer import ClipboardTyper
from app.window_target import ClickPosition, WindowInfo, activate_window, click_at_window_position, list_windows, pick_position_relative_to_window


class MainWindow:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Clipboard Typer")
        self.root.geometry("980x680")
        self.root.minsize(900, 600)
        self.logger = setup_logger()
        self.config = load_config()
        self.typer = ClipboardTyper(self.config)
        self.hotkey_manager: HotkeyManager | None = None
        self.typing_thread: threading.Thread | None = None

        self.status_var = tk.StringVar(value="等待")
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_text_var = tk.StringVar(value="0 / 0")
        self.runtime_info_var = tk.StringVar(value="")
        self.platform_var = tk.StringVar(value=platform_hint())

        self._build_vars()
        self._build_ui()
        self._apply_preview_visibility()
        self._update_runtime_info(self.config)
        self._restart_hotkey_if_needed()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def run(self) -> None:
        self.root.mainloop()

    def _build_vars(self) -> None:
        self.start_delay_var = tk.IntVar(value=self.config.start_delay_ms)
        self.char_delay_var = tk.IntVar(value=self.config.char_delay_ms)
        self.line_delay_var = tk.IntVar(value=self.config.line_delay_ms)
        self.tab_policy_var = tk.StringVar(value=self.config.tab_policy)
        self.tab_spaces_var = tk.IntVar(value=self.config.tab_spaces)
        self.max_length_var = tk.IntVar(value=self.config.max_length)
        self.confirm_var = tk.BooleanVar(value=self.config.confirm_before_type)
        self.show_preview_var = tk.BooleanVar(value=self.config.show_preview)
        self.password_mode_var = tk.BooleanVar(value=self.config.password_mode)
        self.clear_preview_var = tk.BooleanVar(value=self.config.clear_preview_after_type)
        self.clear_clipboard_var = tk.BooleanVar(value=self.config.clear_clipboard_after_type)
        self.hotkey_var = tk.StringVar(value=self.config.hotkey)
        self.enable_hotkey_var = tk.BooleanVar(value=self.config.enable_hotkey)
        self.esc_to_stop_var = tk.BooleanVar(value=self.config.esc_to_stop)
        self.input_mode_var = tk.StringVar(value=self.config.input_mode)
        self.preset_var = tk.StringVar(value="local_fast")
        self.target_window_title_var = tk.StringVar(value=self.config.target_window_title)
        self.click_x_var = tk.IntVar(value=self.config.click_x)
        self.click_y_var = tk.IntVar(value=self.config.click_y)
        self.auto_activate_var = tk.BooleanVar(value=self.config.auto_activate_window)
        self._window_cache: list[WindowInfo] = []
        self._window_title_list: list[str] = []

    def _build_ui(self) -> None:
        root = self.root
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(root, padding=(12, 10, 12, 6))
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(4, weight=1)
        ttk.Label(toolbar, text="Clipboard Typer", font=("Segoe UI", 12, "bold")).grid(row=0, column=6, sticky="e", padx=(16, 0))
        ttk.Button(toolbar, text="读取剪贴板", command=self.load_clipboard).grid(row=0, column=0, padx=(0, 8))
        self.start_button = ttk.Button(toolbar, text="开始输入", command=self.start_typing)
        self.start_button.grid(row=0, column=1, padx=(0, 8))
        self.stop_button = ttk.Button(toolbar, text="停止输入", command=self.stop_typing)
        self.stop_button.grid(row=0, column=2, padx=(0, 16))
        ttk.Label(toolbar, text="预设").grid(row=0, column=3, sticky="e")
        ttk.Combobox(toolbar, textvariable=self.preset_var, values=tuple(PRESETS.keys()), width=20, state="readonly").grid(row=0, column=4, sticky="w", padx=(4, 8))
        ttk.Button(toolbar, text="应用预设", command=self.apply_selected_preset).grid(row=0, column=5)

        main = ttk.Frame(root, padding=(12, 0, 12, 8))
        main.grid(row=1, column=0, sticky="nsew")
        main.columnconfigure(0, weight=0)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        settings = ttk.Frame(main, width=270)
        settings.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        settings.grid_propagate(False)
        settings.columnconfigure(0, weight=1)

        speed = ttk.LabelFrame(settings, text="输入速度", padding=10)
        speed.grid(row=0, column=0, sticky="ew")
        speed.columnconfigure(1, weight=1)
        self._spin(speed, "开始延迟(ms)", self.start_delay_var, 0, 0, 0, 60000, 100)
        self._spin(speed, "字符间隔(ms)", self.char_delay_var, 1, 0, 0, 5000, 5)
        self._spin(speed, "行间隔(ms)", self.line_delay_var, 2, 0, 0, 10000, 10)
        self._spin(speed, "最大长度", self.max_length_var, 3, 0, 1, 1_000_000, 100)

        input_opts = ttk.LabelFrame(settings, text="输入规则", padding=10)
        input_opts.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        input_opts.columnconfigure(1, weight=1)
        ttk.Label(input_opts, text="Tab").grid(row=0, column=0, sticky="w")
        ttk.Combobox(input_opts, textvariable=self.tab_policy_var, values=("spaces", "tab", "ignore"), width=12, state="readonly").grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self._spin(input_opts, "Tab 空格", self.tab_spaces_var, 1, 0, 0, 16, 1)
        ttk.Label(input_opts, text="输入模式").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Combobox(input_opts, textvariable=self.input_mode_var, values=("fast", "normal", "slow", "line"), width=12, state="readonly").grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))
        ttk.Label(input_opts, text="⚠ 仅支持 ASCII，中文会被过滤", foreground="#cc6600").grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))

        behavior = ttk.LabelFrame(settings, text="安全与行为", padding=10)
        behavior.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        ttk.Checkbutton(behavior, text="输入前确认", variable=self.confirm_var).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(behavior, text="显示预览", variable=self.show_preview_var, command=self._apply_preview_visibility).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(behavior, text="密码模式", variable=self.password_mode_var, command=self._apply_preview_visibility).grid(row=2, column=0, sticky="w")
        ttk.Checkbutton(behavior, text="完成后清空预览", variable=self.clear_preview_var).grid(row=3, column=0, sticky="w")
        ttk.Checkbutton(behavior, text="完成后清空剪贴板", variable=self.clear_clipboard_var).grid(row=4, column=0, sticky="w")
        ttk.Button(behavior, text="清空预览", command=self.clear_preview).grid(row=5, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(behavior, text="清空剪贴板", command=self.clear_system_clipboard).grid(row=6, column=0, sticky="ew", pady=(6, 0))

        hotkey_frame = ttk.LabelFrame(settings, text="快捷键", padding=10)
        hotkey_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        hotkey_frame.columnconfigure(1, weight=1)
        ttk.Checkbutton(hotkey_frame, text="启用快捷键", variable=self.enable_hotkey_var, command=self.save_settings).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(hotkey_frame, text="快捷键").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(hotkey_frame, textvariable=self.hotkey_var, width=18).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))
        ttk.Checkbutton(hotkey_frame, text="Esc 停止", variable=self.esc_to_stop_var, command=self.save_settings).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Button(hotkey_frame, text="保存设置", command=self.save_settings).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        target_frame = ttk.LabelFrame(settings, text="目标窗口", padding=10)
        target_frame.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        target_frame.columnconfigure(1, weight=1)
        ttk.Button(target_frame, text="刷新窗口列表", command=self._refresh_window_list).grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Label(target_frame, text="窗口").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.window_combo = ttk.Combobox(target_frame, textvariable=self.target_window_title_var, values=self._window_title_list, width=20)
        self.window_combo.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))
        coord_frame = ttk.Frame(target_frame)
        coord_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        coord_frame.columnconfigure(1, weight=1)
        coord_frame.columnconfigure(3, weight=1)
        ttk.Label(coord_frame, text="X").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(coord_frame, textvariable=self.click_x_var, from_=-1, to=50000, width=6).grid(row=0, column=1, sticky="ew", padx=(4, 8))
        ttk.Label(coord_frame, text="Y").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(coord_frame, textvariable=self.click_y_var, from_=-1, to=50000, width=6).grid(row=0, column=3, sticky="ew", padx=(4, 0))
        ttk.Button(target_frame, text="拾取坐标", command=self._pick_click_position).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Checkbutton(target_frame, text="自动激活窗口并点击", variable=self.auto_activate_var, command=self.save_settings).grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))

        preview_frame = ttk.LabelFrame(main, text="文本预览", padding=10)
        preview_frame.grid(row=0, column=1, sticky="nsew")
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        self.preview = tk.Text(preview_frame, wrap="word", undo=True, font=("Consolas", 11), padx=8, pady=8)
        self.preview.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.preview.configure(yscrollcommand=yscroll.set)

        bottom = ttk.Frame(root, padding=(12, 0, 12, 10))
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)
        ttk.Separator(bottom).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ttk.Progressbar(bottom, variable=self.progress_var, maximum=100).grid(row=1, column=0, sticky="ew")
        ttk.Label(bottom, textvariable=self.progress_text_var, width=16).grid(row=1, column=1, padx=(8, 0))
        ttk.Label(bottom, textvariable=self.status_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Label(bottom, textvariable=self.runtime_info_var, foreground="#444444").grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Label(bottom, textvariable=self.platform_var, foreground="#666666").grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))

    def _spin(self, parent: ttk.Frame, label: str, variable: tk.IntVar, row: int, col: int, from_: int, to: int, increment: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w")
        ttk.Spinbox(parent, textvariable=variable, from_=from_, to=to, increment=increment, width=10).grid(row=row, column=col + 1, sticky="ew", padx=(4, 8))

    def load_clipboard(self) -> None:
        try:
            text = read_clipboard_text()
        except ClipboardError as exc:
            self.set_status(f"剪贴板读取失败：{exc}")
            messagebox.showerror("剪贴板读取失败", str(exc))
            return
        if not text:
            self.set_status("剪贴板为空")
            return
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.set_status(f"已读取剪贴板，长度 {len(text)}")

    def start_typing(self) -> None:
        if self.typing_thread and self.typing_thread.is_alive():
            self.set_status("正在输入中")
            return
        config = self._config_from_ui()
        text = self.preview.get("1.0", "end-1c")
        if not text and config.show_preview:
            self.load_clipboard()
            text = self.preview.get("1.0", "end-1c")
        if not text:
            self.set_status("没有可输入的文本")
            return
        processed = self.typer.preprocess(text)
        if len(processed) > config.max_length:
            messagebox.showwarning("内容过长", f"内容长度 {len(processed)} 超过最大限制 {config.max_length}")
            self.set_status("内容超过最大长度")
            return
        if config.confirm_before_type and not messagebox.askyesno("确认输入", f"即将输入 {len(processed)} 个字符。\n请确认目标窗口已经准备好。\n是否继续？"):
            self.set_status("已取消")
            return
        save_config(config)
        self.config = config
        self.typer.update_config(config)
        self.start_button.configure(state="disabled")
        self.progress_var.set(0)
        self.progress_text_var.set(f"0 / {len(processed)}")
        self._update_runtime_info(config)
        self.typing_thread = threading.Thread(target=self._type_worker, args=(text,), daemon=True)
        self.typing_thread.start()

    def _type_worker(self, text: str) -> None:
        ok = False
        try:
            config = self.config
            if config.auto_activate_window and config.target_window_title.strip():
                self.set_status("正在激活目标窗口...")
                self.logger.info("activating window=%s click=(%s,%s)", config.target_window_title, config.click_x, config.click_y)
                from app.window_target import find_window
                win_info = find_window(config.target_window_title)
                if win_info is None:
                    self.set_status(f"未找到窗口：{config.target_window_title}")
                    return
                activate_window(win_info)
                if config.click_x >= 0 and config.click_y >= 0:
                    click_at_window_position(win_info, ClickPosition(config.click_x, config.click_y))
                    time.sleep(0.1)
            ok = self.typer.type_text(text, self.update_progress, self.set_status)
            self.logger.info("type_finished ok=%s length=%s", ok, len(text))
        except Exception as exc:  # pyautogui/platform errors should not kill UI
            self.logger.exception("type_failed length=%s", len(text))
            self.set_status(f"发生错误：{exc}")
        finally:
            self.root.after(0, lambda: self.start_button.configure(state="normal"))
            if ok:
                self.root.after(0, self._after_successful_type)

    def _after_successful_type(self) -> None:
        if self.config.clear_preview_after_type or self.config.password_mode:
            self.clear_preview()
        if self.config.clear_clipboard_after_type:
            self.clear_system_clipboard()

    def clear_preview(self) -> None:
        self.preview.delete("1.0", "end")
        self.progress_var.set(0)
        self.progress_text_var.set("0 / 0")
        self.set_status("预览已清空")

    def clear_system_clipboard(self) -> None:
        try:
            clear_clipboard()
            self.set_status("剪贴板已清空")
        except ClipboardError as exc:
            self.set_status(f"清空剪贴板失败：{exc}")
            messagebox.showerror("清空剪贴板失败", str(exc))

    def stop_typing(self) -> None:
        self.typer.stop()
        self.set_status("正在停止...")

    def update_progress(self, current: int, total: int) -> None:
        def apply() -> None:
            self.progress_var.set(0 if total == 0 else current / total * 100)
            self.progress_text_var.set(f"{current} / {total}")
        self.root.after(0, apply)

    def set_status(self, message: str) -> None:
        self.root.after(0, lambda: self.status_var.set(message))

    def save_settings(self) -> None:
        config = self._config_from_ui()
        save_config(config)
        self.config = config
        self.typer.update_config(config)
        self._update_runtime_info(config)
        self._restart_hotkey_if_needed()
        self.set_status("设置已保存")

    def _refresh_window_list(self) -> None:
        try:
            self._window_cache = list_windows()
            self._window_title_list = [w.title for w in self._window_cache]
            self.window_combo["values"] = self._window_title_list
            if self._window_title_list:
                current = self.target_window_title_var.get().strip()
                if not current or current not in self._window_title_list:
                    self.target_window_title_var.set(self._window_title_list[0])
                self.set_status(f"已刷新，找到 {len(self._window_title_list)} 个窗口")
            else:
                self.set_status("未找到可用窗口")
        except Exception as exc:
            self.logger.exception("refresh_window_list_failed")
            self.set_status(f"刷新窗口列表失败：{exc}")

    def _pick_click_position(self) -> None:
        title = self.target_window_title_var.get().strip()
        if not title:
            self.set_status("请先选择或输入目标窗口标题")
            return
        from app.window_target import find_window
        win_info = find_window(title)
        if win_info is None:
            self.set_status(f"未找到窗口：{title}")
            return
        self.set_status("3 秒后拾取坐标，请将鼠标移到目标窗口内的目标位置...")

        def _apply(pos: ClickPosition) -> None:
            self.click_x_var.set(pos.x)
            self.click_y_var.set(pos.y)
            self.root.after(0, lambda: self.set_status(f"已拾取坐标：({pos.x}, {pos.y})，请保存设置"))

        pick_position_relative_to_window(win_info, _apply, lambda msg: self.root.after(0, lambda: self.set_status(msg)), delay_seconds=3)

    def apply_selected_preset(self) -> None:
        config = apply_preset(self._config_from_ui(), self.preset_var.get())
        self._set_ui_from_config(config)
        self.save_settings()

    def _config_from_ui(self) -> AppConfig:
        data = {
            "start_delay_ms": self.start_delay_var.get(),
            "char_delay_ms": self.char_delay_var.get(),
            "line_delay_ms": self.line_delay_var.get(),
            "tab_policy": self.tab_policy_var.get(),
            "tab_spaces": self.tab_spaces_var.get(),
            "max_length": self.max_length_var.get(),
            "confirm_before_type": self.confirm_var.get(),
            "show_preview": self.show_preview_var.get(),
            "password_mode": self.password_mode_var.get(),
            "clear_preview_after_type": self.clear_preview_var.get(),
            "clear_clipboard_after_type": self.clear_clipboard_var.get(),
            "hotkey": self.hotkey_var.get(),
            "enable_hotkey": self.enable_hotkey_var.get(),
            "esc_to_stop": self.esc_to_stop_var.get(),
            "input_mode": self.input_mode_var.get(),
            "target_window_title": self.target_window_title_var.get(),
            "click_x": self.click_x_var.get(),
            "click_y": self.click_y_var.get(),
            "auto_activate_window": self.auto_activate_var.get(),
        }
        return validate_config(data)

    def _set_ui_from_config(self, config: AppConfig) -> None:
        self.start_delay_var.set(config.start_delay_ms)
        self.char_delay_var.set(config.char_delay_ms)
        self.line_delay_var.set(config.line_delay_ms)
        self.tab_policy_var.set(config.tab_policy)
        self.tab_spaces_var.set(config.tab_spaces)
        self.max_length_var.set(config.max_length)
        self.confirm_var.set(config.confirm_before_type)
        self.show_preview_var.set(config.show_preview)
        self.password_mode_var.set(config.password_mode)
        self.clear_preview_var.set(config.clear_preview_after_type)
        self.clear_clipboard_var.set(config.clear_clipboard_after_type)
        self.hotkey_var.set(config.hotkey)
        self.enable_hotkey_var.set(config.enable_hotkey)
        self.esc_to_stop_var.set(config.esc_to_stop)
        self.input_mode_var.set(config.input_mode)
        self.target_window_title_var.set(config.target_window_title)
        self.click_x_var.set(config.click_x)
        self.click_y_var.set(config.click_y)
        self.auto_activate_var.set(config.auto_activate_window)
        self._apply_preview_visibility()

    def _apply_preview_visibility(self) -> None:
        if self.password_mode_var.get() or not self.show_preview_var.get():
            self.preview.configure(fg="#999999")
        else:
            self.preview.configure(fg="#000000")

    def _update_runtime_info(self, config: AppConfig) -> None:
        hotkey = config.hotkey if config.enable_hotkey else "未启用"
        target = config.target_window_title if config.auto_activate_window and config.target_window_title else "未设置"
        click = f"({config.click_x}, {config.click_y})" if config.click_x >= 0 and config.auto_activate_window else "未设置"
        message = (
            f"模式：{config.input_mode} | 字符间隔：{config.char_delay_ms}ms | "
            f"行间隔：{config.line_delay_ms}ms | 快捷键：{hotkey} | 目标窗口：{target} | 点击位：{click}"
        )
        self.runtime_info_var.set(message)

    def _restart_hotkey_if_needed(self) -> None:
        if self.hotkey_manager:
            self.hotkey_manager.stop()
            self.hotkey_manager = None
        if not self.enable_hotkey_var.get():
            return
        try:
            self.hotkey_manager = HotkeyManager(self.hotkey_var.get(), lambda: self.root.after(0, self._hotkey_trigger), self.stop_typing)
            self.hotkey_manager.start(self.esc_to_stop_var.get())
            self.logger.info("hotkey_started hotkey=%s", self.hotkey_var.get())
        except Exception as exc:
            self.logger.exception("hotkey_failed")
            self.enable_hotkey_var.set(False)
            self.set_status(f"快捷键注册失败：{exc}")

    def _hotkey_trigger(self) -> None:
        self.load_clipboard()
        self.start_typing()

    def close(self) -> None:
        self.typer.stop()
        if self.hotkey_manager:
            self.hotkey_manager.stop()
        save_config(self._config_from_ui())
        self.root.destroy()

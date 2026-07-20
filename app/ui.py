from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from app.clipboard import ClipboardError, clear_clipboard, read_clipboard_text
from app.commands import Command, add_command, delete_command, filter_by_category, get_categories, load_commands, save_commands, update_command
from app.config import AppConfig, PRESETS, apply_preset, load_config, save_config, validate_config
from app.history import HistoryEntry, add_history, clear_history, load_history, save_history
from app.tray import create_tray_icon, run_tray
from app.hotkey import HotkeyManager
from app.logger import setup_logger
from app.platform_utils import platform_hint
from app.typer import ClipboardTyper
from app.window_target import ClickPosition, WindowInfo, activate_window, click_at_window_position, list_windows, pick_position_relative_to_window


class MainWindow:
    def __init__(self) -> None:
        self.root = ttk.Window(themename="litera")
        self.root.title("Clipboard Typer")
        self.root.geometry("980x680")
        self.root.minsize(900, 600)
        self.logger = setup_logger()
        self.config = load_config()
        self.typer = ClipboardTyper(self.config)
        self.hotkey_manager: HotkeyManager | None = None
        self.typing_thread: threading.Thread | None = None
        self.commands = load_commands()
        self.history = load_history()
        self._cmd_editing_id: str | None = None

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
        self._init_tray()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close_request)

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
        toolbar.columnconfigure(5, weight=1)
        ttk.Label(toolbar, text="Clipboard Typer", font=("Segoe UI", 12, "bold")).grid(row=0, column=7, sticky="e", padx=(16, 0))
        ttk.Button(toolbar, text="读取剪贴板", command=self.load_clipboard).grid(row=0, column=0, padx=(0, 8))
        self.start_button = ttk.Button(toolbar, text="开始输入", command=self.start_typing)
        self.start_button.grid(row=0, column=1, padx=(0, 8))
        self.stop_button = ttk.Button(toolbar, text="停止输入", command=self.stop_typing)
        self.stop_button.grid(row=0, column=2, padx=(0, 16))
        self.next_line_button = ttk.Button(toolbar, text="下一行", command=self._continue_next_line)
        self.next_line_button.grid(row=0, column=3, padx=(0, 16))
        self.next_line_button.grid_remove()
        ttk.Label(toolbar, text="预设").grid(row=0, column=4, sticky="e")
        ttk.Combobox(toolbar, textvariable=self.preset_var, values=tuple(PRESETS.keys()), width=20, state="readonly").grid(row=0, column=5, sticky="w", padx=(4, 8))
        ttk.Button(toolbar, text="应用预设", command=self.apply_selected_preset).grid(row=0, column=6)

        main = ttk.Frame(root, padding=(12, 0, 12, 8))
        main.grid(row=1, column=0, sticky="nsew")
        main.columnconfigure(0, weight=0)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        left_nb = ttk.Notebook(main, width=280)
        left_nb.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        left_nb.grid_propagate(False)

        # ---- Tab 1: 输入设置 ----
        tab_input = ttk.Frame(left_nb, padding=8)
        left_nb.add(tab_input, text=" 输入 ")
        tab_input.columnconfigure(0, weight=1)

        speed = ttk.LabelFrame(tab_input, text="输入速度", padding=10)
        speed.grid(row=0, column=0, sticky="ew")
        speed.columnconfigure(1, weight=1)
        self._spin(speed, "开始延迟(ms)", self.start_delay_var, 0, 0, 0, 60000, 100)
        self._spin(speed, "字符间隔(ms)", self.char_delay_var, 1, 0, 0, 5000, 5)
        self._spin(speed, "行间隔(ms)", self.line_delay_var, 2, 0, 0, 10000, 10)
        self._spin(speed, "最大长度", self.max_length_var, 3, 0, 1, 1_000_000, 100)

        input_opts = ttk.LabelFrame(tab_input, text="输入规则", padding=10)
        input_opts.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        input_opts.columnconfigure(1, weight=1)
        ttk.Label(input_opts, text="Tab").grid(row=0, column=0, sticky="w")
        ttk.Combobox(input_opts, textvariable=self.tab_policy_var, values=("spaces", "tab", "ignore"), width=12, state="readonly").grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self._spin(input_opts, "Tab 空格", self.tab_spaces_var, 1, 0, 0, 16, 1)
        ttk.Label(input_opts, text="输入模式").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Combobox(input_opts, textvariable=self.input_mode_var, values=("fast", "normal", "slow", "line", "step_by_step", "adaptive"), width=12, state="readonly").grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))
        ttk.Label(input_opts, text="⚠ 仅支持 ASCII，中文会被过滤", foreground="#cc6600").grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))

        # ---- Tab 2: 行为 ----
        tab_behavior = ttk.Frame(left_nb, padding=8)
        left_nb.add(tab_behavior, text=" 行为 ")
        tab_behavior.columnconfigure(0, weight=1)

        behavior = ttk.LabelFrame(tab_behavior, text="安全与行为", padding=10)
        behavior.grid(row=0, column=0, sticky="ew")
        ttk.Checkbutton(behavior, text="输入前确认", variable=self.confirm_var).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(behavior, text="显示预览", variable=self.show_preview_var, command=self._apply_preview_visibility).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(behavior, text="密码模式", variable=self.password_mode_var, command=self._apply_preview_visibility).grid(row=2, column=0, sticky="w")
        ttk.Checkbutton(behavior, text="完成后清空预览", variable=self.clear_preview_var).grid(row=3, column=0, sticky="w")
        ttk.Checkbutton(behavior, text="完成后清空剪贴板", variable=self.clear_clipboard_var).grid(row=4, column=0, sticky="w")
        ttk.Button(behavior, text="清空预览", command=self.clear_preview).grid(row=5, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(behavior, text="清空剪贴板", command=self.clear_system_clipboard).grid(row=6, column=0, sticky="ew", pady=(6, 0))

        hotkey_frame = ttk.LabelFrame(tab_behavior, text="快捷键", padding=10)
        hotkey_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        hotkey_frame.columnconfigure(1, weight=1)
        ttk.Checkbutton(hotkey_frame, text="启用快捷键", variable=self.enable_hotkey_var, command=self.save_settings).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(hotkey_frame, text="快捷键").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(hotkey_frame, textvariable=self.hotkey_var, width=18).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))
        ttk.Checkbutton(hotkey_frame, text="Esc 停止", variable=self.esc_to_stop_var, command=self.save_settings).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Button(hotkey_frame, text="保存设置", command=self.save_settings).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        # ---- Tab 3: 目标窗口 ----
        tab_target = ttk.Frame(left_nb, padding=8)
        left_nb.add(tab_target, text=" 目标 ")
        tab_target.columnconfigure(0, weight=1)

        target_frame = ttk.LabelFrame(tab_target, text="目标窗口", padding=10)
        target_frame.grid(row=0, column=0, sticky="ew")
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

        # ---- Tab 4: 命令库 ----
        tab_cmds = ttk.Frame(left_nb, padding=8)
        left_nb.add(tab_cmds, text=" 命令 ")
        tab_cmds.columnconfigure(0, weight=1)
        tab_cmds.rowconfigure(1, weight=1)

        cmd_top = ttk.Frame(tab_cmds)
        cmd_top.grid(row=0, column=0, sticky="ew")
        cmd_top.columnconfigure(1, weight=1)
        ttk.Label(cmd_top, text="分类").grid(row=0, column=0, sticky="w")
        self.cmd_category_var = tk.StringVar(value="全部")
        self.cmd_category_combo = ttk.Combobox(cmd_top, textvariable=self.cmd_category_var, values=["全部"] + get_categories(self.commands), width=14, state="readonly")
        self.cmd_category_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.cmd_category_combo.bind("<<ComboboxSelected>>", lambda _: self._refresh_cmd_list())

        self.cmd_listbox = tk.Listbox(tab_cmds, font=("Segoe UI", 9))
        self.cmd_listbox.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        self.cmd_listbox.bind("<Double-1>", lambda _: self._cmd_fill_preview())
        cmd_scroll = ttk.Scrollbar(tab_cmds, orient="vertical", command=self.cmd_listbox.yview)
        cmd_scroll.grid(row=1, column=1, sticky="ns", pady=(6, 0))
        self.cmd_listbox.configure(yscrollcommand=cmd_scroll.set)

        cmd_btn_row = ttk.Frame(tab_cmds)
        cmd_btn_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Button(cmd_btn_row, text="填入预览", command=self._cmd_fill_preview).pack(side="left", padx=(0, 4))
        ttk.Button(cmd_btn_row, text="添加", command=self._cmd_add).pack(side="left", padx=(0, 4))
        ttk.Button(cmd_btn_row, text="编辑", command=self._cmd_edit).pack(side="left", padx=(0, 4))
        ttk.Button(cmd_btn_row, text="删除", command=self._cmd_delete).pack(side="left")
        self._refresh_cmd_list()

        # ---- Tab 5: 历史 ----
        tab_history = ttk.Frame(left_nb, padding=8)
        left_nb.add(tab_history, text=" 历史 ")
        tab_history.columnconfigure(0, weight=1)
        tab_history.rowconfigure(0, weight=1)

        self.history_listbox = tk.Listbox(tab_history, font=("Segoe UI", 9))
        self.history_listbox.grid(row=0, column=0, sticky="nsew")
        history_scroll = ttk.Scrollbar(tab_history, orient="vertical", command=self.history_listbox.yview)
        history_scroll.grid(row=0, column=1, sticky="ns")
        self.history_listbox.configure(yscrollcommand=history_scroll.set)
        self.history_listbox.bind("<Double-1>", lambda _: self._history_fill_preview())

        history_btn_row = ttk.Frame(tab_history)
        history_btn_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Button(history_btn_row, text="填入预览", command=self._history_fill_preview).pack(side="left", padx=(0, 4))
        ttk.Button(history_btn_row, text="清空历史", command=self._history_clear).pack(side="left")
        self._refresh_history_list()

        preview_frame = ttk.LabelFrame(main, text="文本预览", padding=10)
        preview_frame.grid(row=0, column=1, sticky="nsew")
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(1, weight=1)
        preview_toolbar = ttk.Frame(preview_frame)
        preview_toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        ttk.Button(preview_toolbar, text="清空", command=self.clear_preview).pack(side="left")
        self.preview = tk.Text(preview_frame, wrap="word", undo=True, font=("Consolas", 11), padx=8, pady=8)
        self.preview.grid(row=1, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview.yview)
        yscroll.grid(row=1, column=1, sticky="ns")
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
        self.history = add_history(text, self.history)
        save_history(self.history)
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
            if config.input_mode == "step_by_step":
                self.root.after(0, lambda: self.next_line_button.grid())
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
            self.root.after(0, lambda: self.next_line_button.grid_remove())
            self.root.after(0, lambda: self.start_button.configure(state="normal"))
            if ok:
                self.root.after(0, self._after_successful_type)

    def _after_successful_type(self) -> None:
        if self.config.clear_preview_after_type or self.config.password_mode:
            self.clear_preview()
        if self.config.clear_clipboard_after_type:
            self.clear_system_clipboard()

    def _continue_next_line(self) -> None:
        self.typer.continue_next_line()
        self.set_status("继续下一行...")

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

    def _refresh_cmd_list(self) -> None:
        self.cmd_listbox.delete(0, "end")
        category = self.cmd_category_var.get()
        filtered = filter_by_category(self.commands, category)
        for cmd in filtered:
            self.cmd_listbox.insert("end", f"[{cmd.category}] {cmd.name}")

    def _get_selected_command(self) -> Command | None:
        sel = self.cmd_listbox.curselection()
        if not sel:
            return None
        category = self.cmd_category_var.get()
        filtered = filter_by_category(self.commands, category)
        idx = sel[0]
        if idx >= len(filtered):
            return None
        return filtered[idx]

    def _cmd_fill_preview(self) -> None:
        cmd = self._get_selected_command()
        if not cmd:
            self.set_status("请先选择一条命令")
            return
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", cmd.content)
        self.set_status(f"已填入：{cmd.name}")

    def _cmd_add(self) -> None:
        self._cmd_editing_id = None
        self._open_cmd_dialog("添加命令", "", "通用", "")

    def _cmd_edit(self) -> None:
        cmd = self._get_selected_command()
        if not cmd:
            self.set_status("请先选择一条命令")
            return
        self._cmd_editing_id = cmd.id
        self._open_cmd_dialog("编辑命令", cmd.name, cmd.category, cmd.content)

    def _cmd_delete(self) -> None:
        cmd = self._get_selected_command()
        if not cmd:
            self.set_status("请先选择一条命令")
            return
        if not messagebox.askyesno("确认删除", f"确定删除命令「{cmd.name}」？"):
            return
        delete_command(self.commands, cmd.id)
        save_commands(self.commands)
        self._refresh_cmd_list()
        self.set_status(f"已删除：{cmd.name}")

    def _open_cmd_dialog(self, title: str, name: str, category: str, content: str) -> None:
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.geometry("480x360")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        ttk.Label(dlg, text="名称").pack(anchor="w", padx=16, pady=(12, 0))
        name_var = tk.StringVar(value=name)
        ttk.Entry(dlg, textvariable=name_var, width=50).pack(fill="x", padx=16)

        ttk.Label(dlg, text="分类").pack(anchor="w", padx=16, pady=(8, 0))
        cat_var = tk.StringVar(value=category)
        ttk.Entry(dlg, textvariable=cat_var, width=50).pack(fill="x", padx=16)

        ttk.Label(dlg, text="命令内容").pack(anchor="w", padx=16, pady=(8, 0))
        content_text = tk.Text(dlg, wrap="word", font=("Consolas", 10), height=10)
        content_text.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        content_text.insert("1.0", content)

        def _save() -> None:
            n = name_var.get().strip()
            c = cat_var.get().strip()
            t = content_text.get("1.0", "end-1c").strip()
            if not n:
                messagebox.showwarning("提示", "名称不能为空", parent=dlg)
                return
            if not t:
                messagebox.showwarning("提示", "命令内容不能为空", parent=dlg)
                return
            if self._cmd_editing_id:
                update_command(self.commands, self._cmd_editing_id, n, c, t)
            else:
                add_command(self.commands, n, c, t)
            save_commands(self.commands)
            self._refresh_cmd_list()
            self._refresh_category_combo()
            dlg.destroy()
            self.set_status(f"已保存：{n}")

        btn_row = ttk.Frame(dlg)
        btn_row.pack(fill="x", padx=16, pady=(0, 12))
        ttk.Button(btn_row, text="保存", command=_save).pack(side="right", padx=(8, 0))
        ttk.Button(btn_row, text="取消", command=dlg.destroy).pack(side="right")

    def _refresh_category_combo(self) -> None:
        cats = ["全部"] + get_categories(self.commands)
        self.cmd_category_combo["values"] = cats

    def _refresh_history_list(self) -> None:
        self.history_listbox.delete(0, "end")
        for entry in self.history:
            self.history_listbox.insert("end", entry.preview)

    def _history_fill_preview(self) -> None:
        sel = self.history_listbox.curselection()
        if not sel:
            self.set_status("请先选择一条历史记录")
            return
        idx = sel[0]
        if idx >= len(self.history):
            return
        entry = self.history[idx]
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", entry.preview)
        self.set_status(f"已填入历史记录（长度 {entry.length}）")

    def _history_clear(self) -> None:
        if not messagebox.askyesno("确认", "确定清空所有输入历史？"):
            return
        clear_history()
        self.history = []
        self._refresh_history_list()
        self.set_status("历史已清空")

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

    def _init_tray(self) -> None:
        self.tray_icon = create_tray_icon(
            on_show=lambda: self.root.after(0, self._show_window),
            on_quit=lambda: self.root.after(0, self.close),
        )
        run_tray(self.tray_icon)

    def _show_window(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _on_close_request(self) -> None:
        """关闭窗口时最小化到托盘，而不是退出。"""
        self.root.withdraw()

    def close(self) -> None:
        self.typer.stop()
        if self.hotkey_manager:
            self.hotkey_manager.stop()
        save_config(self._config_from_ui())
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()

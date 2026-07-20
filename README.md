<p align="center">
  <h1 align="center">📋 Clipboard Typer</h1>
  <p align="center">剪贴板模拟输入工具 — 解决 VNC / 堡垒机 / Web 控制台无法粘贴的问题</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Platform-Windows-0078D4?logo=windows&logoColor=white" alt="Windows">
  <img src="https://img.shields.io/badge/UI-ttkbootstrap-7B2FF7" alt="ttkbootstrap">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License">
</p>

---

## ✨ 功能特性

| 功能 | 说明 |
|---|---|
| 📋 剪贴板读取 | 一键读取剪贴板并预览待输入内容 |
| ⌨️ 逐字符输入 | 模拟键盘逐字符输入，`\n` → Enter，Tab → 空格 |
| ⚡ 6 种输入模式 | `fast` / `normal` / `slow` / `line` / `step_by_step` / `adaptive` |
| 🎯 速度预设 | 本地快速 / VNC 稳定 / Web 控制台慢速 / IPMI 超慢，一键切换 |
| 🪟 目标窗口 | 窗口列表选择、相对坐标拾取、自动激活并点击后输入 |
| 📚 命令库 | 预置 40+ 条运维命令（Linux/Docker/K8s/MySQL/Redis），支持增删改查 |
| 📜 输入历史 | 自动记录最近 50 条输入，双击快速填入 |
| ⏸️ 分段输入 | `step_by_step` 模式每行暂停，手动确认后继续 |
| 🔄 自适应速度 | `adaptive` 模式根据输入重试自动调节速度 |
| ⌨️ 快捷键 | `Ctrl+Alt+V` 可选启用，Esc 可选停止 |
| 🔒 安全模式 | 密码模式、输入前确认、完成后清空预览/剪贴板 |
| 🖥️ 托盘常驻 | 关闭窗口最小化到系统托盘，不退出程序 |
| 🎨 现代 UI | ttkbootstrap 主题美化 |

## 🚀 快速开始

### 一键运行（推荐）

```powershell
.\start.bat
```

自动检查/创建 conda 环境 `typer`、安装依赖、启动程序，日志写入 `start.log`。

### 手动运行

```powershell
python -m pip install -r requirements.txt
python main.py
```

### 打包 exe

```powershell
build\build_windows.bat
```

生成 `dist/ClipboardTyper.exe`。

## 📐 界面布局

```
┌─────────────────────────────────────────────────────────┐
│  [读取剪贴板] [开始输入] [停止输入]  预设: [vnc_stable ▼] │
├────────────┬────────────────────────────────────────────┤
│ ┌ 输入 ┐  │                                            │
│ │ 速度  │  │                                            │
│ │ 规则  │  │           文本预览                          │
│ ├ 行为 ┤  │  [清空]                                     │
│ │ 安全  │  │  ┌────────────────────────────────────┐    │
│ │ 快捷键│  │  │ docker ps                          │    │
│ ├ 目标 ┤  │  │ kubectl get pods -A                  │    │
│ │ 窗口  │  │  │ redis-cli -h 10.0.0.1               │    │
│ ├ 命令 ┤  │  │                                    │    │
│ │ 库    │  │  └────────────────────────────────────┘    │
│ ├ 历史 ┤  │                                            │
│ └──────┘  │                                            │
├───────────┴────────────────────────────────────────────┤
│  ████████████░░░░░░░░  32 / 128                        │
│  正在输入 32 / 128                                      │
│  模式：normal | 字符间隔：50ms | 快捷键：未启用          │
└─────────────────────────────────────────────────────────┘
```

## ⚙️ 默认参数

| 配置 | 默认值 | 说明 |
|---|---:|---|
| 开始延迟 | 3000 ms | 给用户时间切换目标窗口 |
| 字符间隔 | 50 ms | 运维控制台更稳定 |
| 行间隔 | 150 ms | 降低换行后丢字符概率 |
| Tab 处理 | 4 个空格 | 避免 Tab 切换焦点 |
| 最大长度 | 10000 字符 | 防止误输入大段日志 |

## 🔒 安全

- 不保存剪贴板正文到配置或日志
- 默认限制最大输入长度
- 输入中可随时停止
- 密码模式隐藏预览内容

## 🛠️ 技术栈

| 模块 | 技术 |
|---|---|
| 语言 | Python 3.10+ |
| UI 框架 | ttkbootstrap (Tkinter) |
| 剪贴板 | pyperclip |
| 键盘模拟 | pyautogui |
| 全局快捷键 | pynput |
| 系统托盘 | pystray |
| 打包 | PyInstaller |
| CI/CD | GitHub Actions |

## 📁 项目结构

```
clipboard-typer/
├── main.py                  # 程序入口
├── start.bat                # 一键启动脚本（conda）
├── requirements.txt         # Python 依赖
├── config.example.json      # 配置示例
├── .github/
│   └── workflows/
│       └── build.yml        # GitHub Actions 自动构建
├── app/
│   ├── ui.py                # 主界面（ttkbootstrap）
│   ├── typer.py             # 输入核心逻辑
│   ├── clipboard.py         # 剪贴板读写
│   ├── config.py            # 配置加载保存
│   ├── commands.py          # 命令库（增删改查）
│   ├── history.py           # 输入历史记录
│   ├── hotkey.py            # 全局快捷键
│   ├── tray.py              # 系统托盘
│   ├── window_target.py     # 目标窗口选择
│   ├── platform_utils.py    # 平台检测
│   └── logger.py            # 日志模块
├── build/
│   ├── build_windows.bat    # Windows 打包脚本
│   └── version.txt          # 版本信息
└── assets/                  # 图标等资源
```

## 📄 License

MIT

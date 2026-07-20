# Clipboard Typer

剪贴板模拟输入工具：读取本地剪贴板文本，通过模拟键盘逐字符输入到目标窗口。

适用于 VNC、RDP、Web 控制台、堡垒机、IPMI/KVM 等不支持粘贴或剪贴板同步不稳定的场景。

## 功能

- 读取剪贴板并预览待输入内容
- 逐字符模拟键盘输入，`\n` 转 Enter，Tab 转空格
- 四种输入速度模式：fast / normal / slow / line
- 速度预设一键切换：本地快速、VNC 稳定、Web 控制台慢速、IPMI/KVM 超慢
- 目标窗口选择：从窗口列表选择，拾取相对坐标，自动激活窗口并点击后输入
- 全局快捷键可选启用（默认 `Ctrl+Alt+V`），Esc 可选停止
- 密码模式、输入前确认、完成后清空预览/剪贴板
- 配置自动保存，首次启动自动生成 `config.json`
- 仅支持 ASCII 字符，中文会被过滤

## 一键运行

```powershell
.\start.bat
```

自动检查/创建 conda 环境 `typer`、安装依赖、启动程序，运行日志写入 `start.log`。

## 手动运行

```powershell
python -m pip install -r requirements.txt
python main.py
```

## 打包

```powershell
build\build_windows.bat
```

生成 `dist/ClipboardTyper.exe`。

## 默认参数

| 配置 | 默认值 | 说明 |
|---|---:|---|
| 开始延迟 | 3000 ms | 给用户时间切换目标窗口 |
| 字符间隔 | 50 ms | 运维控制台更稳定 |
| 行间隔 | 150 ms | 降低换行后丢字符概率 |
| Tab 处理 | 4 个空格 | 避免 Tab 切换焦点 |
| 最大长度 | 10000 字符 | 防止误输入大段日志 |

## 安全

- 不保存剪贴板正文到配置或日志
- 默认限制最大输入长度
- 输入中可随时停止

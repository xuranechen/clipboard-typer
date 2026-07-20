"""运维命令库：增删改查，JSON 持久化。"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

COMMANDS_PATH = Path("commands.json")


@dataclass
class Command:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    category: str = "通用"
    content: str = ""
    created_at: float = field(default_factory=time.time)


PRESET_COMMANDS: list[dict[str, str]] = [
    # ---- Linux 基础 ----
    {"name": "查看磁盘", "category": "Linux", "content": "df -h"},
    {"name": "查看内存", "category": "Linux", "content": "free -h"},
    {"name": "查看 CPU", "category": "Linux", "content": "top -bn1 | head -20"},
    {"name": "查看进程", "category": "Linux", "content": "ps aux --sort=-%mem | head -20"},
    {"name": "查看网络连接", "category": "Linux", "content": "ss -tulnp"},
    {"name": "查看路由", "category": "Linux", "content": "ip route"},
    {"name": "查看主机名", "category": "Linux", "content": "hostname && uname -a"},
    {"name": "查看系统时间", "category": "Linux", "content": "date && timedatectl"},
    {"name": "查看系统日志", "category": "Linux", "content": "journalctl -xe --no-pager | tail -50"},
    {"name": "查看登录用户", "category": "Linux", "content": "who && w"},
    # ---- 文件操作 ----
    {"name": "查找大文件", "category": "文件", "content": "find / -type f -size +100M -exec ls -lh {} \\; 2>/dev/null"},
    {"name": "查找最近修改", "category": "文件", "content": "find / -type f -mtime -1 -name '*.log' 2>/dev/null"},
    {"name": "递归查找文本", "category": "文件", "content": "grep -rn 'TODO' /path/to/dir"},
    {"name": "统计目录大小", "category": "文件", "content": "du -sh /var/log/*"},
    {"name": "清理 30 天前日志", "category": "文件", "content": "find /var/log -name '*.log' -mtime +30 -delete"},
    # ---- Docker ----
    {"name": "Docker 列表", "category": "Docker", "content": "docker ps -a --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'"},
    {"name": "Docker 镜像", "category": "Docker", "content": "docker images"},
    {"name": "Docker 日志", "category": "Docker", "content": "docker logs --tail 100 -f CONTAINER"},
    {"name": "Docker 清理", "category": "Docker", "content": "docker system prune -af"},
    {"name": "Docker 重启容器", "category": "Docker", "content": "docker restart CONTAINER"},
    {"name": "Docker 进入容器", "category": "Docker", "content": "docker exec -it CONTAINER /bin/bash"},
    # ---- Kubernetes ----
    {"name": "K8s Pod 列表", "category": "Kubernetes", "content": "kubectl get pods -A -o wide"},
    {"name": "K8s 节点状态", "category": "Kubernetes", "content": "kubectl get nodes -o wide"},
    {"name": "K8s 服务列表", "category": "Kubernetes", "content": "kubectl get svc -A"},
    {"name": "K8s Pod 日志", "category": "Kubernetes", "content": "kubectl logs -f POD_NAME -n NAMESPACE"},
    {"name": "K8s 进入 Pod", "category": "Kubernetes", "content": "kubectl exec -it POD_NAME -n NAMESPACE -- /bin/bash"},
    {"name": "K8s 事件", "category": "Kubernetes", "content": "kubectl get events -A --sort-by='.lastTimestamp' | tail -20"},
    {"name": "K8s 资源用量", "category": "Kubernetes", "content": "kubectl top pods -A --sort-by=memory"},
    # ---- 网络 ----
    {"name": "测速", "category": "网络", "content": "curl -o /dev/null -s -w '%{speed_download}' http://test.example.com/100mb"},
    {"name": "DNS 查询", "category": "网络", "content": "nslookup example.com"},
    {"name": "端口扫描", "category": "网络", "content": "nc -zv HOST PORT"},
    {"name": "HTTP 头", "category": "网络", "content": "curl -I https://example.com"},
    {"name": "本机 IP", "category": "网络", "content": "ip addr show | grep 'inet '"},
    # ---- MySQL ----
    {"name": "MySQL 连接", "category": "MySQL", "content": "mysql -u root -p -h HOST"},
    {"name": "MySQL 慢查询", "category": "MySQL", "content": "SHOW VARIABLES LIKE 'slow_query%';"},
    {"name": "MySQL 进程", "category": "MySQL", "content": "SHOW PROCESSLIST;"},
    {"name": "MySQL 表大小", "category": "MySQL", "content": "SELECT table_schema, table_name, ROUND(data_length/1024/1024,2) AS 'MB' FROM information_schema.tables ORDER BY data_length DESC LIMIT 20;"},
    # ---- Redis ----
    {"name": "Redis 连接", "category": "Redis", "content": "redis-cli -h HOST -p 6379"},
    {"name": "Redis 内存", "category": "Redis", "content": "INFO memory"},
    {"name": "Redis 键数量", "category": "Redis", "content": "DBSIZE"},
    {"name": "Redis 慢日志", "category": "Redis", "content": "SLOWLOG GET 10"},
]


def load_commands(path: Path = COMMANDS_PATH) -> list[Command]:
    if not path.exists():
        commands = _from_preset()
        save_commands(commands, path)
        return commands
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        commands = _from_preset()
        save_commands(commands, path)
        return commands
    return [Command(**item) for item in data]


def save_commands(commands: list[Command], path: Path = COMMANDS_PATH) -> None:
    path.write_text(
        json.dumps([asdict(c) for c in commands], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def add_command(commands: list[Command], name: str, category: str, content: str) -> Command:
    cmd = Command(name=name, category=category, content=content)
    commands.append(cmd)
    return cmd


def update_command(commands: list[Command], cmd_id: str, name: str, category: str, content: str) -> bool:
    for cmd in commands:
        if cmd.id == cmd_id:
            cmd.name = name
            cmd.category = category
            cmd.content = content
            return True
    return False


def delete_command(commands: list[Command], cmd_id: str) -> bool:
    for i, cmd in enumerate(commands):
        if cmd.id == cmd_id:
            commands.pop(i)
            return True
    return False


def get_categories(commands: list[Command]) -> list[str]:
    seen: list[str] = []
    for cmd in commands:
        if cmd.category not in seen:
            seen.append(cmd.category)
    return seen


def filter_by_category(commands: list[Command], category: str) -> list[Command]:
    if not category or category == "全部":
        return list(commands)
    return [c for c in commands if c.category == category]


def _from_preset() -> list[Command]:
    return [Command(name=p["name"], category=p["category"], content=p["content"]) for p in PRESET_COMMANDS]

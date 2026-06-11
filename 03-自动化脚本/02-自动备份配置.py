#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单版配置自动备份脚本
========================
适用：没有 Oxidized / RANCID 的环境
功能：每天定时通过 SSH 拉取配置，保存到本地目录
依赖：pip install netmiko
作者：Mavis
版本：v1.0

使用方法：
1. 配置设备列表
2. 加入 cron / Windows 任务计划
3. 每天 02:00 跑一次

Linux cron:
0 2 * * * /usr/bin/python3 /path/to/02-自动备份配置.py

Windows 任务计划:
操作：启动程序
程序：python
参数：C:\HackByJL\HackByJL\03-自动化脚本\02-自动备份配置.py
触发器：每天 02:00
"""

import os
import sys
import json
import hashlib
import difflib
import smtplib
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    from netmiko import ConnectHandler
    from netmiko.exceptions import NetMikoException
except ImportError:
    print("❌ 缺少 netmiko，请先 pip install netmiko")
    sys.exit(1)


# ============================================================
# 1. 设备清单（与 01-采集脚本 保持一致）
# ============================================================
DEVICES = [
    {"name": "RG-EG3220-内网网关", "host": "10.1.1.1", "device_type": "ruijie_os",
     "username": "admin", "password": "YourPassword"},
    {"name": "RG-S5760C-核心1", "host": "10.1.1.10", "device_type": "ruijie_os",
     "username": "admin", "password": "YourPassword"},
    {"name": "RG-S5760C-核心2", "host": "10.1.1.11", "device_type": "ruijie_os",
     "username": "admin", "password": "YourPassword"},
    {"name": "RG-S5760C-核心3", "host": "10.1.1.12", "device_type": "ruijie_os",
     "username": "admin", "password": "YourPassword"},
    {"name": "RG-S5310-接入1", "host": "10.1.1.20", "device_type": "ruijie_os",
     "username": "admin", "password": "YourPassword"},
    {"name": "RG-S5310-接入2", "host": "10.1.1.21", "device_type": "ruijie_os",
     "username": "admin", "password": "YourPassword"},
    {"name": "RG-S5310-接入3", "host": "10.1.1.22", "device_type": "ruijie_os",
     "username": "admin", "password": "YourPassword"},
    {"name": "RG-S5310-接入4", "host": "10.1.1.23", "device_type": "ruijie_os",
     "username": "admin", "password": "YourPassword"},
    {"name": "RG-WS6008-无线AC", "host": "10.1.1.30", "device_type": "ruijie_os",
     "username": "admin", "password": "YourPassword"},
    {"name": "RG-EG3230-外网网关", "host": "10.1.1.2", "device_type": "ruijie_os",
     "username": "admin", "password": "YourPassword"},
    {"name": "H3C-F1000-AK155-防火墙", "host": "10.1.1.50", "device_type": "hp_comware",
     "username": "admin", "password": "YourPassword"},
    {"name": "Huawei-S5735-内网核心", "host": "10.2.1.1", "device_type": "huawei",
     "username": "admin", "password": "YourPassword"},
    {"name": "Huawei-S5735-外网核心", "host": "10.2.1.2", "device_type": "huawei",
     "username": "admin", "password": "YourPassword"},
    {"name": "Huawei-USG6000E-防火墙", "host": "10.2.1.10", "device_type": "huawei",
     "username": "admin", "password": "YourPassword"},
    {"name": "Huawei-AR6300-S-核心路由器", "host": "10.2.1.20", "device_type": "huawei",
     "username": "admin", "password": "YourPassword"},
]


# ============================================================
# 2. 备份配置（获取 running-config 的命令）
# ============================================================
BACKUP_COMMANDS = {
    "ruijie_os": "show running-config",
    "hp_comware": "display current-configuration",
    "huawei": "display current-configuration",
    "cisco_ios": "show running-config",
}


# ============================================================
# 3. 邮件告警（可选）
# ============================================================
EMAIL_CONFIG = {
    "enabled": False,                  # 改成 True 启用
    "smtp_server": "smtp.example.com",
    "smtp_port": 587,
    "use_tls": True,
    "username": "backup@example.com",
    "password": "smtp-password",
    "from_addr": "backup@example.com",
    "to_addrs": ["admin@example.com", "ops@example.com"],
}


# ============================================================
# 4. 备份保留天数
# ============================================================
KEEP_DAYS = 90


# ============================================================
# 5. 核心函数
# ============================================================
def get_md5(content):
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def send_email(subject, content):
    """发送邮件告警"""
    if not EMAIL_CONFIG["enabled"]:
        return
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_CONFIG["from_addr"]
        msg["To"] = ", ".join(EMAIL_CONFIG["to_addrs"])
        msg["Subject"] = subject
        msg.attach(MIMEText(content, "html", "utf-8"))

        with smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
            if EMAIL_CONFIG["use_tls"]:
                server.starttls()
            server.login(EMAIL_CONFIG["username"], EMAIL_CONFIG["password"])
            server.send_message(msg)
        print("  📧 邮件告警已发送")
    except Exception as e:
        print(f"  ⚠️ 邮件发送失败: {e}")


def backup_device(device, backup_root):
    """备份单台设备"""
    name = device["name"]
    host = device["host"]
    device_type = device["device_type"]
    print(f"\n[{name}] {host} - 备份中...")

    backup_cmd = BACKUP_COMMANDS.get(device_type)
    if not backup_cmd:
        print(f"  ⚠️ 没有为 {device_type} 配置备份命令")
        return None

    # 设备目录：backup_root/<设备名>/
    device_dir = backup_root / name
    device_dir.mkdir(parents=True, exist_ok=True)

    try:
        with ConnectHandler(
            device_type=device_type,
            host=host,
            username=device["username"],
            password=device["password"],
            port=device.get("port", 22),
            timeout=30,
        ) as conn:
            output = conn.send_command(backup_cmd, read_timeout=120)

        # 计算 hash
        md5 = get_md5(output)
        file_path = device_dir / f"{datetime.now().strftime('%Y%m%d')}.cfg"
        file_path_md5 = device_dir / f"{datetime.now().strftime('%Y%m%d')}.cfg.md5"

        # 检查变更
        prev_file = None
        prev_diff = None
        for old in sorted(device_dir.glob("*.cfg"), reverse=True):
            if old.name != file_path.name:
                prev_file = old
                break

        is_changed = False
        if prev_file:
            prev_content = prev_file.read_text(encoding="utf-8")
            if get_md5(prev_content) != md5:
                is_changed = True
                prev_diff = "\n".join(difflib.unified_diff(
                    prev_content.splitlines(),
                    output.splitlines(),
                    lineterm="",
                    n=3,
                ))

        # 写文件
        file_path.write_text(output, encoding="utf-8")
        file_path_md5.write_text(md5, encoding="utf-8")

        # 写元数据
        meta = {
            "name": name,
            "host": host,
            "device_type": device_type,
            "backup_time": datetime.now().isoformat(),
            "md5": md5,
            "size": len(output),
            "lines": output.count("\n"),
            "is_changed": is_changed,
        }
        (device_dir / f"{datetime.now().strftime('%Y%m%d')}.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        if is_changed:
            print(f"  ⚠️ 配置已变更！")
            # 邮件告警
            send_email(
                f"[配置变更] {name} ({host})",
                f"<h3>设备 {name} ({host}) 配置已变更</h3>"
                f"<p>时间: {datetime.now().isoformat()}</p>"
                f"<p>MD5: {md5}</p>"
                f"<pre>{prev_diff[:5000] if prev_diff else '无diff'}</pre>"
            )
        else:
            print(f"  ✅ 配置无变化")

        return meta

    except NetMikoException as e:
        print(f"  ❌ Netmiko 错误: {e}")
        send_email(
            f"[备份失败] {name} ({host})",
            f"<h3>设备 {name} ({host}) 备份失败</h3><p>{e}</p>"
        )
        return None
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        send_email(
            f"[备份异常] {name} ({host})",
            f"<h3>设备 {name} ({host}) 备份异常</h3><p>{e}</p>"
        )
        return None


def cleanup_old_backups(backup_root):
    """清理过期备份"""
    print(f"\n清理 {KEEP_DAYS} 天前的备份...")
    cutoff = datetime.now() - timedelta(days=KEEP_DAYS)
    removed = 0
    for f in backup_root.rglob("*.cfg"):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink()
                # 同时删 .md5 和 .json
                for ext in [".cfg.md5", ".json"]:
                    meta = f.with_suffix(ext)
                    if meta.exists():
                        meta.unlink()
                removed += 1
        except Exception:
            pass
    print(f"  共清理 {removed} 个过期文件")


def main():
    """主入口"""
    backup_root = Path(__file__).parent.parent / "04-配置备份" / "历史备份"
    backup_root.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"网络设备自动备份 - 启动")
    print(f"设备数: {len(DEVICES)}")
    print(f"备份目录: {backup_root}")
    print(f"保留天数: {KEEP_DAYS}")
    print("=" * 70)

    results = []
    for device in DEVICES:
        meta = backup_device(device, backup_root)
        if meta:
            results.append(meta)

    # 清理
    cleanup_old_backups(backup_root)

    # 汇总
    changed = [m for m in results if m.get("is_changed")]
    print("\n" + "=" * 70)
    print(f"完成！备份: {len(results)} / 配置变更: {len(changed)}")
    if changed:
        print("变更设备列表:")
        for m in changed:
            print(f"  - {m['name']} ({m['host']})")
    print("=" * 70)


if __name__ == "__main__":
    main()

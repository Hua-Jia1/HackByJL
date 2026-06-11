#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络设备批量信息采集脚本
========================
用途：入厂第一天 / 日常巡检 / 变更前后，一次性采集所有设备的配置和状态
依赖：pip install netmiko
作者：Mavis
版本：v1.0

使用方法：
1. 编辑下方 devices 列表，填入设备信息
2. 编辑 commands 列表，填入要采集的命令
3. 执行：python 01-批量采集设备配置.py

结果：
- 在 04-配置备份/采集结果-YYYYMMDD-HHMMSS/ 下按设备分文件保存
- 同时生成 汇总-errors.log
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

try:
    from netmiko import ConnectHandler
    from netmiko.exceptions import NetMikoAuthenticationException, NetMikoTimeoutException
except ImportError:
    print("❌ 缺少 netmiko 库，请先安装：")
    print("   pip install netmiko")
    sys.exit(1)


# ============================================================
# 1. 设备清单（请按实际环境修改）
# ============================================================
DEVICES = [
    # ---- 一楼 / 业务网（锐捷） ----
    {
        "name": "RG-EG3220-内网网关",
        "host": "10.1.1.1",          # 改成实际管理 IP
        "device_type": "ruijie_os",  # 锐捷 NBR/EG 系列
        "username": "admin",
        "password": "YourPassword",
        "port": 22,
        "timeout": 30,
        "session_log": True,
    },
    {
        "name": "RG-S5760C-核心1",
        "host": "10.1.1.10",
        "device_type": "ruijie_os",
        "username": "admin",
        "password": "YourPassword",
        "port": 22,
    },
    {
        "name": "RG-S5760C-核心2",
        "host": "10.1.1.11",
        "device_type": "ruijie_os",
        "username": "admin",
        "password": "YourPassword",
        "port": 22,
    },
    {
        "name": "RG-S5760C-核心3",
        "host": "10.1.1.12",
        "device_type": "ruijie_os",
        "username": "admin",
        "password": "YourPassword",
        "port": 22,
    },
    {
        "name": "RG-S5310-接入1",
        "host": "10.1.1.20",
        "device_type": "ruijie_os",
        "username": "admin",
        "password": "YourPassword",
        "port": 22,
    },
    {
        "name": "RG-S5310-接入2",
        "host": "10.1.1.21",
        "device_type": "ruijie_os",
        "username": "admin",
        "password": "YourPassword",
        "port": 22,
    },
    {
        "name": "RG-S5310-接入3",
        "host": "10.1.1.22",
        "device_type": "ruijie_os",
        "username": "admin",
        "password": "YourPassword",
        "port": 22,
    },
    {
        "name": "RG-S5310-接入4",
        "host": "10.1.1.23",
        "device_type": "ruijie_os",
        "username": "admin",
        "password": "YourPassword",
        "port": 22,
    },
    {
        "name": "RG-WS6008-无线AC",
        "host": "10.1.1.30",
        "device_type": "ruijie_os",
        "username": "admin",
        "password": "YourPassword",
        "port": 22,
    },
    {
        "name": "RG-EG3230-外网网关",
        "host": "10.1.1.2",
        "device_type": "ruijie_os",
        "username": "admin",
        "password": "YourPassword",
        "port": 22,
    },
    {
        "name": "H3C-F1000-AK155-防火墙",
        "host": "10.1.1.50",
        "device_type": "hp_comware",   # 华三 Comware 系列
        "username": "admin",
        "password": "YourPassword",
        "port": 22,
    },

    # ---- 二楼 / 核心机房（华为） ----
    {
        "name": "Huawei-S5735-内网核心",
        "host": "10.2.1.1",
        "device_type": "huawei",
        "username": "admin",
        "password": "YourPassword",
        "port": 22,
    },
    {
        "name": "Huawei-S5735-外网核心",
        "host": "10.2.1.2",
        "device_type": "huawei",
        "username": "admin",
        "password": "YourPassword",
        "port": 22,
    },
    {
        "name": "Huawei-USG6000E-防火墙",
        "host": "10.2.1.10",
        "device_type": "huawei",
        "username": "admin",
        "password": "YourPassword",
        "port": 22,
    },
    {
        "name": "Huawei-AR6300-S-核心路由器",
        "host": "10.2.1.20",
        "device_type": "huawei",
        "username": "admin",
        "password": "YourPassword",
        "port": 22,
    },
]


# ============================================================
# 2. 采集命令清单（通用）
# ============================================================
# 注意：不同厂商命令略有差异，详见各设备手册
COMMANDS = {
    "ruijie_os": [
        "show version",
        "show running-config",
        "show startup-config",
        "show clock",
        "show ip interface brief",
        "show interface brief",
        "show vlan brief",
        "show ip route",
        "show cpu",
        "show memory",
        "show log",
    ],
    "hp_comware": [  # 华三
        "display version",
        "display current-configuration",
        "display saved-configuration",
        "display clock",
        "display ip interface brief",
        "display interface brief",
        "display vlan brief",
        "display ip routing-table",
        "display cpu-usage",
        "display memory-usage",
        "display logbuffer",
    ],
    "huawei": [
        "display version",
        "display current-configuration",
        "display saved-configuration",
        "display clock",
        "display ip interface brief",
        "display interface brief",
        "display vlan",
        "display ip routing-table",
        "display cpu-usage",
        "display memory-usage",
        "display logbuffer",
    ],
    "cisco_ios": [
        "show version",
        "show running-config",
        "show startup-config",
        "show clock",
        "show ip interface brief",
        "show vlan brief",
        "show ip route",
        "show cpu",
        "show memory",
        "show log",
    ],
}


# ============================================================
# 3. 主流程
# ============================================================
def collect_device(device, output_dir):
    """采集单台设备"""
    name = device["name"]
    host = device["host"]
    device_type = device["device_type"]
    print(f"\n[{name}] {host} - 采集中...")

    commands = COMMANDS.get(device_type, [])
    if not commands:
        print(f"  ⚠️ 没有为 {device_type} 配置命令，跳过")
        return False

    # 设备独立文件夹
    device_dir = output_dir / name
    device_dir.mkdir(parents=True, exist_ok=True)

    # session log（可选，记录所有交互）
    session_log_path = device_dir / "session.log"

    success = True
    try:
        # 连接参数
        connect_params = {
            "device_type": device_type,
            "host": host,
            "username": device["username"],
            "password": device["password"],
            "port": device.get("port", 22),
            "timeout": device.get("timeout", 30),
            "session_log": session_log_path if device.get("session_log", False) else None,
        }

        # 禁用 enable 密码（如果设备不需要）
        if "secret" in device:
            connect_params["secret"] = device["secret"]

        with ConnectHandler(**connect_params) as conn:
            # 跑命令
            for cmd in commands:
                try:
                    # 安全化命令名（用于文件名）
                    safe_cmd = cmd.replace(" ", "_").replace("/", "_")
                    output_file = device_dir / f"{safe_cmd}.txt"

                    print(f"  → {cmd}")
                    output = conn.send_command(
                        cmd,
                        read_timeout=60,
                        expect_string=r"[#>]",
                    )

                    # 写文件
                    with open(output_file, "w", encoding="utf-8") as f:
                        f.write(f"=== {cmd} ===\n")
                        f.write(f"采集时间: {datetime.now().isoformat()}\n")
                        f.write(f"设备: {name} ({host})\n")
                        f.write("=" * 60 + "\n\n")
                        f.write(output)

                except Exception as e:
                    print(f"  ❌ 命令 {cmd} 失败: {e}")
                    with open(device_dir / "errors.log", "a", encoding="utf-8") as f:
                        f.write(f"[{datetime.now()}] {cmd}: {e}\n")

    except NetMikoAuthenticationException:
        print(f"  ❌ 认证失败")
        success = False
    except NetMikoTimeoutException:
        print(f"  ❌ 连接超时")
        success = False
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        success = False

    if success:
        print(f"  ✅ 完成 -> {device_dir}")
    return success


def main():
    """主入口"""
    # 输出目录
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_root = Path(__file__).parent.parent / "04-配置备份" / f"采集结果-{timestamp}"
    output_root.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"网络设备批量信息采集 - 启动")
    print(f"设备数: {len(DEVICES)}")
    print(f"输出目录: {output_root}")
    print(f"开始时间: {datetime.now().isoformat()}")
    print("=" * 70)

    # 汇总结果
    success_list = []
    failed_list = []

    # 逐台采集（顺序执行，避免触发安全告警）
    for i, device in enumerate(DEVICES, 1):
        print(f"\n[{i}/{len(DEVICES)}]", end=" ")
        if collect_device(device, output_root):
            success_list.append(device["name"])
        else:
            failed_list.append(device["name"])

    # 汇总报告
    report_file = output_root / "采集汇总.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"# 设备信息采集汇总\n\n")
        f.write(f"**采集时间**: {datetime.now().isoformat()}\n\n")
        f.write(f"**设备总数**: {len(DEVICES)}\n")
        f.write(f"**成功**: {len(success_list)}\n")
        f.write(f"**失败**: {len(failed_list)}\n\n")
        f.write(f"## 成功设备\n\n")
        for name in success_list:
            f.write(f"- ✅ {name}\n")
        f.write(f"\n## 失败设备\n\n")
        for name in failed_list:
            f.write(f"- ❌ {name}\n")
        f.write(f"\n## 下一步\n\n")
        f.write(f"1. 检查失败设备的 errors.log\n")
        f.write(f"2. 对比每台设备的 running-config 和 startup-config（应一致）\n")
        f.write(f"3. 检查接口错包、CPU/内存异常\n")
        f.write(f"4. 整理输出到 `06-资产与拓扑/` 下的资产清单和拓扑图\n")

    print("\n" + "=" * 70)
    print(f"完成！成功: {len(success_list)} / 失败: {len(failed_list)}")
    print(f"汇总: {report_file}")
    print("=" * 70)

    return 0 if not failed_list else 1


if __name__ == "__main__":
    sys.exit(main())

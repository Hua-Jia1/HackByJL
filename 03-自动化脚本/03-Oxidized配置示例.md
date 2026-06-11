# Oxidized 配置示例（自建自动备份系统）

> **Oxidized** 是开源的网络设备配置备份系统，支持 70+ 厂商，会自动 diff 配置变更并告警。
> **官网**：https://github.com/ytti/oxidized
> **Web UI**：https://github.com/ytti/oxidized-web

---

## 1. 安装（Linux 建议 Ubuntu/Debian）

```bash
# 安装依赖
sudo apt update
sudo apt install -y ruby ruby-dev libsqlite3-dev libssl-dev libssh2-1-dev gcc make

# 安装 Oxidized
sudo gem install oxidized
sudo gem install oxidized-script
sudo gem install oxidized-web

# 初始化配置
sudo oxidized
```

---

## 2. 配置文件 `/etc/oxidized/config`

```yaml
---
username: admin
password: YourPassword              # 默认密码，所有设备共用
# 也可以按设备用 model map 覆盖（见下）

# 备份间隔（秒）
interval: 86400                    # 每天一次
# interval: 3600                  # 每小时一次

# 日志
log: /var/log/oxidized/oxidized.log

# 数据存储（SQLite 即可）
source:
  default: csv
  csv:
    file: "/var/lib/oxidized/.config/oxidized/router.db"
    delimiter: !ruby/regexp /:/
    map:
      name: 0
      ip: 1
      model: 2
      group: 3
      username: 4
      password: 5

# 目标存储（Git，最推荐，天然有版本控制）
input:
  default: ssh, telnet
  debug: false
  ssh:
    secure: false                  # 自签证书可以关
  telnet:
    inspect: false

# 模型映射（设备类型 → Oxidized 支持的 model）
model:
  ruijie_os:
    username: admin
    password: YourPassword
  hp_comware:
    username: admin
    password: YourPassword
  huawei:
    username: admin
    password: YourPassword
  cisco_ios:
    username: admin
    password: YourPassword

# 输出（Git）
output:
  default: git
  git:
    user: Oxidized
    email: oxidized@example.com
    repo: "/var/lib/oxidized/.config/oxidized/git-repos/default.git"

# 钩子（变更告警）
hooks:
  email:                            # 邮件告警
    to: ops@example.com
    from: oxidized@example.com
    smtp: smtp.example.com
    smtp_port: 587
    # ...
  slack:                            # Slack 告警
    server: hooks.slack.com
    token: xoxb-xxx
    channel: "#ops"
    username: Oxidized
  # 自定义 webhook
  http:
    url: http://your-server/webhook
    method: post
    body: '{"text": "Config changed on {{name}}"}'
```

---

## 3. 设备清单 `/var/lib/oxidized/.config/oxidized/router.db`

CSV 格式：`name:ip:model:group:username:password`

```
RG-EG3220-内网网关:10.1.1.1:ruijie_os:一楼业务:admin:YourPassword
RG-S5760C-核心1:10.1.1.10:ruijie_os:一楼业务:admin:YourPassword
RG-S5760C-核心2:10.1.1.11:ruijie_os:一楼业务:admin:YourPassword
RG-S5760C-核心3:10.1.1.12:ruijie_os:一楼业务:admin:YourPassword
RG-S5310-接入1:10.1.1.20:ruijie_os:一楼业务:admin:YourPassword
RG-S5310-接入2:10.1.1.21:ruijie_os:一楼业务:admin:YourPassword
RG-S5310-接入3:10.1.1.22:ruijie_os:一楼业务:admin:YourPassword
RG-S5310-接入4:10.1.1.23:ruijie_os:一楼业务:admin:YourPassword
RG-WS6008-无线AC:10.1.1.30:ruijie_os:一楼业务:admin:YourPassword
RG-EG3230-外网网关:10.1.1.2:ruijie_os:一楼业务:admin:YourPassword
H3C-F1000-AK155-防火墙:10.1.1.50:hp_comware:一楼业务:admin:YourPassword
Huawei-S5735-内网核心:10.2.1.1:huawei:二楼核心:admin:YourPassword
Huawei-S5735-外网核心:10.2.1.2:huawei:二楼核心:admin:YourPassword
Huawei-USG6000E-防火墙:10.2.1.10:huawei:二楼核心:admin:YourPassword
Huawei-AR6300-S-核心路由器:10.2.1.20:huawei:二楼核心:admin:YourPassword
```

---

## 4. 启动服务

### 4.1 一次性运行（测试）

```bash
sudo oxidized
```

### 4.2 systemd 服务

`/etc/systemd/system/oxidized.service`：

```ini
[Unit]
Description=Oxidized - Network Device Configuration Backup
After=network.target

[Service]
Type=simple
User=oxidized
Group=oxidized
ExecStart=/usr/local/bin/oxidized
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now oxidized
sudo systemctl status oxidized
```

### 4.3 启动 Web UI

```bash
oxidized-web --port 8888 --no-daemonize
```

访问 `http://<服务器IP>:8888/`，可以看到所有设备列表、配置历史、diff。

---

## 5. 日常使用

### 5.1 查看备份历史

```bash
cd /var/lib/oxidized/.config/oxidized/git-repos/default.git
git log --oneline --all
# 看每次变更的 commit
```

### 5.2 看某次变更的 diff

```bash
git show <commit-hash>
```

### 5.3 恢复某台设备的某次配置

```bash
cd /var/lib/oxidized/.config/oxidized/git-repos/default.git
git show <commit-hash>:<设备名>.conf > /tmp/old-config.txt
# 然后手动灌入设备（小心）
```

---

## 6. 常见问题

### 6.1 备份失败

- 检查 SSH 端口（很多防火墙开了 22 但其它不行）
- 检查账号密码
- 检查设备 model 名称（Oxidized 用 model 决定命令）

### 6.2 SSH 指纹问题

在 `/etc/oxidized/config` 加：
```yaml
input:
  ssh:
    secure: false
```

### 6.3 性能问题

设备多就拆多台 Oxidized 节点，每节点管一批。

---

## 7. Windows 上跑（不推荐，但能跑）

Oxidized 是 Ruby 应用，Windows 上需要：
- RubyInstaller
- Git for Windows

配置基本一样，但 systemd 服务换成 Windows 任务计划或 NSSM 包装成服务。

> **建议**：备份服务器用 Linux 机器，长期稳定。

---

## 8. 与 Python 备份脚本的选择

| 特性 | Oxidized | Python 脚本 |
|------|----------|------------|
| 安装复杂度 | 中 | 低 |
| 厂商支持 | 70+ | 自己写 |
| Web UI | 有（oxidized-web） | 无 |
| 变更告警 | 内置（email/slack） | 自己写 |
| 配置历史 | Git 天然有 | 自己存 |
| 适合规模 | 中大规模 | 小规模 / 临时 |

**推荐**：设备 < 10 台用 Python 脚本，> 10 台用 Oxidized。

# N-core 添加 Vlan10/20/30 SVI 零中断迁移方案

> 创建日期: 2026-06-17
> 项目: 9号机柜网络架构梳理 + SVI 迁移
> 适用: 医院老院区 (Vlan10/20/30) L3 网关从 H3C Core1 迁到 Ruijie N-core (RG-S5760C)
> 状态: 待阶段0 摸底 + Vlan30 物理通道确认

---

## 一、背景与硬约束

- **业务目标**: 将 Vlan10/20/30 的 L3 网关功能从 H3C Core1 (`YKZZY-HEXIN-SW-1`) 迁移到 N-core (Ruijie `RG-S5760C`).
- **业务约束**: Vlan10/20/30 当前仍有活跃业务, 不可中断 (用户原话: "断网了就玩完了").
- **维护窗口**: 基本上 0 窗口.
- **历史故障**: 之前测试在 N-core 上加 SVI Vlan10/20/30 + IP `192.168.10.1/20.1/30.1` → 立即触发 Vlan200 断网 (2 个科室受影响, 需人工干预) → 回滚 SVI → 恢复.
- **故障复现性**: 100%.

---

## 二、硬阻塞 (从配置直接验证)

### 2.1 IP 冲突

`H3C Core1` (`_parsed_H3C_Core1.txt`) 已配置:

```
interface Vlan-interface10
 ip address 192.168.10.1 255.255.255.0
interface Vlan-interface20
 ip address 192.168.20.1 255.255.255.0
interface Vlan-interface30
 ip address 192.168.30.1 255.255.255.0
```

`H3C Core2` 对应物理 IP 为 `.2`.

**用户最初想在 N-core 上配的 `192.168.10.1/24, 20.1/24, 30.1/24` 与 H3C Core1 物理 IP 完全相同**. 这是导致 Vlan200 断网的最可能原因 (duplicate IP 通过共享 L2 路径引发异常).

### 2.2 DHCP default-router 与 VRRP 虚拟 IP 不一致

N-core 当前 DHCP pool:

```
ip dhcp pool vlan10: default-router 192.168.10.1
ip dhcp pool vlan20: default-router 192.168.20.1
ip dhcp pool vlan30: default-router 192.168.30.1
```

H3C 上 VRRP 虚拟 IP:

```
Vlan10 VRRP virtual: 192.168.10.254
Vlan20 VRRP virtual: 192.168.20.254
Vlan30 VRRP virtual: 192.168.30.254
```

⚠️ **客户端实际拿到的网关是 `10.1/20.1/30.1` (H3C 物理 IP), 绕过了 H3C 的 VRRP 冗余机制**. 这是为什么 H3C Core1 一旦有故障, 客户端不会自动切换到 H3C Core2 (它们直接指向 .1 而非 .254).

### 2.3 Vlan30 物理通道缺失

N-core trunk 配置:

```
interface GigabitEthernet 1/0/20
 switchport mode trunk
 switchport trunk allowed vlan only 4,10,20,200-205
```

**Trunk Gi1/0/20 允许的 VLAN 不包含 Vlan30**. N-core 的 SVI Vlan30 没有物理链路通往 H3C 那一侧. 需要确认 Vlan30 的实际拓扑位置 (见第五章).

---

## 三、路径分析

### 3.1 路径对比

| 维度 | 路径 A: 用 10.3 + VRRP | 路径 B: 用 10.1 + 切换 |
|------|----------------------|----------------------|
| 物理 IP (N-core) | `10.3/20.3/30.3` | `10.1/20.1/30.1` |
| 切换方式 | VRRP 优先级调整 | shutdown 旧 + up 新 |
| 客户端中断 | **0** | 30-90 秒 |
| DHCP 改动 | 需改 default-router `10.1 → 10.254` | 不改 |
| 物理 IP 一致性 | 与 H3C 不一致 | 与 H3C 保持一致 |
| 实施复杂度 | 中 (分阶段) | 高 (需精确编排) |
| 适用场景 | Vlan10/20/30 有业务, 0 窗口 | 有可接受的短窗口 |

### 3.2 路径选择结论

**Vlan10/20/30 仍有业务 + 0 窗口 = 路径 A 是唯一选项**.

理由: `10.1/20.1/30.1` 与 H3C Core1 物理 IP 冲突, 物理 IP 在同一 L2 广播域内只能属于一个设备. 强制使用 10.1 必然触发 100% 复现的 Vlan200 断网.

### 3.3 网关与物理 IP 概念澄清

| 类型 | 当前值 | 路径 A 实施后 | 用途 |
|------|--------|-------------|------|
| H3C 物理 IP | `10.1/20.1/30.1` | 保留 (作为 VRRP Backup) | H3C 自己的路由 |
| H3C VRRP 虚拟 IP | `10.254/20.254/30.254` | 仍存在 (但 Master 在 N-core) | 应作为客户端网关 |
| N-core 物理 IP | (无) | `10.3/20.3/30.3` | N-core 自己的路由 |
| N-core VRRP 虚拟 IP | (无) | `10.254/20.254/30.254` (作为 Master) | 实际作为客户端网关 |
| 客户端 default-router | `10.1/20.1/30.1` (旧) | `10.254/20.254/30.254` (新) | 客户端真正使用的网关 |

**关键**: 客户端感知的是网关 IP (default-router), 不是物理 IP. VRRP 虚拟 IP 漂移时, 客户端无感.

---

## 四、实施步骤 (路径 A, Vlan10/Vlan20 部分)

> Vlan30 待物理通道确认后单独处理 (见第五章).

### 阶段0: 状态摸底 (0 变更)

**H3C Core1 / Core2**:

```bash
display vrrp brief
display interface Vlan-interface 10
display interface Vlan-interface 20
display interface Vlan-interface 30
```

**N-core**:

```bash
show switch virtual
show ip route
show running-config interface vlan 100
show running-config interface vlan 255
show arp count
show running-config interface GigabitEthernet 1/0/20
```

**目的**: 确认 VRRP 主备状态、VSU 状态、trunk 实际允许的 VLAN、ARP 表规模.

### 阶段1: N-core 加 SVI Vlan10/20 (0 客户端感知)

```bash
# N-core 上:
configure terminal
vlan 10
 name xingzhengbangong
vlan 20
 name yijishebei
exit

interface vlan 10
 ip address 192.168.10.3 255.255.255.0
 vrrp 1 ip 192.168.10.254
 vrrp 1 priority 50
 no shutdown
exit

interface vlan 20
 ip address 192.168.20.3 255.255.255.0
 vrrp 2 ip 192.168.20.254
 vrrp 2 priority 50
 no shutdown
exit
end
```

**本阶段回退命令** (任一阶段都保留):

```bash
# N-core 上:
configure terminal
no interface vlan 10
no interface vlan 20
end
```

**本阶段效果**:
- H3C Core1 仍是 Vlan10/20 的 VRRP Master (priority 110)
- N-core 是 Backup (priority 50)
- 客户端完全无感
- **Vlan200 业务不受影响** (没有 duplicate IP, 不会复现之前的事故)

### 阶段2: 改 DHCP default-router

```bash
# N-core 上:
configure terminal
ip dhcp pool vlan10
 default-router 192.168.10.254
 lease 0 0 5
exit
ip dhcp pool vlan20
 default-router 192.168.20.254
 lease 0 0 5
exit
end
```

**本阶段效果**:
- 当前在线客户端: 仍用 `10.1/20.1` (旧租约), 业务不变
- 5 分钟后自动续约的客户端: 开始用 `10.254/20.254`
- 1-2 小时后几乎所有客户端都续约过了
- **业务无感** (续约透明, TCP 会话不会断)

### 阶段3: VRRP Master 切换 (1-3 秒, 客户端无感)

**先在 H3C Core1 上把 priority 调低**:

```bash
# H3C Core1 上:
system-view
interface Vlan-interface10
 vrrp vrid 1 priority 50
interface Vlan-interface20
 vrrp vrid 2 priority 50
quit
save
```

**本阶段效果**:
- VRRP 立刻切换, N-core 变成 Vlan10/20 的 Master
- 虚拟 IP `10.254/20.254` 漂到 N-core
- 已续约的客户端无感 (default-router 跟着 VRRP 走)
- 未续约的客户端继续用 `10.1/20.1`, 仍可达 H3C Core1 (其物理 IP 还在), 不中断

### 阶段4: 验证与清理 (24h 后)

```bash
# N-core 上验证:
show vrrp brief
show ip route
show arp count
```

**可选清理** (无客户端依赖后):
- 移除 H3C Core1 的物理 IP `10.1/20.1`
- DHCP lease 改回原时长 (几小时/几天)
- 移除 N-core SVI Vlan10/20 的 VRRP (如果不再需要 H3C 备份)

---

## 五、Vlan30 处理 (待确认)

### 待确认问题

1. Vlan30 客户端是否在 H3C 侧?
2. 是否有别的 trunk 端口承载 Vlan30?
3. Vlan30 客户端是否可以接受 0 中断 (与 Vlan10/20 同等要求)?

### 可能的处理方式

| Vlan30 客户端位置 | 处理方式 |
|----------------|---------|
| 在 H3C 侧, 且 N-core 有 trunk 到该侧 | 类似 Vlan10/20, 走路径 A (SVI IP 用 30.3, VRRP priority 50 → 150) |
| 在 N-core 侧 | 直接在 N-core 加 SVI Vlan30, IP 用 30.3, **无需 VRRP** |
| 暂未使用 | 暂不处理, 等业务上线前再规划 |

---

## 六、风险与回退

### 风险清单

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 阶段1 加 SVI 后 Vlan200 仍断 | 极低 (用 10.3 无 duplicate IP) | Vlan200 业务中断 | 立即执行回退命令 |
| VRRP 切换时丢包 | 低 (1-3 秒) | 客户端瞬时丢包 | 选择业务低峰期操作 |
| DHCP 续约时延过长 | 低 (lease 已缩到 5 分钟) | 部分客户端延后迁移 | 监控续约率 |
| H3C Core1 与 N-core VRRP 状态不一致 | 极低 | VRRP 切换异常 | 阶段0 必须验证 |
| N-core VSU 堆叠分裂 | 极低 | 全部 N-core 业务中断 | 阶段0 必须验证 VSU 状态 |

### 紧急回退预案 (任何阶段, 30 秒内恢复)

```bash
# N-core 上:
configure terminal
no interface vlan 10
no interface vlan 20
end

# H3C Core1 上恢复 priority 110:
system-view
interface Vlan-interface10
 vrrp vrid 1 priority 110
interface Vlan-interface20
 vrrp vrid 2 priority 110
quit
save
```

---

## 七、待确认事项 (TODO)

- [ ] 跑阶段0 命令, 把输出贴回本会话
- [ ] 确认 Vlan30 客户端位置 (H3C 侧 / N-core 侧 / 暂未使用)
- [ ] 确认是否有别的 trunk 承载 Vlan30
- [ ] 确认 H3C Core1 的 VRRP 状态 (阶段0 输出)
- [ ] 确认 N-core Vlan100 / Vlan255 IP 状态 (阶段0 输出)
- [ ] 确认 N-core VSU 堆叠状态 (阶段0 输出)

---

## 八、引用配置与文档

- 源配置: `C:\机房配置\9机柜\_parsed\_parsed_H3C_Core1.txt`
- 源配置: `C:\机房配置\9机柜\_parsed\_parsed_H3C_Core2.txt`
- 源配置: `C:\机房配置\9机柜\_parsed\_parsed_HJ_S5120V2.txt` (Vlan100 server switch, 与 N-core Vlan100 互通)
- 源配置: `C:\机房配置\9机柜\_parsed\_parsed_W-HJ3.txt` (W-core, 确认 trunk 允许 vlan 2-4094)
- 项目梳理: `C:\HackByJL\HackByJL\9号机柜-网络架构梳理\00-总览.md`
- 项目梳理: `C:\HackByJL\HackByJL\9号机柜-网络架构梳理\01-老院内网-H3C.md`
- 项目梳理: `C:\HackByJL\HackByJL\9号机柜-网络架构梳理\02-新院内网-Ruijie.md`
- 项目梳理: `C:\HackByJL\HackByJL\9号机柜-网络架构梳理\05-路由总览.md`
- 项目梳理: `C:\HackByJL\HackByJL\9号机柜-网络架构梳理\已知事实清单.md`

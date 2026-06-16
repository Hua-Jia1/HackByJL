# N-core #1 — 锐捷 RG-S5760C

> **机柜位置**:U29
> **角色**:内网核心交换机 1(VSU 堆叠成员)
> **原始文件**:`N-core #1  RG-S5760C (锐捷).text`
> **冗余**:与 U28 的 N-core #2 完全相同配置,做 VSU 堆叠或独立冷备

## 基本信息

| 项目 | 值 |
|------|-----|
| 主机名 | N-CORE |
| 软件版本 | S5760X_RGOS 12.6(2)B0702P1 |
| 设备型号 | S5760C-24SFP/8GT8XS-X ×2(堆叠) |
| 系统 MAC | d431.27d2.fc9e |
| 管理 IP | 192.168.1.200(VLAN 1/Mgmt) |
| 堆叠 | switch virtual domain 1(2 台成员) |

## 堆叠配置

```
install switch 1 S5760C-24SFP/8GT8XS-X
install switch 2 S5760C-24SFP/8GT8XS-X
install 1/0 S5760C-24SFP/8GT8XS-X
install 2/0 S5760C-24SFP/8GT8XS-X
!
switch virtual domain 1
```

> 注意 `N-core #1` 和 `N-core #2` 文件内容**完全相同**(对比:主机名/堆叠/MAC/路由/策略/VLAN 都一致),疑为同一个堆叠组的备份配置文件。两份都被命名为"#1""#2",但实际可能是同一 VSU 系统的两个成员。

## VLAN 与 SVI

| VLAN | 描述 | 网关 IP |
|------|------|---------|
| 1 | 默认 | — |
| 4 | vlan004 | — |
| 10 | 行政办公 | 192.168.10.1/24(DHCP) |
| 20 | 一级医技 | 192.168.20.1/24(DHCP) |
| 30 | 所有科室 | (路由) |
| 40 | (DHCP 客户端) | — |
| 100 | (vlan range 包含) | 192.168.254.253/25 — 互联内网网关 EG3220 |
| 200 | 内网办公主 | 192.168.200.1/24(DHCP) |
| 201 | 办公/打印机 | 192.168.201.1/24(DHCP) |
| 202 | 视频会议 | 192.168.202.1/24(DHCP) |
| 203 | 办公 | 192.168.203.1/24(DHCP) |
| 204 | 办公 | 192.168.204.1/24(DHCP) |
| 205 | 办公 | 192.168.205.1/24(DHCP) |
| 255 | 管理 | 192.168.255.1/25 |

## DHCP 服务

> 同时为 vlan200/201/202/203/204/205/10/20/4 提供 DHCP

| 池 | 网段 | 网关 | DNS |
|----|------|------|-----|
| vlan4 | 10.12.4.0/24 | 10.12.4.1 | 223.5.5.5 |
| vlan10 | 192.168.10.0/24 | 192.168.10.1 | 223.5.5.5 |
| vlan20 | 192.168.20.0/24 | 192.168.20.1 | 223.5.5.5 |
| vlan200 | 192.168.200.0/24 | 192.168.200.1 | — |
| vlan201 | 192.168.201.0/24 | 192.168.201.1 | 114.114.114.114 |
| vlan202 | 192.168.202.0/24 | 192.168.202.1 | 114.114.114.114 |
| vlan203 | 192.168.203.0/24 | 192.168.203.1 | 114.114.114.114 |
| vlan204 | 192.168.204.0/24 | 192.168.204.1 | 114.114.114.114 |
| vlan205 | 192.168.205.0/24 | 192.168.205.1 | 114.114.114.114 |

## 关键接口

| 接口 | 配置 | 说明 |
|------|------|------|
| Gi1/0/1 | port-group 10 | →内网网关 EG3220(AggregatePort 10) |
| Gi2/0/1 | port-group 10 | 同上,聚合 10 |
| Gi1/0/8 | port-group 8 | →AP/无线上行(AggregatePort 8,access vlan 100) |
| Gi2/0/8 | port-group 8 | 同上 |
| Gi1/0/20 | trunk vlan 4,10,20,200-205 | →H3C 核心/汇聚? |
| Gi1/0/21 | trunk | 备用 trunk |
| Gi2/0/21 | trunk | 备用 trunk |
| TenGi1/0/27-32 | port-group 1-6 | 万兆聚合(6 条) |
| TenGi2/0/27-32 | port-group 1-6 | 同上 |

### AggregatePort(链路聚合)

| AG | 模式 | 说明 |
|----|------|------|
| Ag1-6 | trunk 2-4094 | 万兆上联(各 2 成员) |
| Ag7 | — | 未配置 |
| Ag8 | access vlan 100 | 无线/AP 上联(`address-bind uplink` 指向这里) |
| Ag10 | trunk | →内网网关 EG3220(Gi0/6+Gi0/7) |

## 路由

```
ip route 10.121.0.0 255.255.0.0 192.168.254.254     # →内网网关 EG3220
ip route 10.121.0.0 255.255.255.0 192.168.254.254
ip route 10.121.81.0 255.255.255.0 192.168.254.254
ip route 192.168.2.2 255.255.255.255 192.168.254.254
ip route 192.168.10.0 255.255.255.0 192.168.254.254
ip route 192.168.20.0 255.255.255.0 192.168.254.254
ip route 192.168.30.0 255.255.255.0 192.168.254.254
ip route 192.168.40.0 255.255.255.0 192.168.254.254
ip route 192.168.50.0 255.255.255.0 192.168.254.254
ip route 192.168.60.0 255.255.255.0 192.168.254.254
ip route 192.168.70.0 255.255.255.0 192.168.254.254
# 所有 VLAN 间路由指向内网网关 EG3220(192.168.254.254)
```

> **注**:核心交换机自身没有默认路由出口,所有跨 VLAN 流量都经内网网关,EG3220 起到统一出口作用。

## 地址绑定(address-bind,防 ARP 欺骗)

```
address-bind uplink AggregatePort 8
address-bind 10.12.4.6     3448.edf9.0f05
address-bind 192.168.200.11 6c4b.90ad.2717
... 共 130+ 条 ...
```

> 大量 IP-MAC 静态绑定,主要为办公终端;`uplink AggregatePort 8` 表示绑定表仅生效在 AP 上联口。

## 安全 / SSH / SNMP

- SSH:启用,使用强算法(dh_group14_sha1, ecdh_sha2_*, sm2dh_sm3)
- SNMP:v3 only,3 次失败锁 5 分钟
- 密码策略:至少 8 位、强密码
- 启用 Web (HTTP/HTTPS)
- Telnet 启用

## 完整原始配置

参见 `../设备原始配置/N-core #1  RG-S5760C (锐捷).text`(同目录原文,533 行)。

```text
version S5760X_RGOS 12.6(2)B0702P1
hostname N-CORE
!
spanning-tree
!
username admin password 7 $10$1a7$3rsQYUPXJ8Szfg==$
!
no cwmp
!
service dhcp
!
ip dhcp pool vlan201
 network 192.168.201.0 255.255.255.0
 dns-server 114.114.114.114
 default-router 192.168.201.1
!... (其余 DHCP 池省略,见上表)
!
ip dhcp pool vlan4
 network 10.12.4.0 255.255.255.0
 dns-server 223.5.5.5
 default-router 10.12.4.1
!
install switch 1 S5760C-24SFP/8GT8XS-X
install switch 2 S5760C-24SFP/8GT8XS-X
install 1/0 S5760C-24SFP/8GT8XS-X
install 2/0 S5760C-24SFP/8GT8XS-X
!
sysmac d431.27d2.fc9e
!
webmaster level 0 username admin secret 8 $1c$7eyy23uMQk$0`4,rb0jf0#(&4|~<:l~,,d#.>l0z.td(nfxv2v!$
enable service web-server http
enable service web-server https
!
nfpp
!
password policy printable-character-check
password policy min-size 8
password policy strong
service password-encryption
!
redundancy
!
no enable service snmp-agent
ip ssh key-exchange dh_group14_sha1 ecdh_sha2_nistp256 ecdh_sha2_nistp384 ecdh_sha2_nistp521 sm2dh_sm3
ip ssh cipher-mode ctr gcm
ip ssh hmac-algorithm sha2-256 sha2-512 sm3
no logging on
!
login privilege log
enable secret 8 $1c$7eyy23uMQk$0`4,rb0jf0#(&4|~<:l~,,d#.>l0z.td(nfxv2v!$
enable password 7 $10$1b9$4xHCraQE1Co/ow==$
enable service ssh-server
enable service telnet-server
!
vlan 4
 name vlan004
!
vlan range 1,10,20,30,40,100,200-212,255
!
interface GigabitEthernet 1/0/1
 port-group 10
!... (其余接口详见原始文件)
!
interface VLAN 100
 ip address 192.168.254.253 255.255.255.128
!
interface VLAN 200
 ip address 192.168.200.1 255.255.255.0
!... (其余 SVI 详见上表)
!
address-bind uplink AggregatePort 8
address-bind 10.12.4.6 3448.edf9.0f05
address-bind 192.168.200.11 6c4b.90ad.2717
!... (130+ 条 address-bind 详见原始文件)
address-bind install
!
switch virtual domain 1
!
ip route 10.121.0.0 255.255.0.0 192.168.254.254
!... (路由表见上)
!
snmp-server logging set-operation
no snmp-server enable version v1
no snmp-server enable version v2c
snmp-server enable version v3
snmp-server enable secret-dictionary-check
snmp-server authentication attempt 3 exceed lock-time 5
!
line console 0
line vty 0 4
 login local
 password 7 $10$04b$1cqMYcIJBDFnqA==$
!
end
```

# W-core — 锐捷 RG-S5760C(无线核心)

> **机柜位置**:U33
> **角色**:外网/无线核心交换机
> **原始文件**:`W-core  RG-S5760C (锐捷).txt` + `外网S5760C.text`(两份不完全相同的备份)
> **冗余**:与外网网关 RG-1G3230(EG3230)直接连接,Gi0/6 ⇄ G0/7

## 基本信息

| 项目 | 值 |
|------|-----|
| 主机名 | W-CORE |
| 软件版本 | S5760X_RGOS 12.6(2)B0702P1 |
| 设备型号 | S5760C-24SFP/8GT8XS-X |
| 系统 MAC | d431.27d2.fd16 |
| 管理 IP | 192.168.1.200(VLAN 1/Mgmt) |
| 默认路由 | 0.0.0.0/0 → 192.168.255.254(→EG3230) |

## 两份配置差异说明 ⚠️

**重要**:`W-core.txt` 与 `外网S5760C.text` 是同一台设备的**两份不同备份**,需现场确认实际生效版本:

| 接口 | W-core.txt | 外网S5760C.text |
|------|------------|-----------------|
| Gi0/2 | access vlan 240 | access vlan 240 |
| Gi0/3 | access vlan 1022 | access vlan 1022 |
| Gi0/4 | access vlan 251(jigui2-3536U-OAServer-GE1) | access vlan 251 |
| Gi0/5 | access vlan 240 | **trunk 2-4094** |
| Gi0/6 | trunk 2-4094 | trunk 2-4094 |
| Gi0/7 | no switchport; 192.168.255.253/25 | no switchport; 192.168.255.253/25 |

> 推测 `W-core.txt` 较早,Gi0/5 后改为 trunk 用作上联/AP 接入。本文档以 `W-core.txt`(更新版本)为基准。

## VLAN 与 SVI

| VLAN | 网段 | 用途 |
|------|------|------|
| 1 | dhcp/mix 192.168.1.200 | 管理 |
| 100 | (在 vlan range 内) | 互联 AP |
| 200 | 192.168.200.1/24 | 无线 AC 管理、办公 |
| 236 | 192.168.236.1/22 | STA 客户端(覆盖 1024 地址) |
| 240 | 192.168.240.1/24 | 无线业务 |
| 241-249 | 192.168.241-249.1/24 | 无线业务 |
| 250 | 192.168.250.1/24 | 无线业务 |
| 251 | 192.168.251.1/24 | OA 服务器对接(Gi0/4) |
| 252 | 192.168.252.1/24 | 备用 |
| 254 | 192.168.254.1/24 | AP DHCP(option 138 → AC) |
| 255 | 192.168.255.1/25 | 与 EG3230 互联 |
| 1022 | 10.30.30.2/24 | Gi0/3 直连 |

## DHCP 服务

| 池 | 网段 | 网关 | 备注 |
|----|------|------|------|
| `ap_pool` | 192.168.254.0/24 | 192.168.254.1 | **option 138 → 192.168.200.3**(AC) |
| vlan240 | 192.168.240.0/24 | 192.168.240.1 | DNS 114.114.114.114 |
| vlan241-249 | 同名网段 | 同名 | DNS 114.114.114.114 |
| vlan250 | 192.168.250.0/24 | 192.168.250.1 | DNS 114.114.114.114 |
| `sta_pool` | 192.168.236.0/22 | 192.168.236.1 | 客户端(覆盖 236.0-239.255) |

## 关键接口

| 接口 | 配置 | 说明 |
|------|------|------|
| Gi0/1 | trunk 2-4094 | 上联核心 |
| Gi0/2 | access vlan 240 | 接入 |
| Gi0/3 | access vlan 1022 | 直连 EG3230 内网侧(10.30.30.x) |
| Gi0/4 | access vlan 251 | →jigui2-3536U-OAServer-GE1 |
| Gi0/5 | access vlan 240(W-core.txt 版本) | 接入 AP/终端 |
| Gi0/6 | trunk 2-4094 | 上联 |
| Gi0/7 | **三层口 192.168.255.253/25** | →EG3230 Gi0/6(192.168.255.254) |
| Gi0/8-24 | trunk 2-4094 | 下联 AP/接入 |
| TenGi0/25-32 | trunk 2-4094 | 万兆上联(8 条) |

## 路由

```
ip route 0.0.0.0 0.0.0.0 192.168.255.254    # →EG3230 Gi0/6
# 其他指向 EG3230 的路由在 EG3230 配置中(W-core 这边未单独配,默认即可)
```

> EG3230 侧还有:
> `ip route 10.30.30.0/24 → 192.168.255.253`
> `ip route 192.168.0.0/16 → 192.168.255.253`

## 安全 / SSH / SNMP

- SSH:启用,强算法(dh_group14_sha1, ecdh_sha2_*, sm2dh_sm3)
- SNMP:v3 only
- 密码策略:8 位+强密码
- 启用 Web (HTTP/HTTPS)
- Telnet 启用

## 与 EG3230 互联

```
W-core Gi0/7 (192.168.255.253/25) <─────> EG3230 Gi0/6 (192.168.255.254/25)
                                      192.168.255.0/25
W-core VLAN 255 SVI: 192.168.255.1/25
EG3230 VLAN 255 (Loopback 或 interface):192.168.255.254/25
```

## 完整原始配置

```text
W-CORE#show running-config
Building configuration...
Current configuration: 7300 bytes

version S5760X_RGOS 12.6(2)B0702P1
hostname W-CORE
!
username admin privilege 15 secret 8 $1c$2MjWkWWQEE$f#!r0.268lb:jh:2!d:<*jp:6d.n!!n~h<.6|(|h$
!
no cwmp
!
service dhcp
!
ip dhcp pool ap_pool
 option 138 ip 192.168.200.3
 network 192.168.254.0 255.255.255.0
 default-router 192.168.254.1
!... (其余 DHCP 池见上表)
!
install 0 S5760C-24SFP/8GT8XS-X
!
sysmac d431.27d2.fd16
ip name-server 223.5.5.5
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
!
login privilege log
enable secret 8 $1c$7eyy23uMQk$0`4,rb0jf0#(&4|~<:l~,,d#.>l0z.td(nfxv2v!$
enable password 7 $10$3a0$MhtTR6EpwN9VjQ==$
enable service ssh-server
enable service telnet-server
!
vlan range 1,100,200,236,240-255,1022
!
interface GigabitEthernet 0/1
 switchport mode trunk
 switchport trunk allowed vlan only 2-4094
!
interface GigabitEthernet 0/2
 switchport access vlan 240
!
interface GigabitEthernet 0/3
 switchport access vlan 1022
!
interface GigabitEthernet 0/4
 description jigui2-3536U-OAServer-GE1
 switchport access vlan 251
!
interface GigabitEthernet 0/5
 switchport access vlan 240    ← (W-core.txt 版本,外网S5760C.text 中为 trunk)
!
interface GigabitEthernet 0/6
 switchport mode trunk
 switchport trunk allowed vlan only 2-4094
!
interface GigabitEthernet 0/7
 no switchport
 ip address 192.168.255.253 255.255.255.128
!
!... (Gi0/8 - Gi0/24, TenGi 0/25-32 均为 trunk 2-4094)
!
interface VLAN 1
 ip address mix dhcp
 ip address mix 192.168.1.200 255.255.255.0
!
interface VLAN 200
 ip address 192.168.200.1 255.255.255.0
!
interface VLAN 236
 ip address 192.168.236.1 255.255.252.0
!
!... (VLAN 240-255, 1022 见上表)
!
interface VLAN 1022
 ip address 10.30.30.2 255.255.255.0
!
interface Mgmt 0
 ip address mix dhcp
 ip address mix 192.168.1.200 255.255.255.0
!
ip route 0.0.0.0 0.0.0.0 192.168.255.254
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
 login
 password 7 $10$2db$/Ojow9aVFNuEKA==$
!
end
```

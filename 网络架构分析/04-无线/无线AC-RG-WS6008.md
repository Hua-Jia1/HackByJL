# 无线 AP 控制器 — 锐捷 RG-WS6008

> **机柜位置**:U35-36
> **角色**:无线 AP 集中控制器
> **原始文件**:`无线 AP（网关） 控制器 AC  RG-WS6008 (锐捷).text`

## 基本信息

| 项目 | 值 |
|------|-----|
| 主机名 | (未设置) |
| 软件版本 | AC_RGOS 11.9(6)W2B1, Release(10162720) |
| 设备型号 | RG-WS6008 |
| 系统 MAC | 8005.8875.1277 |
| CAPWAP 控制器 IP | 192.168.200.3 |
| 管理 IP | Vlan-interface 200: 192.168.200.3/24 |
| CWMP | 启用(向 devicereg.ruijienetworks.com 注册) |
| MQTT | 启用 |
| 转发模式 | forward central(集中转发) |

## 无线配置

```
wlan-config 1 Zangyiyuan     ← SSID 名称
 ssid-code utf-8
 tunnel local

ap-group default
 interface-mapping 1 236 ap-wlan-id 1    ← WLAN 1 ⇄ VLAN 236

ac-controller
 capwap ctrl-ip 192.168.200.3
 no ac-control disable     ← 启用 AC 控制
 country CN
```

## 速率配置

- 802.11g:1/2/5 Mbps disabled,6+ supported,11 mandatory
- 802.11b:1/2/5 disabled,11 mandatory
- 802.11a:6/12/24 mandatory,其余 supported

> 经典企业 WiFi 配置,只允许 11/12/24 Mbps 以上。

## 安全

```
wlansec 1
 security rsn enable
 security rsn ciphers aes enable
 security rsn akm psk enable
 security rsn akm psk set-key ascii XXK123123
 security wpa enable
 security wpa ciphers aes enable
 security wpa akm psk enable
 security wpa akm psk set-key ascii XXK123123
```

- WPA2-PSK + AES(同时启用 RSN 和 WPA,兼容老终端)
- PSK 密码:**XXK123123**(明文存在配置中,需及时更换)

## VLAN 与接口

```
vlan range 1,200,236,254

interface GigabitEthernet 0/8
 switchport mode trunk
# 其余 GE0/1-7 未配置

interface VLAN 1
 ip address dhcp
interface VLAN 200
 ip address 192.168.200.3 255.255.255.0
```

> 仅 Gi0/8 是 trunk(上联 W-core);AC 自身管理走 VLAN 200。

## 路由

```
ip route 0.0.0.0 0.0.0.0 192.168.200.1     # →W-core VLAN 200 SVI
```

## 流量 / 应用识别

```
no identify-application enable    # 关闭
wids
black-white-list
```

> WIDS(无线入侵检测)启用,可检测 rogue AP 等。

## DHCP Option 138

W-core 配置 `ap_pool` DHCP 池包含:
```
option 138 ip 192.168.200.3
```

> AP 启动后从 DHCP 获取 option 138,知道 AC 的 IP,自动建立 CAPWAP 隧道。

## CWMP / MQTT

- CWMP(TR-069):ACS URL = `http://devicereg.ruijienetworks.com/service/tr069servlet`
- MQTT:启用(推测接锐捷云管平台)

## 安全 / SSH / 管理

- SSH:启用
- 密码:`ruijie@123`(明文,需加固)
- 启用 Web (HTTP/HTTPS)

## 完整原始配置

```text
version AC_RGOS 11.9(6)W2B1, Release(10162720)
language character-set UTF-8
!
wlan-config 1 Zangyiyuan
 ssid-code utf-8
 tunnel local
!
ap-group default
 interface-mapping 1 236 ap-wlan-id 1
!
ap-config all
!
ac-controller
 capwap ctrl-ip 192.168.200.3
 no ac-control disable
 country CN
 802.11g network rate 1 disabled
 802.11g network rate 2 disabled
 802.11g network rate 5 disabled
 802.11g network rate 6 supported
 802.11g network rate 9 supported
 802.11g network rate 11 mandatory
 802.11g network rate 12 supported
 802.11g network rate 18 supported
 802.11g network rate 24 supported
 802.11g network rate 36 supported
 802.11g network rate 48 supported
 802.11g network rate 54 supported
 802.11b network rate 1 disabled
 802.11b network rate 5 disabled
 802.11b network rate 11 mandatory
 802.11a network rate 6 mandatory
 802.11a network rate 12 mandatory
 802.11a network rate 24 mandatory
!... (略)
!
wlan-cap
 forward central
!
wids
!
black-white-list
!
no identify-application enable
!
cwmp
 acs url http://devicereg.ruijienetworks.com/service/tr069servlet
 cpe inform
!
install 0 WS6008
!
sysmac 8005.8875.1277
!
enable service web-server http
enable service web-server https
webmaster level 0 username admin password 7 0132564a3d11031e527d46
!
mqtt-server enable
no service password-encryption
!
redundancy
!
no rnfp-ping-reply enable
!
control-plane
 anti-arp-spoof scan 20
 attack threshold 500
!... (control-plane 完整)
!
ip ssh key-exchange dh_group14_sha1 ecdh_sha2_nistp256 ecdh_sha2_nistp384 ecdh_sha2_nistp521
clock timezone UTC +8 0
!
link-check disable
!
nfpp
!
frn
!
enable secret 5 $1$sMod$x6z4CpwF27sAv82q 
enable service ssh-server
!
vlan range 1,200,236,254
!
interface GigabitEthernet 0/1-7
# 默认未启用
!
interface GigabitEthernet 0/8
 switchport mode trunk
!
interface VLAN 1
 ip address dhcp
!
interface VLAN 200
 ip address 192.168.200.3 255.255.255.0
!
wlansec 1
 security rsn enable
 security rsn ciphers aes enable
 security rsn akm psk enable
 security rsn akm psk set-key ascii XXK123123
 security wpa enable
 security wpa ciphers aes enable
 security wpa akm psk enable
 security wpa akm psk set-key ascii XXK123123
!
ip route 0.0.0.0 0.0.0.0 192.168.200.1
!
line console 0
line vty 0 4
 login
 password ruijie@123
!
end
```

## 与其他设备关系图

```
┌─────────────────────────────┐
│ W-core (RG-S5760C)          │
│  VLAN 200 SVI 192.168.200.1 │
│  VLAN 254 SVI 192.168.254.1 │
│  AP DHCP pool: 192.168.254.x│
│  Option 138 → 192.168.200.3 │
└────────────┬────────────────┘
             │ trunk (Gi0/8)
             ↓
┌─────────────────────────────┐
│ 无线 AC (RG-WS6008)         │
│  VLAN 200 SVI 192.168.200.3 │
│  CAPWAP ctrl-ip 192.168.200.3│
│  SSID: Zangyiyuan (WPA2-PSK)│
└────────────┬────────────────┘
             │ CAPWAP 隧道
             ↓
        ┌─────────┐
        │   APs   │  STA → VLAN 236 (192.168.236.0/22)
        └─────────┘
```

# 排障：按现象检查，不反复重装

先在 TUN 关闭时测试显式本地代理，再检查系统代理和应用接管。一次只排查一层，避免同时修改服务器、DNS、网卡和客户端设置。

| 现象 | 优先检查 |
|---|---|
| 本地代理测试也失败 | 设备授权、服务器服务、tailnet 访问权限与链式字段 |
| 本地代理通过，浏览器失败 | 系统代理开关、浏览器自己的代理设置 |
| 浏览器通过，其它应用失败 | TUN 权限、路由、DNS 及应用自身设置 |
| 页面没有代理组 | 当前订阅是否启用、是否生成 SERVER 选择组 |

## 密钥到期后如何续期

**这是设备认证到期，不是 1000 分钟额度耗尽。续期是重新授权，不需要购买新的流量包。**

### 先确认是哪台设备

在 Tailscale 控制台【Machines / Devices】分别检查服务器和 Clash 内置节点。电脑上的独立 Tailscale 客户端是第三个身份，它的到期日不代表 Clash 内置节点的到期日。

设备菜单显示 `Disable key expiry`，表示目前启用了到期；显示 `Enable key expiry`，表示目前已关闭到期。普通用户设备通常默认有认证期限，具体日期以后台为准。

### 服务器重新认证

**先确认有云控制台、VNC 或另一条有效管理通道。** 强制认证可能中断 tailnet；不要在唯一一条 tailnet SSH 会话中直接执行。

```bash
sudo tailscale up --force-reauth
# 打开终端给出的登录链接，用原 tailnet 账号重新授权。
tailscale status
```

如果 CLI 要求保留现有非默认参数，按其提示补齐，不使用 `--reset` 清空已有路由或出口设置。完成后确认设备在线、到期日更新，再测试代理。通常无需重装 Xray 或更换 VLESS UUID。

### Clash 内置节点重新认证

1. 保留原 `state-dir`，重启 Clash 内核或完全退出后重开，发起一次代理请求。
2. 若日志输出新的认证链接，打开并确认原账号授权，再检查该内置节点是否在线、到期日是否更新。
3. 若后台提供 `Reauthenticate`，按网页提示处理；该按钮只在合适的认证状态下出现。
4. 若没有链接/按钮，且节点已过期，可使用下面的临时恢复窗口；不要用独立客户端的 `tailscale up` 当成内置节点的续期命令，也不要先删设备或状态目录。

不同内核版本的认证入口可能不同。恢复后仍保留到期策略时，应按该版本支持的重新认证方式操作；对自己控制的可信常驻节点，也可在恢复窗口内选择关闭到期。

### 已过期并且连不上：先恢复一个窗口

在对应的已过期设备菜单选择 **`Temporarily extend key`**。官方说明会临时延长 **30 分钟**，用来恢复连接并完成重新认证，或在窗口内为可信设备选择 `Disable key expiry`。

临时延长不是永久续期；如果没有完成后续操作，窗口结束仍可能断开。不要反复等待它自动恢复。

### 不希望常驻设备定期重新登录

在对应设备菜单选择 **`Disable key expiry`**。这项设置按设备生效，服务器与内置客户端需分别确认；`ephemeral: false` 不会自动设置它。

只对可信、自己控制的设备考虑关闭。关闭会减少周期认证保护，设备丢失、转让或停用时仍应及时撤销访问。本文步骤是说明，不会自动替使用者修改账号设置。

参考：[官方密钥到期与恢复](https://tailscale.com/docs/features/access-control/key-expiry) · [官方 Linux 重新认证](https://tailscale.com/docs/install/linux) · [内置 tsnet 认证入口](https://github.com/MetaCubeX/tailscale/blob/main/tsnet/tsnet.go)。

## 独立 Tailscale 断开后，Clash 外网超时

先区分两件事：

1. **流量未接管**：系统代理和 TUN 都关闭时，只打开 Clash 窗口并不会自动代理浏览器或全机流量。
2. **代理路径本身失效**：即便显式 `curl --proxy http://127.0.0.1:7897` 也失败，就不是接管开关的问题。

比较导入的源配置与【当前运行配置】。正确关系是 VLESS `SERVER-NODE` 的 `dialer-proxy: TAILNET`。某些 GUI 链式代理操作会删除顶层节点的这个字段，导致 VLESS 直接连接服务器 tailnet 地址；原官方 Tailscale 开着时恰好能到，关闭就超时。

本仓库用 inline provider 保存 VLESS 节点，再用 `SERVER` 组引用。修复后重新激活订阅或从托盘完全退出并重开 Clash，再停止官方 Tailscale 做独立测试。不要仅凭 `alive: true`、登录已成功或一个延迟数字认定完整链路可用。

参考：[上游相关问题](https://github.com/clash-verge-rev/clash-verge-rev/issues/6426)、[链式代理实现](https://github.com/clash-verge-rev/clash-verge-rev/blob/dev/src-tauri/src/config/runtime.rs)。具体版本可能不同，优先检查实际生成配置。

## 代理组页面空白，提示没有节点

若 YAML 只有 `proxies`、规则直接指向裸节点而没有 `proxy-groups`，部分界面没有代理组可展示。它不等于代理端口一定失效，但也不是成功证据。

本仓库生成 `SERVER` 选择组并引用 `private-egress`。若仍空白：确认选中了正确订阅，查看内核日志和配置校验结果，再刷新代理页面。不要把“切全局模式”当成修复链式字段的办法。

## 全局 exit node 开启后国内外都断网

先关出口恢复。服务器侧分开测试：

```bash
getent hosts github.com
cat /etc/resolv.conf
sysctl net.ipv4.ip_forward net.ipv6.conf.all.forwarding
tailscale status
sudo systemctl status tailscaled --no-pager
```

部分云内网 DNS 位于 `100.64.0.0/10`。该网段也用于 tailnet，Tailscale 的防伪造处理或网络路由可能影响这类 DNS 响应，出现 IP 连通而解析失败。不能把所有 DNS 故障都归因于这一点，应先观察配置和实际请求。

若已确认且使用 NetworkManager，可将活动连接切换为公共 DNS：

```bash
nmcli -f NAME,UUID,DEVICE connection show --active
# 将占位符替换为当前活动连接和设备，不照抄别人的 UUID。
sudo bash server/repair-networkmanager-dns.sh ACTIVE_CONNECTION_UUID DEVICE
getent hosts github.com
```

脚本备份旧设置，用 `nmcli device reapply`，不执行网卡 down/up。不要只手工覆盖 `/etc/resolv.conf` 后就认定持久生效；网络管理器可能重写它。确认重启 Tailscale 后仍解析正常。

回退：`sudo bash server/rollback-networkmanager-dns.sh`。公共 DNS 是否可达也依赖当地网络；脚本不是所有云环境通用的自动修复。

## 内置 exit-node 冷启动失败

直接给内置 Tailscale 填 `exit-node` 时，某些内核版本会在 peer map 尚未就绪时设置出口，产生找不到节点的初始化错误。等待或重新授权不一定解决。

本方案不使用内置 `exit-node` 字段，而是只通过 tailnet 建立到私有 VLESS 的连接，把 Internet 出站交给服务器 Xray。原全局出口保留作可选回退，不与最终链路混为一谈。

## `state-dir` 不被允许或授权反复丢失

- 查看内核启动参数的 `-d`，状态目录必须在它允许的目录内。
- 更换用户、数据目录或便携模式后，不能照抄旧绝对路径。
- 退出占用状态文件的测试内核再迁移，不复制到公开仓库。
- 不同时启动两个内核使用同一个状态目录；不要随意删除 `tailscaled.state`。

## TUN 一开全机断网

先关闭 TUN 恢复，然后用显式本地代理测试。只有代理测试正常，再检查：服务模式/管理员权限、虚拟网卡、DNS 劫持、GUI 全局 DNS 覆写、TUN 栈及其它 VPN 的路由。

系统代理主要面向遵循系统代理的软件，TUN 才用于接管更多程序。最终是否覆盖游戏、UDP 或特定研究工具，必须用对应软件实际验证，不能只测浏览器。

## 为什么只换域名或用 Cloudflare Tunnel 不是直接替代品

如果被阻断的是服务器公网路径，只给同一 IP 换域名通常不改变网络可达性。Cloudflare Tunnel 的网站发布和整机 Internet 出口也不是同一功能，不能把任意 HTTP 隧道地址直接当成 VLESS/SOCKS 节点。

本教程使用 tailnet 私有传输。选择其它隧道时，需要重新确认传输协议、客户端配合及服务条款。

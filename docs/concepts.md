# 原理与术语：先理解，再配置

## 分流与全局代理

全局代理倾向于让所有流量走同一个出口。分流先判断目标，再决定直连还是代理：国内站点走本地网络，其他目标走服务器。

规则通常依据域名集合（GeoSite）或 IP 数据库（GeoIP）判断。本教程把局域网和国内目标交给 `DIRECT`，其余交给 `SERVER`。“其余”是逐条匹配后的兜底选择，不是绝对准确的地理判断。

## 四个组件各管什么？

| 组件 | 可以理解为 | 职责 |
|---|---|---|
| Clash Verge Rev | 操作面板 | 导入配置、显示连接、切换系统代理和 TUN |
| Mihomo | 分拣员与网络引擎 | 执行规则、DNS 和代理协议；内置 Tailscale |
| Tailscale | 设备间通道 | 让电脑与服务器通过 tailnet 私网地址通信 |
| Xray | 服务器上的出站代理 | 接收 VLESS 请求并访问目标网站 |

Clash 是界面、Mihomo 是内核；Tailscale 解决设备间连接，Xray 解决代理请求出站。它们负责不同层次，而不是互相替代。

## tailnet 地址不是公网 IP

公网 IP 用于普通互联网连接；tailnet 地址在 Tailscale 网络中标识设备，常见 IPv4 位于 `100.64.0.0/10`。

切换 Wi-Fi、热点或运营商时，本机公网 IP 可能改变。本方案不将它写进节点配置，而由 Tailscale 重建连接，期间可能短暂断流。

教程中的 `100.64.0.10` 仅说明格式；搭建时应读取自己服务器的实际 tailnet 地址。

## 数据是否经过 Tailscale 官方服务器？

不一定。控制面负责设备身份、连接信息和访问规则；真正传输数据时，设备可以直连，也可以通过 DERP 或已配置的 Peer Relay 中继。直连通常性能更好，中继用于其它路径不合适的情况，数据仍为设备间加密。

完整过程、如何检查实际路径以及费用计算，见 [Tailscale 工作原理、免费流量与带宽](tailscale-network-and-cost.md)。

## 为什么不只用 Tailscale exit node？

Exit node 适合简单的全局出口需求；若要按域名/IP 分流，还需要规则引擎决定去向。

本教程让内置 Tailscale 只连接服务器私网 VLESS 入口，由 Xray 出站。因此 Windows 日常只需 Clash，不用给内置节点填 `exit-node`，Linux 也不需要为这条应用层链路开启 IP 转发。已有 exit node 可保留作准备和应急通道。

## “持久设备”是另一种网络模式吗？

不是。持久/临时描述离线后是否保留设备身份；直连/中继描述数据传输路径；密钥到期则是认证期限，三者相互独立。`ephemeral: false` 适合日常设备，但不代表永久免认证。见 [常见问题](faq.md)。

## 为什么叠加 VLESS 和 Tailscale？

VLESS 表达“请服务器替我访问目标”，Tailscale 提供到服务器的私网通道。`dialer-proxy: TAILNET` 指定先通过内置隧道连接，再发送 VLESS 请求。

若该字段丢失，VLESS 会尝试直接连接 tailnet 地址，此时可能又依赖独立 Tailscale 客户端。

这段传输已有 Tailscale 加密，因此这里不为 VLESS 再加 TLS。前提是只绑定服务器 tailnet 地址并控制访问权限，不要直接照搬成公网监听。

## 系统代理与 TUN

| 模式 | 适用场景 | 注意事项 |
|---|---|---|
| 系统代理 | 浏览器和遵循系统设置的软件 | 有些软件会绕过它 |
| TUN / 虚拟网卡 | 覆盖更多应用和 UDP | 需要合适权限、路由、DNS 设置 |

推荐先让浏览器通过系统代理工作，再开 TUN 测实际应用。TUN 接管后仍然按规则分流，不等于全部走远端。

## 配置里的名字

| 名称 | 含义 |
|---|---|
| `DIRECT` | 本地直连 |
| `TAILNET` | 内置 Tailscale 通道 |
| `SERVER-NODE` | 服务器 VLESS 节点 |
| `SERVER` | 界面可见的选择组，引用 `SERVER-NODE` |
| `private-egress` | 同一份 YAML 中保存节点的 inline provider |

Inline provider 不需要下载第二份订阅，也能避开部分 GUI 链式操作会重写顶层 `dialer-proxy` 的兼容问题。

下一步：[完整安装教程](deployment.md)。

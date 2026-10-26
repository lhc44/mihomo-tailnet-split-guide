# Windows 单客户端分流：Mihomo + 内置 Tailscale

一份脱敏、可复用的部署记录：服务器公网连接受阻时，通过 Tailscale 私有网络承载服务器代理；Windows 日常只运行 Clash Verge Rev，国内直连，其他流量按规则走自己的服务器。

**这里没有可直接使用的订阅、服务器凭据或设备身份。** 所有私人参数均由使用者在本地生成。示例 `100.64.0.10` 是虚构的 tailnet 地址，不是可连接的节点。

## 最终结构

```text
Windows / Clash Verge Rev（Mihomo 内核）
  ├─ 国内域名 / 国内 IP / 局域网 → DIRECT → 本地网络
  └─ 其他目标 → SERVER 代理组
                  → SERVER-NODE（VLESS / XUDP）
                  → TAILNET（Mihomo 内置 Tailscale）
                  → 服务器 tailnet 地址:10808
                  → Xray freedom → Internet
```

- 单客户端是指 Windows 端日常只需要 Clash；服务器仍运行 Tailscale 和 Xray 两个服务。
- 最终方案不依赖本机公网 IP 固定，不需要公网开放 `10808`，也不需要为链式代理启用 Linux IP 转发。
- 原 Tailscale 全局出口可作为安装、授权和紧急回退通道，不是最终链路必须同时开启的客户端。
- 国内/国外是域名及 IP 数据库分类结果，并不是对所有站点的永久保证。跨国服务、CDN、自建域名可能需要追加规则。
- 可达性仍取决于当前网络能否接入 Tailscale 控制面及直连/中继路径；不承诺任意运营商、任意时间可用或固定速度。

## 文件导览

| 文件 | 用途 |
|---|---|
| `server/install-tailscale-static.sh` | 可选：全新 amd64 Linux 的官方静态包安装 |
| `server/enable-exit-node.sh` | 可选：先建立全局出口作为回退 |
| `server/install-private-proxy.sh` | 安装只绑定 tailnet 地址的 VLESS 入口 |
| `server/render_config.py` | 参数校验及服务器配置渲染 |
| `server/repair-networkmanager-dns.sh` | 可选：修复云内网 DNS 与 CGNAT 网段冲突 |
| `server/rollback-*.sh` | 各变更对应的回退，不删除已有设备身份 |
| `client/generate_profile.py` | 本地生成带可见代理组的私人 YAML |
| `client/Backup-Clash.ps1` / `Restore-Clash.ps1` | 备份、校验和恢复 Clash 设置 |
| `client/Test-Split.ps1` / `probe_socks_udp.py` | HTTP 及 SOCKS UDP 连通性测试 |
| `tools/check_publication.py` | 发布前文件白名单及敏感标记扫描 |
| [部署说明](docs/deployment.md) | 从服务器到客户端的完整操作 |
| [排障手册](docs/troubleshooting.md) | 真实踩坑的脱敏总结 |
| [发布及脱敏](docs/publication.md) | 哪些内容永远不应提交 |

## 快速开始

完整前提和备份要求见 [部署说明](docs/deployment.md)。不要将下面几步理解成无需授权、无需服务器的一键服务。

1. 安装并授权服务器 Tailscale，检查服务器能解析域名并访问互联网。
2. 如需要，先配置并批准 Tailscale exit node，建立回退通道。
3. 在服务器运行：

   ```bash
   sudo bash server/install-private-proxy.sh
   ```

4. 将服务器生成的 `server-info.json` **私下**保存到本机 `local/`，不要发到 Issue。
5. 在 Windows PowerShell 7 中生成本机配置：

   ```powershell
   python -m pip install -r requirements.txt
   $homeDir = Join-Path $env:APPDATA 'io.github.clash-verge-rev.clash-verge-rev'
   python client/generate_profile.py `
     --server-info local/server-info.json `
     --state-dir "$homeDir/tailscale-split-state" `
     --out local/split.yaml
   ```

6. Clash【订阅】导入 `local/split.yaml`，点击启用。初次触发代理请求后，在日志中找到内置 Tailscale 的设备授权链接，用自己的账号确认设备。
7. 确认【代理】可见 `SERVER → SERVER-NODE`，模式为【规则】；先开【系统代理】，再断开原 Tailscale 连接，验证国内外网页。
8. 浏览器验证正常后，再开启【TUN / 虚拟网卡】接管其他软件；按提示安装服务或确认管理员操作。

## 为什么采用 inline provider

某些 Clash Verge Rev 链式代理操作会清掉顶层 `proxies` 中的 `dialer-proxy`。源 YAML 看起来正确，但运行时 `SERVER` 失去 `TAILNET` 前置隧道，就会出现“原 Tailscale 一断开，国外全部超时”。

本方案把 VLESS 节点放在 `proxy-providers.private-egress.payload` 中，保留 `dialer-proxy: TAILNET`，再通过 `SERVER` 选择组引用。无需下载第二份订阅，也避免“只有两个裸节点、代理组页面空白”的展示问题。

这是针对所观察版本行为的兼容写法，不表示所有未来版本都有同样问题。详见 [上游实现](https://github.com/clash-verge-rev/clash-verge-rev/blob/dev/src-tauri/src/config/runtime.rs) 和 [Mihomo provider 文档](https://wiki.metacubex.one/config/proxy-providers/)。

## 验证与边界

该架构曾进行实机独立验证：停止原 Tailscale 连接后，Google、GitHub、国内网站可达；国内流量直连、国外流量使用服务器出口；SOCKS UDP DNS 查询和重启后连接通过。原始记录包含私人地址和设备信息，因此不放入仓库。

**这些架构验证不等于此处泛化安装脚本已覆盖所有发行版、所有 TUN 模式或移动端。** 新环境需要按说明重新测试。仓库自动检查覆盖模板约束、错误参数、链式字段保留、Bash 语法和发布检查；不会在 CI 登录私人 tailnet 或自动执行服务器部署。

本地检查：

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
for file in server/*.sh; do bash -n "$file"; done
python tools/check_publication.py
```

## 版本与参考

- 服务器安装示例固定 Xray `v26.10.21`，下载文件 SHA256 在脚本内固定；升级时应同时审阅版本、资产和校验值。
- 静态安装示例固定 Tailscale `1.104.2` / Linux amd64；已有安装直接复用，不强制重装。
- Windows 需要支持 `type: tailscale`、inline provider、VLESS XUDP 的 Mihomo 构建；在对应内核上执行 `-t` 验证，而不是只看客户端版本。
- [Tailscale exit nodes](https://tailscale.com/docs/features/exit-nodes)
- [Mihomo Tailscale](https://wiki.metacubex.one/config/proxies/tailscale/)
- [Mihomo DNS](https://wiki.metacubex.one/config/dns/)
- [Clash Verge 本地导入](https://www.clashverge.dev/guide/profile.html)
- [Xray VLESS](https://xtls.github.io/config/inbounds/vless.html)

本项目与以上软件无隶属关系。网络策略、服务套餐和中继可达性会变化；免费软件不代表服务器及流量永远免费。

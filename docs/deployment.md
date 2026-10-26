# 完整安装教程

目标：Windows 只运行 Clash Verge Rev，国内直连，其他目标经自己的服务器出站。

不熟悉术语可以先读 [原理与术语](concepts.md)。这份教程把操作分为服务器和 Windows 两侧；所有命令都在项目根目录运行，切勿在错误的机器上执行。

## 0. 准备环境

| 位置 | 必要条件 |
|---|---|
| 服务器 | Linux amd64、systemd、可用的 SSH 管理连接、可访问互联网 |
| 服务器工具 | `curl`、`unzip`、`python3`、`sha256sum`、`ss`；安装脚本使用 root 权限 |
| Windows | Clash Verge Rev、Python 3.10+、PowerShell 7、`curl.exe` |
| 网络 | 本地与服务器都能接入 Tailscale，且 tailnet 访问规则允许客户端连接代理端口 |

服务器和电脑各下载一份仓库文件。Windows 打开 PowerShell 7（`pwsh`），进入项目目录。服务器另开 SSH 会话，进入它自己的项目目录。

首次安装应保留 SSH 管理连接和一条可恢复的普通网络通道。遇到错误先查该步结果，不要同时改网卡、DNS、防火墙和代理配置。

## 1. 服务器安装并登录 Tailscale

**在服务器执行。** 已安装可直接复用；尚未安装按 [官方 Linux 说明](https://tailscale.com/download/linux) 操作。

```bash
tailscale version
sudo systemctl enable --now tailscaled
sudo tailscale up
```

打开终端给出的登录链接，用自己的 Tailscale 账号授权此服务器，然后检查：

```bash
tailscale status
tailscale ip -4
getent hosts github.com
```

**成功判据：** 有一个 `100.x.x.x` 形式的 tailnet IPv4，设备在线，域名可解析。本文用 `100.64.0.10` 示意，实际操作要换成自己的值。

如果系统软件仓库安装困难，可看 [静态包安装](#附录-a可选的静态包安装)；如果加入 Tailscale 后解析异常，先查 [DNS 排障](troubleshooting.md)，不要继续叠加服务。

## 2. 服务器部署私网 VLESS 入口

**在服务器执行：**

```bash
sudo bash server/install-private-proxy.sh
sudo systemctl status tailnet-private-proxy --no-pager
sudo ss -H -lnt '( sport = :10808 )'
```

脚本会校验固定版本 Xray 下载包，随机生成节点 UUID，创建专用服务账号和 systemd 服务。已有安装目录或备份时会停止，避免覆盖正在使用的设置。

**成功判据：** 服务为 `active`，监听的是 `服务器 tailnet 地址:10808`，不是 `0.0.0.0:10808` 或公网地址。

这条链路通过 Tailscale 加密私网传输，因此 VLESS 本身没有额外 TLS；不要把监听地址改成公网通配地址。脚本也不会为代理入口开放公网安全组或清空现有防火墙。

在 Tailscale ACL/grants 中允许指定客户端访问服务器 **TCP `10808`**。服务器出站默认阻止常见私网目标，适用于 Internet 出口；访问内部业务应另行设计规则。

## 3. 把节点参数保存到 Windows

服务器生成的参数文件是：

```text
/opt/tailnet-private-proxy/server-info.json
```

里面是 `server`、`port`、`uuid`，文件权限为 `0600`。将它通过自己的管理通道保存到 Windows 项目目录下的 `local/server-info.json`。

例如，当 Windows 已经通过独立 Tailscale 客户端加入同一网络，且服务器允许当前管理账号使用 SSH 时，可以用 SCP：

```powershell
New-Item -ItemType Directory -Force local | Out-Null
$server = '100.64.0.10'  # 替换为自己的服务器 tailnet 地址
scp "root@${server}:/opt/tailnet-private-proxy/server-info.json" local/server-info.json
```

上例以允许 root SSH 的环境示意。若使用普通管理账号，通过现有 sudo 和文件传输方式获取即可，不必额外开放 root 登录。也可使用既有的服务器控制台或 SSH 文件传输工具。

该文件是个人节点配置，不是可分享的订阅。`local/` 用于保存运行时参数。

## 4. 备份 Clash 并生成 YAML

**在 Windows PowerShell 7 执行：**

```powershell
pwsh -File client/Backup-Clash.ps1 -Destination local/clash-backup
python -m pip install -r requirements.txt
$homeDir = Join-Path $env:APPDATA 'io.github.clash-verge-rev.clash-verge-rev'
python client/generate_profile.py `
  --server-info local/server-info.json `
  --state-dir "$homeDir/tailscale-split-state" `
  --out local/split.yaml
```

**成功判据：** 生成 `local/split.yaml`，其中有 `TAILNET`、`private-egress` 和 `SERVER` 代理组。生成器在输出文件已存在时停止；修改配置前先保留上一份可用版本。

`$homeDir` 应是实际 Mihomo 的 `-d` 数据目录。便携版或自定义数据目录需要调整，`state-dir` 也必须位于该目录允许的范围内。

可在导入前校验（将 `$core` 替换为实际安装位置）：

```powershell
$core = 'C:/Apps/ClashVerge/verge-mihomo.exe'
& $core -t -d $homeDir -f (Resolve-Path local/split.yaml).Path
```

若提示 GeoSite/MMDB 缺失，先通过 Clash 的正规更新功能安装数据库。语法检查只验证配置，不代表网络已通。

## 5. 导入、授权、选择规则模式

1. 打开 Clash →【订阅】，拖入 `local/split.yaml`，点击它使其生效。
2. 打开【代理】，选择【规则】，应看到 **`SERVER → SERVER-NODE`**。
3. 在 PowerShell 执行一次测试，以触发内置 Tailscale 初始化：

   ```powershell
   pwsh -File client/Test-Split.ps1
   ```

4. 初次尚未授权时，测试可能失败；打开 Clash 日志，找到内置 Tailscale 的设备绑定链接，用同一 Tailscale 账号授权电脑节点。
5. 授权完成后重新执行测试。服务器和电脑内置节点是两台独立设备，都需要加入自己的 tailnet。

如果初次访问控制面需要临时通道，可借用已经可用的独立 Tailscale 出口。安装过程中借它联网很正常，但下一步要断开它再测试，否则还不能确认单客户端独立工作。

本方案不要求为内置节点批准 exit node，也不需要填写 `exit-node` 字段。

## 6. 独立验证，然后开启流量接管

先保持 TUN 关闭。若安装了独立 Tailscale 客户端，**断开它的连接**；只关闭窗口不等于断开。管理员终端也可执行 `tailscale down`，无需强停系统服务。

```powershell
pwsh -File client/Test-Split.ps1 -WithUdp
```

期望三个网站 HTTP `200`，UDP 输出 `SOCKS_UDP_DNS_OK`。脚本显式使用本地 `7897` 代理；若自己改了端口，加 `-Port` 指定。

接下来按需要开启：

| 设置 | 操作 | 如何确认 |
|---|---|---|
| 系统代理 | 在 Clash 开启【系统代理】 | 浏览器可打开国内外网页 |
| 规则分流 | 保持【规则】模式 | 【连接】中国内测试目标为 `DIRECT`，国外为 `SERVER` |
| TUN | 浏览器测试正常后开启【TUN / 虚拟网卡】 | 按提示安装服务/批准 UAC，再测试目标应用 |

GUI 可能覆盖 YAML 中的 DNS 或 TUN 设置，应以实际运行配置和日志为准。节点在线或页面显示延迟，不等于完整链路已工作。

最后再做三次检查：完全退出后重开 Clash、切换 Wi-Fi/热点、使用真正需要的应用。公网 IP 变化不需要改节点，但隧道重连可能短暂中断。

## 7. 回退与恢复

先关 Clash【系统代理】和【TUN】，恢复普通网络。若预先准备了独立 Tailscale 出口，可重新连接它作为临时通道。

恢复 Clash 设置前，从托盘完全退出 Clash：

```powershell
pwsh -File client/Restore-Clash.ps1 -Backup local/clash-backup -CheckOnly
pwsh -File client/Restore-Clash.ps1 -Backup local/clash-backup
```

服务器停用新增代理：

```bash
sudo bash server/rollback-private-proxy.sh
```

回退保留不活动文件和设备身份，不递归删除个人配置。Clash 恢复脚本恢复备份中的主设置，不清理后来添加但未引用的 profile 文件。

使用可选组件时，按依赖关系回退：私网代理 → 全局出口变更 → 静态 Tailscale 安装。DNS 回退单独操作，并保留有效管理连接。

## 附录 A：可选的静态包安装

仅适用于全新的 Linux amd64 安装。已有 Tailscale 时优先复用，不运行此脚本覆盖。

从 [官方稳定包目录](https://pkgs.tailscale.com/stable/#static) 获取脚本固定的 Tailscale `1.104.2` amd64 归档并核对校验值：

```bash
# 替换为实际文件路径和核对过的 SHA256。
sudo bash server/install-tailscale-static.sh /path/to/archive.tgz EXPECTED_SHA256
sudo tailscale up
```

回退：`sudo bash server/rollback-tailscale-static.sh`。该回退仅针对配套静态安装，不用于卸载包管理器安装的 Tailscale。

## 附录 B：可选的全局出口通道

如果想先建立一个简单全局出口用于准备或应急，在服务器执行：

```bash
sudo bash server/enable-exit-node.sh
```

然后在自己的 Tailscale 控制台批准服务器用作出口，Windows 独立 Tailscale 客户端选择它。全局出口和规则分流是两条不同路径，本教程最终方案不依赖这一步。

启用后断网应先取消出口，参考 [排障手册](troubleshooting.md) 检查 DNS、转发和路由。回退服务器变更：`sudo bash server/rollback-exit-node.sh`。

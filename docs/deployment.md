# 从零部署与回退

## 0. 前提与重要边界

- 服务器：Linux amd64、systemd、已有管理通道，能访问互联网；准备 `curl`、`unzip`、`python3`。不要把 SSH 密码写进脚本。
- 客户端：Windows、Python 3.10+、PowerShell 7、Clash Verge Rev；确认所选 Mihomo 内核支持 Tailscale。
- 使用自己管理的 tailnet。服务器和内置 Mihomo 节点需要分别授权；不是给服务器授权一次就自动给所有客户端授权。
- 先保留一条可恢复的服务器管理会话。不要在未核对设备和连接配置时重启网卡、清空防火墙或覆盖 DNS。
- `local/` 用来放私密生成物，默认被 Git 忽略。它仍是明文私人配置，应放在只有本人可读的位置；`.gitignore` 不是加密或访问控制。

## 1. 服务器加入 Tailscale

### 优先复用已有安装

```bash
tailscale version
sudo systemctl enable --now tailscaled
sudo tailscale up
tailscale status
tailscale ip -4
getent hosts github.com
```

`tailscale up` 打印的授权 URL 只给设备所有者使用，不放入仓库、截图或公开日志。

没有安装时优先参考 [官方 Linux 安装](https://tailscale.com/download/linux)。过旧发行版的软件仓库可能失效；可使用官方静态包，但生产环境更推荐仍在维护的系统。

### 可选：官方静态包

从 [官方稳定包目录](https://pkgs.tailscale.com/stable/#static) 获取脚本固定版本的 Linux amd64 归档，核对官方校验值。脚本要求显式提供校验值，不盲信来历不明的二进制。

```bash
# 自行替换归档路径和已经核对的 SHA256；下面不是可直接运行的真实参数。
sudo bash server/install-tailscale-static.sh /path/to/archive.tgz EXPECTED_SHA256
sudo tailscale up
```

该脚本仅支持全新安装，遇到现有命令、unit 或安装路径就停止。授权状态保存在服务器本地，不输出到仓库。

回退：`sudo bash server/rollback-tailscale-static.sh`。应先关闭依赖它的新增私有代理；脚本保留设备身份文件和二进制，便于人工恢复。

## 2. 可选：建立原 Tailscale 全局出口作为回退

```bash
sudo bash server/enable-exit-node.sh
```

然后在 Tailscale 控制台批准该服务器用作出口。Windows 官方客户端选择该出口，确认国内外网页可达。这里是全局转发，不是国内外规则分流。

若开启后国内外均断网，先关闭出口恢复连接，再按 [DNS 排障](troubleshooting.md) 检查服务器 DNS、IP 转发和 Tailscale 防火墙链。不要盲目重复安装。

回退：`sudo bash server/rollback-exit-node.sh`，恢复先前通告的路由及运行时转发值。备份在 `/var/backups/tailnet-exit-node/`，仅留在服务器。

最终 VLESS-over-tailnet 是应用层代理，不需要启用或批准 exit node；本节只是迁移过程中可选的回退通道。

## 3. 部署只在 tailnet 内监听的代理

在仓库根目录运行：

```bash
sudo bash server/install-private-proxy.sh
sudo systemctl status tailnet-private-proxy --no-pager
sudo ss -H -lnt '( sport = :10808 )'
```

期望监听 `服务器的 tailnet 地址:10808`，而不是 `0.0.0.0:10808` 或公网地址。UUID 每次全新部署随机生成，不使用仓库内固定凭据。

脚本只绑定私网接口，不修改云安全组或现有防火墙，不改 SSH 配置。需要在 tailnet ACL/grants 中允许指定客户端访问此服务器的 TCP `10808`；不要为了省事放开整个 tailnet。

VLESS 本身设置为无额外 TLS，是因为这段链路封装在 Tailscale 加密网络内。**不要照抄成公网裸 VLESS。** 出站阻止访问服务器本地及常见私网段，适用于纯 Internet 出口；如需要访问私有服务，应另行设计访问规则。

私人参数保存在 `/opt/tailnet-private-proxy/server-info.json`，权限 `0600`。通过已有可信管理通道将其复制到 Windows `local/server-info.json`。示例：

```powershell
New-Item -ItemType Directory -Force local | Out-Null
$server = '100.64.0.10'  # 虚构示例，替换为自己的服务器 tailnet 地址
scp "root@${server}:/opt/tailnet-private-proxy/server-info.json" local/server-info.json
```

若不允许 root SSH，使用自己的管理账号及受控 sudo 读取方式；不要为本教程额外放开 root 登录。

回退：`sudo bash server/rollback-private-proxy.sh`。停用并移除新增 unit，保留原 Tailscale、服务器 DNS、退出节点和不活动文件。重新安装前先人工检查留存路径，不覆盖旧备份。

## 4. Windows 本地生成配置

先备份当前 Clash：

```powershell
pwsh -File client/Backup-Clash.ps1 -Destination local/clash-backup
python -m pip install -r requirements.txt
$homeDir = Join-Path $env:APPDATA 'io.github.clash-verge-rev.clash-verge-rev'
python client/generate_profile.py `
  --server-info local/server-info.json `
  --state-dir "$homeDir/tailscale-split-state" `
  --out local/split.yaml
```

配置里的 `state-dir` 必须位于实际 Mihomo `-d` 指定的主目录下，否则内核安全路径检查会拒绝。便携版或更换用户时，先查实际数据目录，不能照抄别人的绝对路径。生成器要求输出文件尚不存在，避免覆盖正在工作的配置。

验证内核语法（将 `$core` 替换成实际安装位置）：

```powershell
$core = 'C:/Apps/ClashVerge/verge-mihomo.exe'
& $core -t -d $homeDir -f (Resolve-Path local/split.yaml).Path
```

若 GeoSite/MMDB 缺失，先通过客户端的正规更新功能安装数据库。正在运行的内核占用 `cache.db` 时，独立 `-t` 可能提示缓存锁；区分缓存警告与真正配置错误，不要删掉身份状态去“修复”。

## 5. 导入与内置设备授权

1. Clash →【订阅】，拖入 `local/split.yaml`，点击启用。
2. 模式选【规则】，在【代理】确认 `SERVER` 选择组及其中的 `SERVER-NODE`。
3. 第一次通过本地代理请求网页，会触发内置 Tailscale 初始化；在日志找到设备绑定链接，用自己的账号确认新设备。
4. 内置设备是一个独立身份，只需访问服务器 TCP `10808`；最终方案不必把它设为 exit node。
5. 初次授权可暂借原官方 Tailscale 的可用网络；接下来必须做独立测试，不能把“借原出口成功”误判为单客户端完成。

如果迁移已授权的 `state-dir`，必须先停止正在使用它的内核，复制后核对文件 SHA256；只在自己的机器之间受控操作。不要同时开两个内核读写同一个身份目录，不要把状态放在仓库。

## 6. 先验证代理，再启用系统接管

先保持 TUN 关闭。打开 Clash【系统代理】，再**断开原 Tailscale 连接**，不只是关掉它的窗口。也可以在管理员终端使用 `tailscale down`；无需强停系统服务。

```powershell
# 不自动改变原 Tailscale 状态，使用者应先按上文断开。
pwsh -File client/Test-Split.ps1 -WithUdp
```

三个网页返回 `200`、UDP 输出 `SOCKS_UDP_DNS_OK`，只说明本地代理路径通过。还需在 Clash【连接】确认百度命中 `DIRECT`、Google/GitHub 命中 `SERVER`。若自行用 IP 查询站验证出口，不要公开原始结果。

然后开启 Clash【TUN / 虚拟网卡】，按提示安装服务或批准 UAC，测试不遵循系统代理的实际软件。TUN 的权限、网卡、GUI 全局设置及 DNS 覆写可能与 YAML 不同，以运行配置及日志为准。

完成后日常只开 Clash。网络从 Wi-Fi 切到热点后，隧道需要重建，可能短暂断流；本机公网 IP 改变不需要修改节点地址。请测试一次切网、一次冷启动、一次原 Tailscale 停止后的访问。

## 7. 回退与恢复

网络回退优先：关 Clash 的系统代理及 TUN → 重新连接官方 Tailscale → 选择原出口。保留回退软件直到确认新方案稳定。

恢复 Clash 设置前，从托盘完全退出 Clash：

```powershell
pwsh -File client/Restore-Clash.ps1 -Backup local/clash-backup -CheckOnly
pwsh -File client/Restore-Clash.ps1 -Backup local/clash-backup
```

这里恢复导入前五类主设置，不删除后加的未引用 profile 文件或设备身份，避免误删别的配置。备份若不完整，应先人工检查，不进行猜测性恢复。

服务器各脚本有独立回退，按依赖关系处理：私有代理 → 可选 exit-node 变更 → 可选静态 Tailscale 安装。DNS 回退单独处理，确保管理连接不依赖即将停用的服务。

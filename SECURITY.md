# 私密信息处理

不要通过公开 Issue 或 Pull Request 发送 UUID、代理 YAML、SSH 密码、GitHub/Tailscale 密钥、设备授权链接、节点 ID、状态目录、原始日志或个人 IP 查询结果。

排障前只保留错误类型、软件版本和脱敏字段结构。尤其检查 `server`、`uuid`、`state-dir`、日志里的授权 URL 及 Windows 用户目录。

VLESS 无额外 TLS 的配置仅适用于这里的 Tailscale 加密私网承载。保持监听地址仅为服务器 tailnet 地址，并限制 tailnet ACL/grants；不要改为公网通配监听。

如果凭据曾被提交，先撤销或轮换对应凭据、设备身份及访问权限，再处理 Git 历史。只删除最新文件不够。

脚本是可审阅的部署辅助，不保证适配所有发行版。运行前备份并保留管理连接，逐步验证，不在失去回退通道时强制切换。

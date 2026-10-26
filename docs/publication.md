# 脱敏与发布检查

## 仓库只放可复用材料

采用重新编写模板而不是替换旧日志里的 IP：日志中往往还藏有节点 ID、授权链接、家庭公网 IP、SSH 指纹、用户路径和账号名称。旧部署目录、聊天记录、截屏、私钥和状态文件都不复制进来。

本仓库不包含：

- 实际服务器公网/私网地址、域名、机器名或控制台设备链接；
- 登录账号、SSH 密码、访问令牌、代理 UUID、设备认证密钥；
- 真实用户名路径、运营商出口及地理位置记录；
- `tailscaled.state`、运行日志、Clash 已生成私人配置、服务器备份；
- 原始测试记录或预装的认证状态；
- 以邮箱或聊天昵称标识个人的 Git 作者信息。

示例地址采用虚构 tailnet 地址，公共解析器地址保留其公开用途。真实参数在运行时生成，写入 `local/` 或服务器权限受限目录。

## 发布前

```bash
python -m unittest discover -s tests -v
python tools/check_publication.py
git add README.md SECURITY.md LICENSE requirements.txt .gitignore .gitattributes client server docs tools tests .github
python tools/check_publication.py --staged
git diff --cached --stat
git diff --cached
```

扫描器执行允许文件类型和目录检查，并查找常见令牌、设备密钥、UUID 及个人 Windows 路径。它只报告文件、行号和类别，不回显匹配内容。可通过进程环境变量 `PRIVATE_DENY_JSON` 提供一组本机私密拒绝字符串；该值不要写进命令历史、仓库或 CI。

扫描器不能识别所有秘密，仍须人工审阅 diff，确认没有归档、二进制、子模块、外链状态文件或意外文件。`.gitignore` 不会删除历史中已经提交过的秘密。

## Git 历史也需要脱敏

- 在全新干净目录初始化仓库，不复制原工作目录的 `.git`。
- 用不含私人邮箱的通用作者身份提交，或者使用本人选择的 GitHub noreply 身份。
- 推送前审阅提交文件列表和作者元数据；默认创建私有仓库，确认后再决定是否公开。
- 仓库归属账号和 GitHub 操作记录仍由 GitHub 展示，私有仓库也不是匿名服务。
- 凭据若已泄漏，先撤销/轮换，再清理历史。后续单独删文件并不能撤销泄漏。

## 验证边界

公开仓库记录的是泛化模板测试结果，不保存真实连通性输出。模板及回退脚本经过静态/单元检查，不会因为存在 CI 绿勾就宣称已经替读者在服务器实装、验证了 TUN 或完成其账号授权。

# 薯条-OKR撰写SKILL

一个 Claude Code skill：按公司飞书 OKR 的真实写法，帮员工写季度个人 OKR。

1. 用 lark-cli（飞书命令行工具） 读上级链路和同组同事的 OKR，沿对齐关系爬出整张对齐网
2. 找出所有 @到本人的 KR，结合本人周报、项目文档盘点输入
3. 按公司格式起草 O / KR / 权重 / 对齐，并逐条自检
4. 本人确认后，才决定是否写回飞书

## 安装

```bash
git clone https://github.com/blairmeow93/okr-skill.git
mkdir -p ~/.claude/skills
ln -s "$(pwd)/okr-skill/skills/薯条-OKR撰写SKILL" ~/.claude/skills/
```

需要先装好 lark-cli 并用 `lark-cli auth login` 登录（需要 OKR 读写和通讯录读取权限）。

重开 Claude Code 后输入 `/薯条-OKR撰写SKILL` 使用。

## 内容

- `SKILL.md`：固定六步流程
- `references/公司OKR写法规范.md`：格式、权重、对齐逻辑、KR 好坏对照（示例已脱敏）
- `references/lark-cli读写OKR.md`：读、爬、写 OKR 的命令和踩过的坑
- `references/示例-一线产品经理.md`：完整示例（虚构）
- `scripts/okr_crawl.py`：沿对齐关系爬 OKR，输出对齐树和全文

## License

MIT

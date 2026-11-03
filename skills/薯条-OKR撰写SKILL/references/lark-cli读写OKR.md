# 用 lark-cli 读写飞书 OKR

全部用 `--as user`（员工本人身份）。bot 身份没有申请 OKR 权限，会报 `app_scope_not_applied`。

## 找人

```bash
lark-cli contact +search-user --user-ids me --as user          # 自己
lark-cli contact +search-user --query "张三" --as user          # 按姓名
lark-cli contact +search-user --user-ids "ou_a,ou_b" --as user  # 按 open_id 批量
```

坑：`--user-ids` 一次**最多返回 20 人**，传 50 个只回 20 个，不报错。批量要按 20 切。

## 找周期 / OKR id

```bash
lark-cli okr +cycle-list --user-id <open_id> --as user
```

`current_active_cycles` 里可能同时有季度和年度周期，写季度 OKR 时取季度那个。

**v2 的周期 id = v1 的 okr id = 飞书链接里的 `okrId`**，三者是同一个数。

链接 `…/okr/user/<一串数字>/?okrId=<id>` 里 `/user/` 后面那串是飞书内部 ID，不是 open_id 也不是 user_id，API 用不了，直接忽略。

## 读一份 OKR（含上下对齐）

```bash
lark-cli api GET /open-apis/okr/v1/okrs/batch_get \
  --params '{"okr_ids":["<okr_id>"],"lang":"zh_cn"}' --as user
```

- 一次最多 10 个 okr_id。
- v1 返回里有对齐信息，v2 的 `+cycle-detail` 没有，所以爬网用 v1。
- `aligning_objective_list` = 本目标对齐到的**上级**；`aligned_objective_list` = 对齐到本目标的**下级**。每项带 `okr_id` 和 `owner.open_id`。
- 部分 O / KR 没有 `content` 字段，表示没有查看权限，脚本里显示为 `<无权限>`。

不要用 `okr objectives get` 去查链接里的 okrId，那是周期 id 不是目标 id，会报 `okr data not found`。

## 爬整张对齐网

```bash
python3 -I scripts/okr_crawl.py --seed <okr_id> --out <临时目录>
```

公司对齐网是连通的，从任何一个中层出发都能爬到全公司（约 240 份 OKR 约 2 分钟）。只想看局部可以加 `--max 50`。

## 写入（只在员工明确同意后）

```bash
# 1. 预览
lark-cli okr +batch-create --cycle-id <周期id> --input @okr.json --dry-run --as user
# 2. 创建（O 和 KR 一起建，失败会自动回滚）
lark-cli okr +batch-create --cycle-id <周期id> --input @okr.json --as user
# 3. 权重
lark-cli okr +weight --help        # 按帮助设置 O 和 KR 权重
# 4. 对齐：本人 O 对齐到上级 O
lark-cli okr objective.alignments create --objective-id <本人O的id> \
  --data '{"to_entity_id":"<上级O的id>","to_entity_type":2}' --as user
# 5. 读回核对
lark-cli okr +cycle-detail --cycle-id <周期id> --as user
```

`okr.json` 格式：

```json
[{"text":"O 内容","krs":[{"text":"KR 内容","mention":["ou_协同人"]}]}]
```

`mention` 会以 @ 的形式追加在文本末尾，所以文本里不要再手写 `@某人`。上级 O 的 id 从 `all.json` 的 `objective_list[].id` 里取。

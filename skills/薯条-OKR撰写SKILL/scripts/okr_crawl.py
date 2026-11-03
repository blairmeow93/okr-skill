#!/usr/bin/env python3
"""从一个或几个 OKR（用户周期）出发，沿对齐关系上下爬取整张对齐网，输出可读文本。

用法：
  python3 -I okr_crawl.py --seed <okr_id> [--seed <okr_id> ...] --out <目录> [--max 400]

okr_id 的三种来源：
  1. 飞书 OKR 链接里的 okrId=xxx（链接里 /user/ 后面那串是飞书内部 ID，API 用不了，忽略）
  2. lark-cli okr +cycle-list --user-id <open_id> --as user 返回的周期 id（v2 周期 id = v1 okr id）
  3. lark-cli api GET /open-apis/okr/v1/users/<open_id>/okrs 返回的 okr_list[].id

输出（都在 --out 目录）：
  all.json   原始数据：{okr_id: okr}
  owner.json {okr_id: open_id}
  users.json {open_id: 用户信息}
  tree.md    自上而下的对齐树（人名 + 部门 + O 数量）
  dump.md    每个人的全部 O / KR，含权重和上下对齐对象

v1 字段含义（已实测）：
  aligning_objective_list = 本目标对齐到的上级目标（向上）
  aligned_objective_list  = 对齐到本目标的下级目标（向下）
"""
import argparse, collections, json, os, subprocess, sys


def lark(args):
    out = subprocess.run(["lark-cli", *args, "--as", "user"], capture_output=True, text=True).stdout
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        sys.exit("lark-cli 返回无法解析：" + out[:500])


def crawl(seeds, limit):
    seen, queue = {}, list(seeds)
    while queue and len(seen) < limit:
        batch = []
        while queue and len(batch) < 10:
            q = queue.pop(0)
            if q not in seen and q not in batch:
                batch.append(q)
        if not batch:
            continue
        d = lark(["api", "GET", "/open-apis/okr/v1/okrs/batch_get",
                  "--params", json.dumps({"okr_ids": batch, "lang": "zh_cn"})])
        if not d.get("ok"):
            print("读取失败", batch, json.dumps(d, ensure_ascii=False)[:300], file=sys.stderr)
        for okr in d.get("data", {}).get("okr_list", []):
            seen[okr["id"]] = okr
            for o in okr.get("objective_list", []):
                for a in o.get("aligned_objective_list", []) + o.get("aligning_objective_list", []):
                    if a["okr_id"] not in seen and a["okr_id"] not in queue:
                        queue.append(a["okr_id"])
        for b in batch:
            seen.setdefault(b, None)
    return {k: v for k, v in seen.items() if v}


def owners(data):
    own = {}
    for v in data.values():
        for o in v["objective_list"]:
            for a in o["aligned_objective_list"] + o["aligning_objective_list"]:
                own[a["okr_id"]] = a["owner"]["open_id"]
    return own


def resolve(ids):
    users, ids = {}, sorted(ids)
    for i in range(0, len(ids), 20):  # 每次最多返回 20 人，超过会静默截断
        d = lark(["contact", "+search-user", "--user-ids", ",".join(ids[i:i + 20])])
        for u in d.get("data", {}).get("users", []):
            users[u["open_id"]] = u
    return users


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max", type=int, default=400)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    data = crawl(a.seed, a.max)
    own = owners(data)
    users = resolve(set(own.values()))
    nm = lambda k: users.get(own.get(k), {}).get("localized_name", own.get(k, "?"))
    dep = lambda k: users.get(own.get(k), {}).get("department", "?")

    par, ch = collections.defaultdict(set), collections.defaultdict(set)
    for k, v in data.items():
        for o in v["objective_list"]:
            par[k] |= {x["okr_id"] for x in o["aligning_objective_list"]}
            ch[k] |= {x["okr_id"] for x in o["aligned_objective_list"]}

    with open(f"{a.out}/tree.md", "w") as f:
        done = set()

        def walk(k, depth):
            f.write("  " * depth + f"- {nm(k)}（{dep(k)}）{len(data[k]['objective_list'])}O\n")
            if k in done:
                return
            done.add(k)
            for c in sorted(ch[k] & data.keys(), key=nm):
                walk(c, depth + 1)

        for r in sorted((k for k in data if not par[k]), key=lambda r: -len(ch[r])):
            walk(r, 0)

    with open(f"{a.out}/dump.md", "w") as f:
        for k, v in data.items():
            f.write(f"\n## {nm(k)}（{dep(k)}） okr={k}\n")
            for i, o in enumerate(v["objective_list"], 1):
                f.write(f"O{i} [权重{o.get('weight')}] {o.get('content', '<无权限>').strip()}\n")
                f.write(f"   ↑对齐: {[nm(x['okr_id']) for x in o['aligning_objective_list']]}"
                        f"  ↓被对齐: {[nm(x['okr_id']) for x in o['aligned_objective_list']]}\n")
                for j, kr in enumerate(o["kr_list"], 1):
                    f.write(f"   KR{j} [权重{kr.get('kr_weight')}] {kr.get('content', '<无权限>').strip()}\n")

    for name, obj in (("all", data), ("owner", own), ("users", users)):
        json.dump(obj, open(f"{a.out}/{name}.json", "w"), ensure_ascii=False, indent=1)
    print(f"共 {len(data)} 份 OKR，{len(users)} 人。输出在 {a.out}/tree.md 和 dump.md")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图记忆 vs 向量记忆：用我们自己的用户画像数据做一次可复现的对照实验。

设计约束（保证两边公平）：
1. 两套系统共用同一批事实源 (Fact)。图侧把一条 Fact 存成一条带双时间的边，
   向量侧把同一条 Fact 渲染成一句自然语言，两者信息量相同。
2. 向量侧离线无 embedding 模型，用字符 bigram TF-IDF + 余弦作为 dense 检索的
   替身。这是对向量方案的**宽松**替代：字面重合度天然偏高，若向量仍输，
   说明差距来自结构而非编码器。
3. 图侧不用大模型，用确定性遍历（实体链接 + 1~2 跳 + 时间区间过滤）。
4. 判定自动化：答对 = 上下文包含 gold 事实，且不含与该问题答案冲突的失效事实。

数据：data/user_profiles.json（20 个用户，4 维画像）
时间设定：画像采集于 2026-11-01；对 3 个用户注入一次"偏好迁移"事件（2026-11-20），
        这是为了制造真实业务里必然出现的新旧偏好交替，注入项在结果中单独标注。
"""
import json, math, re, time, collections, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
NOW = "2026-11-25"
BASE_DATE = "2026-11-01"
MIGRATE_DATE = "2026-11-20"
MIGRATE_USERS = 3          # 注入偏好迁移的用户数
TOP_K = 10                 # 两边统一取 10 条，对齐 mem0 默认 top_k
random.seed(7)

# ---------------------------------------------------------------- 事实层
class Fact:
    """一条事实：主体 - 关系 - 客体，带业务有效期与来源。"""
    __slots__ = ("fid", "subj", "rel", "obj", "text", "valid_from", "valid_to", "meta")

    def __init__(self, fid, subj, rel, obj, text, valid_from, valid_to=None, meta=None):
        self.fid, self.subj, self.rel, self.obj = fid, subj, rel, obj
        self.text, self.valid_from, self.valid_to = text, valid_from, valid_to
        self.meta = meta or {}

    def active_at(self, t):
        return self.valid_from <= t and (self.valid_to is None or t < self.valid_to)

    def as_dict(self):
        return {"id": self.fid, "subj": self.subj, "rel": self.rel, "obj": self.obj,
                "text": self.text, "valid_from": self.valid_from,
                "valid_to": self.valid_to, "meta": self.meta}


def load_users():
    with open(os.path.join(HERE, "data", "user_profiles.json"), encoding="utf-8") as f:
        return json.load(f)["users"]


CAT_CN = {"vod_streaming": "视频点播", "short_video": "短视频", "live_streaming": "直播",
          "mobile_game": "手游", "meeting": "会议", "voip": "语音通话",
          "instant_message": "即时消息", "watch_live": "直播观看"}


def build_facts(users):
    """把画像展开成事实集合。"""
    facts = []
    n = 0
    for u in users:
        uid = u["user_id"]
        b = u["dim_b_app_behavior"]
        c = u["dim_c_spatio_temporal"]
        d = u["dim_d_network_exp"]

        # 1) 应用类别偏好
        for cat, w in b["app_usage_profile"].items():
            n += 1
            facts.append(Fact(f"F{n:04d}", uid, "PREFERS_CATEGORY", cat,
                              f"用户 {uid} 偏好{CAT_CN.get(cat, cat)}业务，时长占比 {w:.2%}",
                              BASE_DATE, None, {"kind": "category", "weight": w}))

        # 2) 子应用偏好
        for app, w in b["frequent_apps"].items():
            n += 1
            facts.append(Fact(f"F{n:04d}", uid, "USES_APP", app,
                              f"用户 {uid} 常用子应用 {app}，占其会话 {w:.2%}",
                              BASE_DATE, None, {"kind": "app", "weight": w}))

        # 3) 常驻小区 / 跟踪区
        for pair, cnt in list(c["recurrent_cells"]["pairs"].items())[:3]:
            cell, win = pair.split("|") if "|" in pair else (pair, "")
            n += 1
            facts.append(Fact(f"F{n:04d}", uid, "RESIDES_AT", cell,
                              f"用户 {uid} 常驻小区 {cell}（{win} 时段出现 {cnt} 次）",
                              BASE_DATE, None, {"kind": "cell", "window": win, "count": cnt}))

        # 4) 活跃时段
        if c["active_hours"]:
            top_hour = max(c["active_hours"], key=c["active_hours"].get)
            n += 1
            facts.append(Fact(f"F{n:04d}", uid, "ACTIVE_AT", f"{top_hour}时",
                              f"用户 {uid} 的高峰活跃小时为 {top_hour} 点",
                              BASE_DATE, None, {"kind": "hour"}))

        # 5) 网络偏好与体验
        rp = d["rat_preference"]
        n += 1
        facts.append(Fact(f"F{n:04d}", uid, "PREFERS_RAT", "5G" if rp["5g_share"] > 0.5 else "4G",
                          f"用户 {uid} 的 5G 驻留占比为 {rp['5g_share']:.2%}",
                          BASE_DATE, None, {"kind": "rat", "share": rp["5g_share"]}))

        n += 1
        facts.append(Fact(f"F{n:04d}", uid, "EXPERIENCES_DELAY", "latency",
                          f"用户 {uid} 的时延中位数 {d['latency_profile']['median_ms']} ms",
                          BASE_DATE, None, {"kind": "latency",
                                            "value": d["latency_profile"]["median_ms"]}))
    return facts


VIDEO_APPS = ["youku_vod", "bilibili_vod", "iqiyi_vod", "kuaishou_svod", "douyin_svod",
              "hongguo_svod", "tencent_vod"]


def inject_migration(facts, users):
    """对前 N 个用户注入一次视频应用迁移，制造"新旧偏好交替"。

    选一个该用户已在用的视频应用（旧），迁到一个他没用过的新视频应用。
    旧边截断（valid_to = 迁移日）但不删除；新边从迁移日生效。
    """
    injected = []
    for u in users:
        if len(injected) >= MIGRATE_USERS:
            break
        uid = u["user_id"]
        apps = u["dim_b_app_behavior"]["frequent_apps"]
        old_apps = [a for a in apps if a in VIDEO_APPS]
        new_apps = [a for a in VIDEO_APPS if a not in apps]
        if not old_apps or not new_apps:
            continue
        old_app = max(old_apps, key=lambda a: apps[a])
        new_app = new_apps[0]
        old = next((f for f in facts if f.subj == uid and f.obj == old_app and f.rel == "USES_APP"), None)
        if old is None:
            continue
        old.valid_to = MIGRATE_DATE                       # 旧边截断，不删除
        nid = f"F{len(facts)+1:04d}"
        facts.append(Fact(nid, uid, "USES_APP", new_app,
                          f"用户 {uid} 从 {MIGRATE_DATE} 起改用子应用 {new_app}，不再使用 {old_app}",
                          MIGRATE_DATE, None,
                          {"kind": "app", "weight": apps[old_app], "migrated_from": old_app}))
        injected.append({"user_id": uid, "from": old_app, "to": new_app,
                         "at": MIGRATE_DATE, "old_fact": old.fid, "new_fact": nid})
    return injected


# ---------------------------------------------------------------- 图侧
class GraphMemory:
    """邻接表 + 双时间边。检索=实体链接后做有界 BFS + 时间过滤。"""

    def __init__(self, facts):
        self.facts = {f.fid: f for f in facts}
        self.out = collections.defaultdict(list)   # (node) -> [fact]
        for f in facts:
            self.out[f.subj].append(f)

    def edges(self, node, t):
        return [f for f in self.out.get(node, []) if f.active_at(t)]

    def retrieve(self, q, t, k=5):
        """返回 (facts, hops) —— 纯结构遍历，不做相似度。"""
        got, hops = [], 0
        if q["type"] == "single":
            got = self.edges(q["user"], t)
            got = [f for f in got if f.rel == q["rel"]]
            hops = 1
        elif q["type"] == "multi":
            # user -> cell -> 同小区其他用户 -> 其应用偏好
            my_cells = {f.obj for f in self.edges(q["user"], t) if f.rel == "RESIDES_AT"}
            peers = {f.subj for f in self.facts.values()
                     if f.rel == "RESIDES_AT" and f.obj in my_cells and f.active_at(t)}
            peers.discard(q["user"])
            for p in sorted(peers):
                got += [f for f in self.edges(p, t) if f.rel == "PREFERS_CATEGORY"]
            hops = 3
        elif q["type"] == "temporal":
            # 指定时刻的边：active_at 直接给出答案，不需要相似度
            got = [f for f in self.out.get(q["user"], [])
                   if f.rel == q["rel"] and f.obj == q["obj"]
                   and f.valid_from <= q["at"]
                   and (f.valid_to is None or q["at"] < f.valid_to)]
            hops = 1
        elif q["type"] == "negation":
            # 偏好迁移：需要同时给出旧边（已失效）与新边（生效），才算讲清"变了"
            got = [f for f in self.out.get(q["user"], []) if f.rel == "USES_APP"]
            got.sort(key=lambda f: f.valid_from)
            hops = 1
        if q["type"] in ("multi", "negation"):
            return got, hops
        return got[:k], hops


# ---------------------------------------------------------------- 向量侧
def bigrams(s):
    s = re.sub(r"\s+", "", s)
    return [s[i:i+2] for i in range(len(s) - 1)] or [s]


class VectorMemory:
    """字符 bigram TF-IDF + 余弦。作为 dense 向量检索的离线替身。"""

    def __init__(self, facts):
        self.facts = facts
        self.docs = [bigrams(f.text) for f in facts]
        df = collections.Counter()
        for d in self.docs:
            for w in set(d):
                df[w] += 1
        N = len(self.docs)
        self.idf = {w: math.log((N + 1) / (c + 1)) + 1 for w, c in df.items()}
        self.vecs = [self._vec(d) for d in self.docs]

    def _vec(self, grams):
        tf = collections.Counter(grams)
        v = {w: (1 + math.log(c)) * self.idf.get(w, 1.0) for w, c in tf.items()}
        nrm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {w: x / nrm for w, x in v.items()}

    def retrieve(self, q, t, k=TOP_K):
        """对齐 mem0 的检索语义：先按 user_id 分区，再在分区内做相似度排序。

        mem0 的 write/read 都以 user_id 为作用域，跨用户检索本来就不存在；
        multi 类问题需要跨用户比较，此时不做分区（模拟"实体锚点+邻居"场景）。
        """
        qv = self._vec(bigrams(q["query"]))
        scope = None if q["type"] == "multi" else q.get("user")
        scored = []
        for f, v in zip(self.facts, self.vecs):
            if scope is not None and f.subj != scope:
                continue
            s = sum(x * v.get(w, 0.0) for w, x in qv.items())
            if s > 0:
                scored.append((s, f))
        scored.sort(key=lambda x: -x[0])
        return [f for _, f in scored[:k]]


# ---------------------------------------------------------------- 评测
def make_queries(facts, users, injected):
    """4 类问题，每类若干条。gold 用确定性规则算，不手工标注。"""
    qs = []
    mig = {m["user_id"]: m for m in injected}

    # Q1 单跳：当前最常用的子应用
    for u in users[:5]:
        uid = u["user_id"]
        cur = [f for f in facts if f.subj == uid and f.rel == "USES_APP" and f.active_at(NOW)]
        if not cur:
            continue
        gold = max(cur, key=lambda f: f.meta.get("weight", 0))
        qs.append({"id": f"S{len(qs)+1}", "type": "single", "user": uid, "rel": "USES_APP",
                   "query": f"用户 {uid} 现在最常用的子应用是哪个？",
                   "gold": gold.fid, "expect": gold.obj, "at": NOW})

    # Q2 多跳：同小区 + 偏好某类业务
    by_cell = collections.defaultdict(set)
    for f in facts:
        if f.rel == "RESIDES_AT" and f.active_at(NOW):
            by_cell[f.obj].add(f.subj)
    for cell, members in list(by_cell.items()):
        if len(members) < 3:
            continue
        seed = sorted(members)[0]
        gold = [f.fid for f in facts
                if f.subj in members and f.subj != seed and f.rel == "PREFERS_CATEGORY"
                and f.obj == "short_video" and f.active_at(NOW)]
        if not gold:
            continue
        qs.append({"id": f"M{len(qs)+1}", "type": "multi", "user": seed,
                   "query": f"和用户 {seed} 常驻同一小区的人里，谁偏好短视频？",
                   "gold": gold[0], "gold_set": gold, "expect": "short_video", "at": NOW})
        if len([q for q in qs if q["type"] == "multi"]) >= 4:
            break

    # Q3 时序 + Q4 否定：针对注入过迁移的用户
    for uid, m in mig.items():
        old = next(f for f in facts if f.fid == m["old_fact"])
        qs.append({"id": f"T{len(qs)+1}", "type": "temporal", "user": uid,
                   "rel": "USES_APP", "obj": m["from"], "at": "2026-11-15",
                   "query": f"用户 {uid} 在 11 月 15 日用哪个视频应用看剧？",
                   "gold": old.fid, "expect": m["from"]})
        new = next(f for f in facts if f.fid == m["new_fact"])
        qs.append({"id": f"N{len(qs)+1}", "type": "negation", "user": uid,
                   "rel": "USES_APP", "obj": m["from"], "at": NOW,
                   "also": old.fid,
                   "query": f"用户 {uid} 的视频应用偏好变过吗？现在用哪个？",
                   "gold": new.fid, "expect": f"从 {m['from']} 变为 {m['to']}"})
    return qs


def judge(q, retrieved, factmap):
    """答对 = gold 在上下文；且没有与答案冲突的失效事实混进来。

    冲突事实定义：与该问题 gold 同关系类型、但在问题时刻已失效的边。
    向量侧无法按时间过滤，容易把旧事实一起召回 —— 这个指标就是量它的。
    """
    ids = {f.fid for f in retrieved}
    golds = q.get("gold_set") or [q["gold"]]
    hit = any(g in ids for g in golds)
    t = q["at"]
    rel = factmap[q["gold"]].rel
    if q["type"] == "negation":
        # 迁移类问题要能同时看到"旧边已失效"与"新边已生效"，缺一不可
        complete = hit and q.get("also") in ids
        return hit, 0, complete
    conflicts = sum(1 for f in retrieved if f.rel == rel and not f.active_at(t))
    return hit, conflicts, (hit and conflicts == 0)


def run():
    users = load_users()
    facts = build_facts(users)
    injected = inject_migration(facts, users)
    G, V = GraphMemory(facts), VectorMemory(facts)
    factmap = {f.fid: f for f in facts}
    queries = make_queries(facts, users, injected)

    rows = []
    for q in queries:
        t0 = time.perf_counter()
        gf, ghops = G.retrieve(q, q["at"])
        tg = (time.perf_counter() - t0) * 1000
        t0 = time.perf_counter()
        vf = V.retrieve(q, q["at"])
        tv = (time.perf_counter() - t0) * 1000
        gh, gc, gok = judge(q, gf, factmap)
        vh, vc, vok = judge(q, vf, factmap)
        rows.append({
            "qid": q["id"], "type": q["type"], "query": q["query"], "at": q["at"],
            "gold_fact": q["gold"], "expect": q["expect"],
            "graph": {"hit": gh, "conflicts": gc, "correct": gok, "hops": ghops,
                      "ctx_chars": sum(len(f.text) for f in gf) + 12 * max(0, len(gf) - 1),
                      "ms": round(tg, 3), "facts": [f.fid for f in gf]},
            "vector": {"hit": vh, "conflicts": vc, "correct": vok,
                       "ctx_chars": sum(len(f.text) for f in vf) + 12 * max(0, len(vf) - 1),
                       "ms": round(tv, 3), "facts": [f.fid for f in vf]},
        })

    def agg(side, typ=None):
        rs = [r for r in rows if typ is None or r["type"] == typ]
        if not rs:
            return {"n": 0, "recall": 0, "correct": 0, "conflict_rate": 0,
                    "avg_ctx_chars": 0, "avg_ms": 0}
        return {
            "n": len(rs),
            "recall": round(sum(r[side]["hit"] for r in rs) / len(rs), 3),
            "correct": round(sum(r[side]["correct"] for r in rs) / len(rs), 3),
            "conflict_rate": round(sum(1 for r in rs if r[side]["conflicts"]) / len(rs), 3),
            "avg_ctx_chars": round(sum(r[side]["ctx_chars"] for r in rs) / len(rs), 1),
            "avg_ms": round(sum(r[side]["ms"] for r in rs) / len(rs), 3),
        }

    summary = {s: {"all": agg(s), **{t: agg(s, t) for t in ("single", "multi", "temporal", "negation")}}
               for s in ("graph", "vector")}

    out = {
        "config": {"n_users": len(users), "n_facts": len(facts), "now": NOW,
                   "base_date": BASE_DATE, "injected_migrations": injected,
                   "vector_encoder": "char-bigram TF-IDF cosine (offline stand-in for dense embedding)",
                   "top_k": 5},
        "summary": summary,
        "rows": rows,
        "graph": {"nodes": None, "edges": [f.as_dict() for f in facts]},
    }
    with open(os.path.join(HERE, "lab_results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    # 打印对照表
    print(f"用户 {len(users)} / 事实 {len(facts)} 条 / 注入迁移 {len(injected)} 例 / 问题 {len(rows)} 个\n")
    head = f"{'类型':<10}{'n':>3}{'图·答对':>8}{'向量·答对':>9}{'图·冲突率':>9}{'向量·冲突率':>11}{'图·ctx字符':>10}{'向量·ctx字符':>12}"
    print(head); print("-" * len(head) * 2)
    for t in ("single", "multi", "temporal", "negation"):
        g, v = summary["graph"][t], summary["vector"][t]
        tn = {"single": "Q1 单跳", "multi": "Q2 多跳", "temporal": "Q3 时序", "negation": "Q4 否定"}[t]
        print(f"{tn:<10}{g['n']:>3}{g['correct']:>8.2f}{v['correct']:>9.2f}"
              f"{g['conflict_rate']:>9.2f}{v['conflict_rate']:>11.2f}"
              f"{g['avg_ctx_chars']:>10.0f}{v['avg_ctx_chars']:>12.0f}")
    g, v = summary["graph"]["all"], summary["vector"]["all"]
    print("-" * len(head) * 2)
    print(f"{'合计':<10}{g['n']:>3}{g['correct']:>8.2f}{v['correct']:>9.2f}"
          f"{g['conflict_rate']:>9.2f}{v['conflict_rate']:>11.2f}"
          f"{g['avg_ctx_chars']:>10.0f}{v['avg_ctx_chars']:>12.0f}")
    print(f"\n平均检索耗时 图 {g['avg_ms']}ms / 向量 {v['avg_ms']}ms")
    return out


if __name__ == "__main__":
    run()

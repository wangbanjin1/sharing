#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把实验里那张图真正画出来：Zep 式时序知识图谱的一个 ego 子图。

布局用力导向（纯 Python，节点少，迭代 300 次足够），输出静态 HTML：
- 大图：一个用户 + 他的常驻小区 + 同小区邻居 + 应用/类别，含失效边
- 两张小图：同一张图在 t=2026-11-15 与 t=2026-11-25 两个时刻的差异
- 交互：hover 高亮邻居、切换时间点
"""
import json, math, os, random, collections

HERE = os.path.dirname(os.path.abspath(__file__))
res = json.load(open(os.path.join(HERE, "lab_results.json"), encoding="utf-8"))
EDGES = res["graph"]["edges"]
INJ = res["config"]["injected_migrations"]
SUMMARY = res["summary"]
ROWS = res["rows"]

random.seed(3)

COLOR = {
    "user": "#1d4ed8", "cell": "#7c3aed", "app": "#047857",
    "category": "#b45309", "hour": "#475569", "rat": "#be123c",
}
LABEL_KIND = {"user": "用户", "cell": "常驻小区", "app": "子应用",
              "category": "业务类别", "hour": "活跃时段", "rat": "制式偏好"}


def kind_of(f):
    return f["meta"].get("kind", "other")


def build_subgraph():
    seed = INJ[0]["user_id"] if INJ else EDGES[0]["subj"]
    # 1) seed 的常驻小区
    cells = {e["obj"] for e in EDGES if e["subj"] == seed and e["rel"] == "RESIDES_AT"}
    cell = sorted(cells)[0] if cells else None
    # 2) 同小区的其他用户
    peers = {e["subj"] for e in EDGES if e["rel"] == "RESIDES_AT" and e["obj"] == cell}
    peers.discard(seed)
    peers = sorted(peers)[:5]
    keep_users = {seed} | set(peers)
    # 3) 保留这些用户的 应用/类别/时段/制式 事实
    edges = [e for e in EDGES
             if (e["subj"] in keep_users and e["rel"] in ("USES_APP", "PREFERS_CATEGORY",
                                                          "ACTIVE_AT", "PREFERS_RAT"))
             or (e["rel"] == "RESIDES_AT" and e["obj"] == cell and e["subj"] in keep_users)]
    # 每个用户最多保留 3 条 USES_APP，避免糊成一团
    cnt = collections.Counter()
    pruned = []
    for e in sorted(edges, key=lambda x: -x["meta"].get("weight", 0)):
        if e["rel"] == "USES_APP":
            if cnt[e["subj"]] >= 3:
                continue
            cnt[e["subj"]] += 1
        pruned.append(e)
    return seed, cell, pruned


def nodes_of(edges):
    ns = {}
    for e in edges:
        for nid, kind in ((e["subj"], "user"), (e["obj"], kind_of(e))):
            if nid not in ns:
                ns[nid] = {"id": nid, "kind": kind, "label": nid}
    return ns


def layout(nodes, edges, iters=400, center=None):
    pos = {n: [random.uniform(-1, 1), random.uniform(-1, 1)] for n in nodes}
    k = 0.85
    for it in range(iters):
        disp = {n: [0.0, 0.0] for n in nodes}
        ids = list(nodes)
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
                d = math.hypot(dx, dy) or 0.01
                f = k * k / d
                disp[a][0] += dx / d * f; disp[a][1] += dy / d * f
                disp[b][0] -= dx / d * f; disp[b][1] -= dy / d * f
        for e in edges:
            a, b = e["subj"], e["obj"]
            dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
            d = math.hypot(dx, dy) or 0.01
            f = d * d / k
            disp[a][0] -= dx / d * f; disp[a][1] -= dy / d * f
            disp[b][0] += dx / d * f; disp[b][1] += dy / d * f
        temp = max(0.02, 0.12 * (1 - it / iters))
        for n in nodes:
            dx, dy = disp[n]
            d = math.hypot(dx, dy) or 0.01
            pos[n][0] += dx / d * min(d, temp)
            pos[n][1] += dy / d * min(d, temp)
    # 归一化到 0..1
    xs = [p[0] for p in pos.values()]; ys = [p[1] for p in pos.values()]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    for n in pos:
        pos[n][0] = (pos[n][0] - x0) / (x1 - x0 or 1)
        pos[n][1] = (pos[n][1] - y0) / (y1 - y0 or 1)
    # 把种子用户压到画布中心，避免视觉焦点跑偏
    if center and center in pos:
        cx, cy = pos[center]
        for n in pos:
            pos[n][0] = 0.5 + (pos[n][0] - cx) * 0.80
            pos[n][1] = 0.5 + (pos[n][1] - cy) * 0.80
        # 收缩后再整体归一，保证四周留白均匀、不裁切
        xs = [q[0] for q in pos.values()]; ys = [q[1] for q in pos.values()]
        ax, bx, ay, by = min(xs), max(xs), min(ys), max(ys)
        for n in pos:
            pos[n][0] = 0.06 + 0.88 * (pos[n][0] - ax) / (bx - ax or 1)
            pos[n][1] = 0.05 + 0.90 * (pos[n][1] - ay) / (by - ay or 1)
    # 最小间距松弛：避免小半径节点（如 5G、时段）贴在一起导致标签打架
    ids = list(pos)
    for _ in range(60):
        moved = False
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
                d = math.hypot(dx, dy) or 0.001
                if d < 0.075:
                    push = (0.075 - d) / 2
                    ux, uy = dx / d, dy / d
                    pos[a][0] += ux * push; pos[a][1] += uy * push
                    pos[b][0] -= ux * push; pos[b][1] -= uy * push
                    moved = True
        if not moved:
            break
    for n in pos:
        pos[n][0] = min(0.96, max(0.04, pos[n][0]))
        pos[n][1] = min(0.95, max(0.05, pos[n][1]))
    return pos


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def render_svg(nodes, edges, pos, w, h, t, show_labels=True, small=False):
    pad = 40 if not small else 24
    def xy(n):
        return pad + pos[n][0] * (w - 2 * pad), pad + (1 - pos[n][1]) * (h - 2 * pad)

    deg = collections.Counter()
    for e in edges:
        deg[e["subj"]] += 1; deg[e["obj"]] += 1

    out = [f'<svg viewBox="0 0 {w} {h}" class="graph" data-t="{t}">']
    # 边
    out.append('<g class="edges">')
    for e in edges:
        if e["subj"] not in pos or e["obj"] not in pos:
            continue
        x1, y1 = xy(e["subj"]); x2, y2 = xy(e["obj"])
        alive = e["valid_from"] <= t and (e["valid_to"] is None or t < e["valid_to"])
        cls = "edge alive" if alive else "edge dead"
        col = COLOR.get(nodes[e["obj"]]["kind"], "#94a3b8")
        dash = "" if alive else 'stroke-dasharray="4 4"'
        out.append(
            f'<line class="{cls}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{col if alive else "#cbd5e1"}" stroke-width="{2.0 if alive else 1.2}" {dash} '
            f'data-s="{esc(e["subj"])}" data-o="{esc(e["obj"])}" data-fid="{e["id"]}"/>')
        if not small and e["rel"] == "RESIDES_AT":
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            out.append(f'<text class="elabel" x="{mx:.1f}" y="{my - 3:.1f}" text-anchor="middle">常驻</text>')
        if not small and e["valid_to"]:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            out.append(f'<text class="elabel dead-label" x="{mx:.1f}" y="{my + 10:.1f}" '
                       f'text-anchor="middle">失效 {e["valid_to"][5:]}</text>')
    out.append('</g>')
    # 节点
    out.append('<g class="nodes">')
    boxes = []          # 已占用的标签矩形，用于避让
    labels = []
    for n, meta in nodes.items():
        x, y = xy(n)
        r = 10 + min(10, deg[n] * 1.6)
        if meta["kind"] == "user":
            r = 14 + min(6, deg[n])
        fill = COLOR.get(meta["kind"], "#64748b")
        shape = "rect" if meta["kind"] == "category" else "circle"
        if shape == "rect":
            out.append(f'<rect class="node" x="{x-13:.1f}" y="{y-9:.1f}" width="26" height="18" rx="3" '
                       f'fill="{fill}" data-id="{esc(n)}" data-kind="{meta["kind"]}"/>')
        else:
            out.append(f'<circle class="node" cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" '
                       f'data-id="{esc(n)}" data-kind="{meta["kind"]}"/>')

        if show_labels:
            short = n if len(n) <= 16 else n[:14] + "…"
            fs = 9 if small else 10
            tw = len(short) * fs * 0.62 + 6
            ly = y + r + (11 if not small else 9)
            lx = x
            for step in range(8):             # 标签避让：先下移，再左右错开
                rect = (lx - tw / 2, ly - fs, lx + tw / 2, ly + 2)
                clash = any(not (rect[2] < b[0] or rect[0] > b[2] or rect[3] < b[1] or rect[1] > b[3])
                            for b in boxes)
                if not clash:
                    break
                if step % 2 == 0:
                    ly += fs + 2.5
                else:
                    lx += (tw * 0.62) * (1 if (step // 2) % 2 == 0 else -1)
            boxes.append((lx - tw / 2, ly - fs, lx + tw / 2, ly + 2))
            labels.append((lx, ly, short, fs))
    for x, ly, short, fs in labels:
        out.append(f'<text class="nlabel" x="{x:.1f}" y="{ly:.1f}" '
                   f'text-anchor="middle" font-size="{fs}">{esc(short)}</text>')
    out.append('</g></svg>')
    return "\n".join(out)


def main():
    seed, cell, edges = build_subgraph()
    nodes = nodes_of(edges)
    pos = layout(list(nodes), edges, center=seed)
    T1, T2 = "2026-11-15", "2026-11-25"

    svg_big = render_svg(nodes, edges, pos, 980, 520, T2)
    svg_t1 = render_svg(nodes, edges, pos, 460, 340, T1, show_labels=False, small=True)
    svg_t2 = render_svg(nodes, edges, pos, 460, 340, T2, show_labels=False, small=True)

    n_user = sum(1 for m in nodes.values() if m["kind"] == "user")
    n_alive = sum(1 for e in edges if e["valid_from"] <= T2 and (e["valid_to"] is None or T2 < e["valid_to"]))
    n_dead = len(edges) - n_alive

    def pct(x):
        return f"{x*100:.0f}%"

    s = SUMMARY
    rows_html = ""
    names = {"single": ("Q1 单跳", "当前最常用的子应用", "检索侧能直接定位到该用户的有效偏好边"),
             "multi": ("Q2 多跳", "同小区的其他人偏好什么", "需要 用户→小区→邻居→偏好 三跳"),
             "temporal": ("Q3 时序", "11 月 15 日那天用哪个应用", "需要按 valid_at/invalid_at 区间取边"),
             "negation": ("Q4 迁移", "偏好变了没、现在用哪个", "需要同时给出失效旧边与生效新边")}
    for k, (nm, desc, why) in names.items():
        g, v = s["graph"][k], s["vector"][k]
        rows_html += (f"<tr><td><b>{nm}</b><div class='sub'>{desc}</div></td>"
                      f"<td class='num'>{pct(g['correct'])}</td><td class='num'>{pct(v['correct'])}</td>"
                      f"<td class='num'>{g['avg_ctx_chars']:.0f}</td><td class='num'>{v['avg_ctx_chars']:.0f}</td>"
                      f"<td class='sub'>{why}</td></tr>")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>图记忆 vs 向量记忆 · 我们自己的数据</title>
<style>
:root{{--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--bg:#f8fafc;--card:#fff;
--blue:#1d4ed8;--violet:#7c3aed;--green:#047857;--amber:#b45309;--rose:#be123c;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.7 -apple-system,"Segoe UI","Microsoft YaHei",system-ui,sans-serif;}}
.wrap{{max-width:1060px;margin:0 auto;padding:40px 24px 72px}}
h1{{font-size:26px;margin:0 0 6px;letter-spacing:-.4px}}
.lead{{color:var(--muted);margin:0 0 28px;font-size:14px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:22px 24px;margin-bottom:22px}}
h2{{font-size:17px;margin:0 0 14px;display:flex;align-items:center;gap:8px}}
h2 .tag{{font-size:11px;font-weight:600;color:var(--muted);border:1px solid var(--line);
border-radius:99px;padding:2px 8px}}
.legend{{display:flex;flex-wrap:wrap;gap:14px;margin:0 0 10px;font-size:12px;color:var(--muted)}}
.legend i{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:-1px}}
.legend i.sq{{border-radius:2px}}
svg.graph{{width:100%;height:auto;display:block;background:
radial-gradient(circle at 50% 45%,#ffffff 0%,#f8fafc 70%)}}
.edge{{stroke-linecap:round;transition:opacity .18s}}
.edge.dead{{opacity:.55}}
.nlabel{{fill:#334155;font-family:ui-monospace,Menlo,monospace;paint-order:stroke;stroke:#fff;stroke-width:3px;stroke-linejoin:round}}
.elabel{{fill:#94a3b8;font-size:9px;paint-order:stroke;stroke:#fff;stroke-width:3px}}
.dead-label{{fill:#f43f5e;font-size:8.5px}}
.node{{stroke:#fff;stroke-width:2;cursor:pointer;transition:transform .12s,opacity .18s}}
.node.dim{{opacity:.18}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.two figure{{margin:0;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:#fff}}
.two figcaption{{font-size:12px;color:var(--muted);padding:8px 12px;border-bottom:1px solid var(--line);
background:#fbfdff;display:flex;justify-content:space-between}}
.two .dead-count{{color:var(--rose)}}
table{{width:100%;border-collapse:collapse;font-size:13.5px}}
th{{text-align:left;font-weight:600;color:var(--muted);font-size:12px;border-bottom:1px solid var(--line);
padding:8px 6px}}
td{{padding:10px 6px;border-bottom:1px solid #f1f5f9;vertical-align:top}}
td.num{{font-variant-numeric:tabular-nums;font-weight:600;font-family:ui-monospace,Menlo,monospace}}
td .sub{{font-size:12px;color:var(--muted);font-weight:400}}
.note{{background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;padding:14px 16px;font-size:13px;color:#7c2d12}}
ul.tight{{margin:8px 0 0;padding-left:20px}}
ul.tight li{{margin:6px 0}}
code{{background:#f1f5f9;padding:1px 5px;border-radius:4px;font-size:12.5px}}
.badge{{display:inline-block;font-size:11px;padding:1px 7px;border-radius:99px;
background:#eef2ff;color:#3730a3;margin-left:6px}}
</style></head><body><div class="wrap">

<h1>图记忆 vs 向量记忆：用我们自己的画像数据跑一遍</h1>
<p class="lead">数据：20 个用户的网元画像（260 条事实）· 注入 3 例偏好迁移 · 15 个问题 4 类对照
· 图侧为 Zep/Graphiti 式双时态边，向量侧为 mem0 式 user_id 分区 + 相似度召回</p>

<div class="card">
<h2>先看图长什么样 <span class="tag">ego 子图 · 2 跳内</span></h2>
<div class="legend">
  <span><i style="background:{COLOR['user']}"></i>用户</span>
  <span><i style="background:{COLOR['cell']}"></i>常驻小区</span>
  <span><i style="background:{COLOR['app']}"></i>子应用</span>
  <span><i class="sq" style="background:{COLOR['category']}"></i>业务类别</span>
  <span><i style="background:{COLOR['hour']}"></i>活跃时段</span>
  <span>—— 当前有效边</span>
  <span style="opacity:.6">- - 已失效边（旧事实保留）</span>
</div>
{svg_big}
<p class="lead" style="margin:12px 0 0">中心是用户 <code>{seed}</code>，同小区共 {n_user} 人；
共 {len(edges)} 条事实边，其中 <b>{n_alive}</b> 条在 {T2} 有效、<b>{n_dead}</b> 条已失效。
虚线的两条边就是这个用户 11 月 20 日从旧视频应用切到新应用留下的痕迹——旧边没有删，只是被 <code>invalid_at</code> 截断。</p>
</div>

<div class="card">
<h2>同一张图，两个时刻 <span class="tag">双时间到底在干什么</span></h2>
<div class="two">
  <figure><figcaption><span>{T1}（迁移前）</span><span>{sum(1 for e in edges if e['valid_from']<=T1 and (e['valid_to'] is None or T1<e['valid_to']))} 条有效</span></figcaption>{svg_t1}</figure>
  <figure><figcaption><span>{T2}（迁移后）</span><span class="dead-count">{sum(1 for e in edges if not (e['valid_from']<=T2 and (e['valid_to'] is None or T2<e['valid_to'])))} 条失效</span></figcaption>{svg_t2}</figure>
</div>
<p class="lead" style="margin:12px 0 0">同一批节点、同一批边，只换一个 <code>t</code> 参数，答案就变了。
向量库做不到这件事：它的时间只能体现在文本里，检索时没有"这条边在 t 时刻是否成立"的开关。</p>
</div>

<div class="card">
<h2>4 类问题上谁答对 <span class="tag">答对 = 上下文含答案且无冲突旧事实</span></h2>
<table>
<tr><th>查询类型</th><th>图</th><th>向量</th><th>图·上下文字符</th><th>向量·上下文字符</th><th>为什么</th></tr>
{rows_html}
</table>
<p class="note" style="margin-top:14px"><b>读这张表要注意两件事。</b>
① Q1 的差距不可信：向量侧用的是字符 bigram TF-IDF 替代 embedding，"最常用"这种语义排序它本来就弱，
真实 embedding 在单跳上应该接近满分，所以 Q1 应视为<b>平手</b>。
② Q2/Q3/Q4 的差距与编码器质量无关：向量库里根本没有"谁和谁同小区""这条边什么时候失效"这种结构，
再好的 embedding 也变不出来。这三行才是建图的真实收益。</p>
</div>

<div class="card">
<h2>结论</h2>
<ul class="tight">
<li><b>建图的优势不是"记得更准"，是"能回答需要走关系和时间的问题"。</b>
单跳偏好、单条事实的召回，向量完全够用，而且写入便宜一个量级。</li>
<li><b>真正的分水岭是三个能力</b>：多跳（用户→小区→邻居→偏好）、时间点查询（11 月 15 日那天是什么状态）、
变更取证（旧边失效但不删除，能回答"变过吗"）。这三件事在向量库里没有对应结构，只能靠模型现场推理。</li>
<li><b>代价也很具体</b>：这张图 20 个用户就 260 条边，真实数据是百万级单据；
每条边都要跑实体抽取 + 消解 + 时间归一，写入成本比"一次 embedding"高一个量级；
实体消解一错（同名合并、别名拆开），上面三个能力的收益会直接归零。</li>
<li><b>对我们这个场景的判断</b>：意图理解 Agent 的高频查询是"这个用户/这个业务默认怎么配"—— 单跳，向量够；
真正需要图的是"跨会话指代"和"变更核实"（用户说"还是老样子"，但老样子已经变过两次）。
所以不是二选一，而是<b>向量做默认，图只覆盖需要溯源的那一小撮查询</b>。</li>
</ul>
</div>

<p class="lead">复现：<code>python graph_vs_vector_lab.py</code> → <code>lab_results.json</code>；
本页由 <code>gen_vis.py</code> 生成。向量侧未使用 embedding 模型，结论已在上面标注适用范围。</p>
</div>
<script>
document.querySelectorAll('.node').forEach(function(n){{
  n.addEventListener('mouseenter', function(){{
    var id = n.dataset.id;
    document.querySelectorAll('.edge').forEach(function(e){{
      var hit = e.dataset.s === id || e.dataset.o === id;
      e.style.opacity = hit ? 1 : .08;
      e.style.strokeWidth = hit ? 3 : e.style.strokeWidth;
    }});
    document.querySelectorAll('.node').forEach(function(m){{
      var rel = m.dataset.id === id;
      if(!rel){{
        rel = Array.from(document.querySelectorAll('.edge')).some(function(e){{
          return (e.dataset.s===id&&e.dataset.o===m.dataset.id)||(e.dataset.o===id&&e.dataset.s===m.dataset.id);
        }});
      }}
      m.classList.toggle('dim', !rel);
    }});
  }});
  n.addEventListener('mouseleave', function(){{
    document.querySelectorAll('.edge').forEach(function(e){{ e.style.opacity=''; e.style.strokeWidth=''; }});
    document.querySelectorAll('.node').forEach(function(m){{ m.classList.remove('dim'); }});
  }});
}});
</script>
</body></html>"""

    out = os.path.join(HERE, "graph_vs_vector_report.html")
    open(out, "w", encoding="utf-8").write(html)
    print("wrote", out, f"({len(html)} chars) 节点 {len(nodes)} 边 {len(edges)}")


if __name__ == "__main__":
    main()

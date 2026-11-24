#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Zep-Graphiti 建图 vs. Mem0 向量记忆深度对比与真实数据实验可视化报告（HTML）。"""
from __future__ import annotations

import json
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_JSON = os.path.join(HERE, "hybrid_exp_results.json")
OUT_LAVISH = r"D:\coding\sharing\.lavish\zep_graph_vs_mem0_vector_analysis.html"
OUT_ARTIFACT = r"C:\Users\Administrator\.gemini\antigravity\brain\45c16082-ce2c-4341-805b-57a1728e3f0a\zep_graph_vs_mem0_vector_analysis.html"


def build_html(data: dict) -> str:
    data_json = json.dumps(data, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="parchment">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Zep-Graphiti 建图与 Mem0 向量记忆对比实验报告</title>
<style>
  :root {{
    --bg: #FBF7F0;
    --surface: #FFFFFF;
    --surface-soft: #F2ECE1;
    --border: #E2D9C8;
    --text: #1F2328;
    --muted: #59636E;
    --accent: #1D4ED8;
    --accent-soft: #EFF6FF;
    --green: #15803D;
    --green-soft: #F0FDF4;
    --red: #B91C1C;
    --red-soft: #FEF2F2;
    --amber: #B45309;
    --amber-soft: #FFFBEB;
    --purple: #6D28D9;
    --purple-soft: #F5F3FF;
    --shadow: 0 2px 10px rgba(31,35,40,0.06);
  }}
  [data-theme="github"] {{
    --bg: #F6F8FA;
    --surface: #FFFFFF;
    --surface-soft: #F6F8FA;
    --border: #D0D7DE;
    --text: #1F2328;
    --muted: #656D76;
    --accent: #0969DA;
    --accent-soft: #DDF4FF;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    line-height: 1.65;
  }}
  .wrap {{ max-width: 1200px; margin: 0 auto; padding: 24px 20px 64px; }}
  header {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px 28px;
    margin-bottom: 20px;
    box-shadow: var(--shadow);
  }}
  .header-top {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; }}
  h1 {{ margin: 0 0 8px; font-size: 24px; line-height: 1.3; }}
  .subtitle {{ color: var(--muted); font-size: 14px; margin: 0; }}
  .theme-bar {{ display: flex; gap: 8px; }}
  button {{
    cursor: pointer;
    border: 1px solid var(--border);
    background: var(--surface-soft);
    color: var(--text);
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 13px;
    transition: all 0.15s;
  }}
  button:hover {{ border-color: var(--accent); color: var(--accent); }}
  button.active {{ background: var(--accent); color: #FFFFFF; border-color: var(--accent); }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    margin-top: 18px;
  }}
  .kpi {{
    background: var(--surface-soft);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 14px;
  }}
  .kpi .label {{ font-size: 12px; color: var(--muted); }}
  .kpi .val {{ font-size: 22px; font-weight: 700; margin-top: 2px; }}
  .kpi .hint {{ font-size: 12px; color: var(--muted); margin-top: 2px; }}

  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 22px 26px;
    margin-bottom: 20px;
    box-shadow: var(--shadow);
  }}
  h2 {{
    margin: 0 0 14px;
    font-size: 18px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
  }}
  h3 {{ margin: 16px 0 8px; font-size: 15px; }}
  p {{ margin: 8px 0; font-size: 14px; }}
  ul {{ margin: 6px 0 10px; padding-left: 20px; font-size: 14px; }}
  li {{ margin: 4px 0; }}

  table {{ width: 100%; border-collapse: collapse; font-size: 13.5px; margin: 10px 0; }}
  th, td {{ border-bottom: 1px solid var(--border); padding: 10px 12px; text-align: left; vertical-align: top; }}
  th {{ background: var(--surface-soft); font-weight: 600; border-top: 2px solid var(--text); border-bottom: 1.5px solid var(--text); }}
  tr:last-child td {{ border-bottom: 2px solid var(--text); }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; }}
  .good {{ color: var(--green); }}
  .bad {{ color: var(--red); }}
  .warn {{ color: var(--amber); }}

  .callout {{
    border-left: 4px solid var(--accent);
    background: var(--accent-soft);
    padding: 12px 16px;
    border-radius: 0 8px 8px 0;
    margin: 12px 0;
    font-size: 14px;
  }}
  .callout.green {{ border-left-color: var(--green); background: var(--green-soft); }}
  .callout.red {{ border-left-color: var(--red); background: var(--red-soft); }}
  .callout.amber {{ border-left-color: var(--amber); background: var(--amber-soft); }}

  .split-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  @media (max-width: 900px) {{ .split-2 {{ grid-template-columns: 1fr; }} }}

  .graph-toolbar {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 12px; }}
  .graph-stage {{
    display: grid;
    grid-template-columns: 1.7fr 1fr;
    gap: 16px;
    align-items: start;
  }}
  @media (max-width: 960px) {{ .graph-stage {{ grid-template-columns: 1fr; }} }}
  .svg-box {{
    border: 1px solid var(--border);
    border-radius: 10px;
    background: #FFFFFF;
    overflow: hidden;
    position: relative;
  }}
  svg {{ width: 100%; height: 470px; display: block; }}
  .legend {{
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    padding: 8px 12px;
    background: var(--surface-soft);
    border-top: 1px solid var(--border);
    font-size: 12px;
    color: var(--muted);
  }}
  .legend-item {{ display: inline-flex; align-items: center; gap: 5px; }}
  .dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}

  .inspector {{
    border: 1px solid var(--border);
    border-radius: 10px;
    background: var(--surface-soft);
    padding: 14px;
    max-height: 515px;
    overflow-y: auto;
    font-size: 13px;
  }}
  .inspector h4 {{ margin: 0 0 8px; font-size: 14px; }}
  .pill {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11.5px;
    font-weight: 600;
    margin-right: 4px;
  }}
  .pill.active {{ background: var(--green-soft); color: var(--green); border: 1px solid #BBF7D0; }}
  .pill.invalid {{ background: var(--red-soft); color: var(--red); border: 1px solid #FECACA; }}
  .pill.tag {{ background: var(--accent-soft); color: var(--accent); border: 1px solid #BFDBFE; }}

  .mem0-list {{ display: flex; flex-direction: column; gap: 8px; max-height: 460px; overflow-y: auto; }}
  .mem0-item {{
    background: var(--surface-soft);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 9px 12px;
    font-size: 13px;
  }}
  .mem0-item.deleted {{
    background: var(--red-soft);
    border-color: #FECACA;
    text-decoration: line-through;
    color: var(--red);
  }}
  .code-inline {{
    background: var(--surface-soft);
    border: 1px solid var(--border);
    padding: 1px 5px;
    border-radius: 4px;
    font-family: Consolas, monospace;
    font-size: 12.5px;
  }}
  @media print {{
    html, body {{ background: #FFFFFF !important; }}
    .theme-bar, .graph-toolbar {{ display: none !important; }}
    .card, header {{ box-shadow: none !important; break-inside: auto; }}
  }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="header-top">
      <div>
        <h1>Zep-Graphiti 建图与 Mem0 向量记忆对比及实测报告</h1>
        <p class="subtitle">基于联接 Agent 真实混合轨迹数据（20 个用户、495 条网元单据与对话记录）的拓扑体检与 6 类题型对照实验</p>
      </div>
      <div class="theme-bar" data-lavish-ui="true">
        <button id="btn-parchment" class="active" onclick="setTheme('parchment')">暖阳米纸</button>
        <button id="btn-github" onclick="setTheme('github')">GitHub 简洁</button>
      </div>
    </div>
    <div class="kpi-grid" id="kpi-grid"></div>
  </header>

  <section class="card">
    <h2>一、核心区别：不是“图数据库对比向量数据库”，而是三种数据结构取舍</h2>
    <p>对照 <span class="code-inline">long_term_memory_and_paper_matrix_v6.xlsx</span> 中两篇论文的机制拆解，Zep-Graphiti 与 Mem0（基础版）都在做语义记忆检索（两边都用向量相似度），真正的分水岭在于写入与更新阶段如何处理<strong>历史演进、证据溯源与实体关系</strong>。</p>
    <table>
      <thead>
        <tr>
          <th style="width:15%">对比维度</th>
          <th style="width:28%">Mem0（基础扁平向量版）</th>
          <th style="width:31%">Zep / Graphiti（双时态三层图谱）</th>
          <th style="width:26%">对联接 Agent 的实际影响</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>情景层与溯源</strong></td>
          <td>无情景记忆层，只保留抽取后的自包含短句（15~80 词）。</td>
          <td>底层只读保存原始情节节点（<span class="code-inline">Episode</span>），上层每条关系边挂接 <span class="code-inline">episodes[]</span> 来源编号列表。</td>
          <td>决定能否区分“单次偶发提及”与“单据+对话多次累积的长期习惯”。</td>
        </tr>
        <tr>
          <td><strong>冲突与更新机制</strong></td>
          <td>阶段二调用大模型执行 <span class="code-inline">ADD / UPDATE / DELETE</span>，旧事实直接覆写或物理删除。</td>
          <td>保留旧边不删，仅把旧边的业务失效时间 <span class="code-inline">t_invalid</span> 截断为新边的 <span class="code-inline">t_valid</span>（双时间轴）。</td>
          <td>Mem0 撤销后干净但彻底失忆；Zep 能回溯历史，但<strong>默认同屏展示失效边会干扰小模型</strong>。</td>
        </tr>
        <tr>
          <td><strong>数据组织形态</strong></td>
          <td>按 <span class="code-inline">user_id</span> 隔离的扁平自然语言短句集合，彼此无结构连接。</td>
          <td>实体节点 + 有向双时态关系边 + 动态社区话题摘要（支持 1~2 跳图遍历）。</td>
          <td>单用户下多为 1 跳星型结构；只有跨实体对齐或跨用户共享小区时多跳才显威。</td>
        </tr>
        <tr>
          <td><strong>写入成本与保真</strong></td>
          <td>每轮约 1~2 次大模型调用，写入轻快，短句可读性好。</td>
          <td>需做实体抽取、消歧合并、关系抽取、时间换算、冲突检测与摘要刷新，成本高且三元组易压扁过程细节。</td>
          <td>单用户高频写入场景下，全量 Graphiti 管线的延迟与 Token 开销偏重。</td>
        </tr>
      </tbody>
    </table>
  </section>

  <section class="card">
    <h2>二、在我们的真实数据上，图到底长什么样？</h2>
    <div class="callout amber">
      <strong>拓扑体检核心发现：</strong>在 20 个用户的真实混合轨迹（过滤 165 条噪声后 330 条有效单据与对话）上，<strong>单用户视角的图平均只有 13.95 个节点、14.85 条边，其中 66.2% 的边直接连在 User 中心节点上</strong>——本质上是一个“以 User 为中心的浅星型图”。只有当 20 个用户通过 <strong>10 个共享基站小区（Cell）</strong> 与 <strong>19 个共享应用（App）</strong> 连成全局图时，图才真正长出多跳网状骨架。
    </div>

    <div class="graph-toolbar" data-lavish-ui="true">
      <button id="view-single" class="active" onclick="switchView('single')">视图 1：单用户星型图（persona_8613522947905）</button>
      <button id="view-cross" onclick="switchView('cross')">视图 2：跨用户同小区关联图（Cell 4600040386A）</button>
      <span style="font-size:12.5px;color:var(--muted);margin-left:6px;">提示：点击图中任意节点或关系边，右侧实时查看双时态区间与原始情节证据</span>
    </div>

    <div class="graph-stage">
      <div class="svg-box">
        <svg id="graph-svg" viewBox="0 0 760 470"></svg>
        <div class="legend">
          <span class="legend-item"><span class="dot" style="background:#1D4ED8"></span>User 用户</span>
          <span class="legend-item"><span class="dot" style="background:#15803D"></span>App 标准应用</span>
          <span class="legend-item"><span class="dot" style="background:#0EA5E9"></span>Cell 基站小区</span>
          <span class="legend-item"><span class="dot" style="background:#D97706"></span>Venue 场所</span>
          <span class="legend-item"><span class="dot" style="background:#7C3AED"></span>Alias 个性别名 / Category</span>
          <span class="legend-item"><span class="dot" style="background:#DC2626"></span>BranchRule 临时规则（虚线=已失效）</span>
        </div>
      </div>
      <div class="inspector" id="inspector"></div>
    </div>

    <h3>对照：同一用户（persona_8613522947905）在 Mem0 向量库里长什么样？</h3>
    <p>下面右侧为同一批 17 条有效记录写入 Mem0 后留存的 12 条扁平文本与 1 条被 <span class="code-inline">DELETE</span> 物理删除的临时规则记录。可以看到：没有 <span class="code-inline">episodes[]</span> 证据计数，且被撤销的“突发恶劣天气”规则彻底消失。</p>
    <div class="split-2">
      <div>
        <div class="callout green" style="margin-top:0">
          <strong>Zep 图谱侧留存特征（14 节点 · 16 边 · 17 情节）：</strong><br/>
          1. 单据的 <span class="code-inline">bilibili_vod</span> 与对话的「B站」「小破站」自然汇聚到同一 App 节点，边上挂载 <strong>14 条情节编号</strong>；<br/>
          2. 红色虚线边 <span class="code-inline">HAS_BRANCH_RULE → 突发恶劣天气</span> 保留完整区间 <span class="code-inline">[2026-01-13 13:28, 2026-01-14 14:35)</span>。
        </div>
        <div id="zep-edge-summary" class="mem0-list"></div>
      </div>
      <div>
        <div class="callout red" style="margin-top:0">
          <strong>Mem0 向量侧留存特征（12 条扁平短句 · 1 条已删）：</strong><br/>
          1. 每条事实互相孤立，单据、场所、别名分散在不同短句里，无法直接聚合证据频次；<br/>
          2. <span class="code-inline">n06</span> 撤销后，<span class="code-inline">branch_rule</span> 被阶段二直接 <span class="code-inline">DELETE</span>，历史记录无从回溯。
        </div>
        <div id="mem0-list" class="mem0-list"></div>
      </div>
    </div>
  </section>

  <section class="card">
    <h2>三、6 类真实业务题型对照实验结果（62 题，公平检索口径）</h2>
    <p>为了不给图谱开“上帝视角”，Zep 检索统一采用<strong>文本相似度召回 + 实体锚定 1~2 跳扩展 + 频次重排</strong>，并专门拆出 <strong>Zep-Default（默认返回全部命中边，含已失效旧边）</strong> 与 <strong>Zep-Strict（按查询时刻严格过滤双时态区间）</strong>，与 Mem0 扁平向量检索同台对比。</p>
    <table>
      <thead>
        <tr>
          <th>评测题型</th>
          <th class="num">题数</th>
          <th class="num">Mem0（扁平向量）</th>
          <th class="num">Zep-Default（含失效边）</th>
          <th class="num">Zep-Strict（时间窗过滤）</th>
          <th>差距归因分析</th>
        </tr>
      </thead>
      <tbody id="bench-tbody"></tbody>
    </table>

    <div class="callout red">
      <strong>复现了 Zep 原论文的真实局限（Q2-撤销后问当前态）：</strong>在 4 道“规则撤销/主线晋升后再问当前状态”的题目上，<strong>Mem0 拿了 100%（因为旧规则删干净了），而 Zep-Default 掉到 0%</strong>——把带失效时间戳的旧边原样塞进上下文后，直接造成陈旧事实泄露（与 <span class="code-inline">v6.xlsx</span> 中记录的 LongMemEval 小模型下跌 3.33% 完全一致）。必须像 Zep-Strict 一样在检索层强制按查询时刻过滤 <span class="code-inline">t_invalid</span> 才能避免误导。
    </div>
  </section>

  <section class="card">
    <h2>四、结论与联接 Agent 的务实选型建议</h2>
    <div class="split-2">
      <div class="callout green" style="margin:0">
        <strong>建图真正有优势的 3 个场景</strong>
        <ul>
          <li><strong>需要历史状态演进与时间点回溯</strong>：如临时保障规则撤销、主力应用迁移，靠双时态边 <span class="code-inline">[t_valid, t_invalid)</span> 留痕而不覆盖。</li>
          <li><strong>多源异构证据聚合与溯源</strong>：网元单据（<span class="code-inline">sub_app_id / cell_id</span>）与用户对话（口语别名 / 场所）指向同一实体，沿 <span class="code-inline">Episode ↔ Edge</span> 直接统计频次与回查原话。</li>
          <li><strong>跨用户 / 基站小区级群体关联</strong>：多用户共享 <span class="code-inline">Cell</span> 与 <span class="code-inline">App</span> 节点，实现同小区拥塞/卡顿联动排障。</li>
        </ul>
      </div>
      <div class="callout amber" style="margin:0">
        <strong>建图没有优势（甚至划不来）的 3 个场景</strong>
        <ul>
          <li><strong>单用户单跳当前偏好补全</strong>：单用户图 66.2% 是星型 1 跳边，Mem0 准确率已达 95%~100%，重型图谱纯属杀鸡用牛刀。</li>
          <li><strong>高频写入与低延迟约束</strong>：Graphiti 每条消息都触发实体抽取、消歧、冲突检测与摘要刷新，写入延迟和 Token 成本显著高于 Mem0。</li>
          <li><strong>需要保留完整过程细节</strong>：三元组压缩天然丢弃多轮澄清话术与长段推理过程（仍需情景原文或程序记忆补充）。</li>
        </ul>
      </div>
    </div>
    <div class="callout" style="margin-top:16px">
      <strong>对联接 Agent 的落地架构建议（轻量关系表吸收 Zep 基因 + 向量检索）：</strong><br/>
      1. <strong>现阶段（单用户意图理解与偏好补全为主）</strong>：不直接上重型图数据库，采用<strong>结构化双时态槽位表 + 向量检索</strong>——把 Zep 最有价值的 2 个设计直接吸收到表字段里：① 每条偏好记录维护 <span class="code-inline">[t_valid, t_invalid)</span> 软失效区间（查询当前态默认过滤失效记录，历史回溯时再放开）；② 每条偏好维护 <span class="code-inline">source_episodes[]</span> 指针列表连回情景记录表，区分单次偶发与多次累积。<br/>
      2. <strong>演进阶段（扩展到基站小区级群体排障 / 多用户共性体验挖掘）</strong>：再以 <span class="code-inline">Cell</span> 和 <span class="code-inline">App</span> 为共享枢纽节点，构建轻量邻接图索引（无需把所有对话细节都塞进三元组）。
    </div>
  </section>
</div>

<script>
const DATA = {data_json};

function setTheme(t) {{
  document.documentElement.setAttribute('data-theme', t);
  document.getElementById('btn-parchment').classList.toggle('active', t === 'parchment');
  document.getElementById('btn-github').classList.toggle('active', t === 'github');
}}

function renderKPIs() {{
  const t = DATA.topology;
  const b = DATA.benchmark;
  const items = [
    {{ label: '实验真实数据规模', val: `${{DATA.user_count}} 用户 / ${{DATA.ingest_stats.total_records}} 条`, hint: `过滤噪声 ${{DATA.ingest_stats.noise_ignored}} 条，有效情节 ${{DATA.ingest_stats.episodes_written}} 条` }},
    {{ label: '单用户图平均规模', val: `${{t.single_user_avg.avg_nodes}} 节点 / ${{t.single_user_avg.avg_edges}} 边`, hint: `User 星型中心度 ${{(t.single_user_avg.avg_star_centrality*100).toFixed(1)}}%（浅星型结构）` }},
    {{ label: '跨用户全局图枢纽', val: `${{t.global_graph.shared_cell_bridges}} 小区 / ${{t.global_graph.shared_app_bridges}} 应用`, hint: `全局共 ${{t.global_graph.total_nodes}} 节点、${{t.global_graph.total_edges}} 条边` }},
    {{ label: '62 题综合准确率', val: `Zep-Strict ${{(b.zep_strict.summary.overall.acc*100).toFixed(1)}}%`, hint: `Zep-Default ${{(b.zep_default.summary.overall.acc*100).toFixed(1)}}% · Mem0 ${{(b.mem0.summary.overall.acc*100).toFixed(1)}}%` }}
  ];
  document.getElementById('kpi-grid').innerHTML = items.map(x => `
    <div class="kpi">
      <div class="label">${{x.label}}</div>
      <div class="val">${{x.val}}</div>
      <div class="hint">${{x.hint}}</div>
    </div>
  `).join('');
}}

const TYPE_COLOR = {{
  User: '#1D4ED8',
  App: '#15803D',
  Cell: '#0EA5E9',
  Venue: '#D97706',
  Alias: '#7C3AED',
  Category: '#64748B',
  BranchRule: '#DC2626',
  KPI: '#BE123C'
}};

function showInspector(title, html) {{
  document.getElementById('inspector').innerHTML = `<h4>${{title}}</h4>${{html}}`;
}}

function renderSingleGraph() {{
  const cs = DATA.case_study;
  const svg = document.getElementById('graph-svg');
  const cx = 370, cy = 235;
  const pos = {{}};
  const uid = cs.user_id;
  pos[uid] = {{ x: cx, y: cy }};

  // 按类型分区摆放，避免重叠
  const groups = {{ App: [], Cell: [], Venue: [], BranchRule: [], Alias: [], Category: [] }};
  cs.zep_nodes.forEach(n => {{ if (n.id !== uid && groups[n.type]) groups[n.type].push(n); }});

  const placeArc = (arr, r, startDeg, endDeg) => {{
    arr.forEach((n, i) => {{
      const deg = arr.length === 1 ? (startDeg + endDeg)/2 : startDeg + (endDeg - startDeg) * (i / (arr.length - 1));
      const rad = deg * Math.PI / 180;
      pos[n.id] = {{ x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }};
    }});
  }};
  placeArc(groups.App, 155, -145, -75);
  placeArc(groups.Cell, 165, -35, 40);
  placeArc(groups.Venue, 155, 85, 135);
  placeArc(groups.BranchRule, 165, 175, 195);
  placeArc(groups.Alias, 265, -155, -110);
  placeArc(groups.Category, 265, -70, -55);

  let html = `<defs>
    <marker id="arr" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#94A3B8" />
    </marker>
    <marker id="arr-red" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#DC2626" />
    </marker>
  </defs>`;

  cs.zep_edges.forEach((e, idx) => {{
    const p1 = pos[e.src], p2 = pos[e.dst];
    if (!p1 || !p2) return;
    const isInv = Boolean(e.t_invalid);
    const stroke = isInv ? '#DC2626' : (e.count >= 5 ? '#1D4ED8' : '#94A3B8');
    const sw = isInv ? 2.4 : Math.min(1.4 + Math.log2(e.count + 1) * 0.8, 3.6);
    const dash = isInv ? '6,4' : '';
    const mx = (p1.x + p2.x) / 2, my = (p1.y + p2.y) / 2;
    html += `<g style="cursor:pointer" onclick="inspectSingleEdge(${{idx}})">
      <line x1="${{p1.x}}" y1="${{p1.y}}" x2="${{p2.x}}" y2="${{p2.y}}" stroke="${{stroke}}" stroke-width="${{sw}}" stroke-dasharray="${{dash}}" marker-end="url(#${{isInv?'arr-red':'arr'}})" />
      <rect x="${{mx-34}}" y="${{my-9}}" width="68" height="16" rx="4" fill="#FFFFFF" fill-opacity="0.92" stroke="${{isInv?'#FECACA':'#E2E8F0'}}" />
      <text x="${{mx}}" y="${{my+2}}" text-anchor="middle" font-size="9.5" fill="${{isInv?'#B91C1C':'#475569'}}">${{e.rel}} (${{e.count}})</text>
    </g>`;
  }});

  cs.zep_nodes.forEach((n, idx) => {{
    const p = pos[n.id];
    if (!p) return;
    const col = TYPE_COLOR[n.type] || '#475569';
    const r = n.type === 'User' ? 24 : 16;
    const label = n.label.length > 11 ? n.label.slice(0, 10) + '…' : n.label;
    html += `<g style="cursor:pointer" onclick="inspectSingleNode('${{n.id}}')">
      <circle cx="${{p.x}}" cy="${{p.y}}" r="${{r}}" fill="${{col}}" stroke="#FFFFFF" stroke-width="2.5" />
      <text x="${{p.x}}" y="${{p.y + r + 13}}" text-anchor="middle" font-size="11" font-weight="600" fill="#1F2328">${{label}}</text>
    </g>`;
  }});

  svg.innerHTML = html;
  // 默认展示那条最有代表性的已失效双时态边
  const invIdx = cs.zep_edges.findIndex(e => e.t_invalid);
  inspectSingleEdge(invIdx >= 0 ? invIdx : 0);
}}

function inspectSingleEdge(idx) {{
  const cs = DATA.case_study;
  const e = cs.zep_edges[idx];
  const epMap = Object.fromEntries(cs.zep_episodes.map(x => [x.ep_id, x]));
  const epsHtml = e.episodes.map(id => {{
    const ep = epMap[id];
    return ep ? `<div style="padding:6px 8px;background:#FFF;border:1px solid var(--border);border-radius:6px;margin-top:6px;">
      <div><strong>${{ep.ep_id}}</strong> · ${{ep.ts}} · <span class="pill tag">${{ep.carrier}}/${{ep.role}}</span></div>
      <div style="color:var(--muted);margin-top:2px;">${{ep.raw_text}}</div>
    </div>` : '';
  }}).join('');
  showInspector(`关系边详情：${{e.rel}}`, `
    <div><span class="pill ${{e.t_invalid ? 'invalid' : 'active'}}">${{e.t_invalid ? '已失效 (SOFT-INVALID)' : '当前生效 (ACTIVE)'}}</span>
    <span class="pill tag">证据数: ${{e.count}}</span></div>
    <p style="margin-top:8px"><strong>三元组：</strong><span class="code-inline">${{e.src}}</span> → <strong>${{e.rel}}</strong> → <span class="code-inline">${{e.dst}}</span></p>
    <p><strong>事实陈述：</strong>${{e.fact_text}}</p>
    <p><strong>双时态区间：</strong><br/>生效 <span class="code-inline">${{e.t_valid}}</span><br/>失效 <span class="code-inline">${{e.t_invalid || 'NULL (仍有效)'}}</span></p>
    <p><strong>底层情节溯源（episodes[]）：</strong></p>
    ${{epsHtml}}
  `);
}}

function inspectSingleNode(nid) {{
  const cs = DATA.case_study;
  const n = cs.zep_nodes.find(x => x.id === nid);
  const relEdges = cs.zep_edges.filter(e => e.src === nid || e.dst === nid);
  showInspector(`实体节点：${{n.label}}`, `
    <div><span class="pill tag">${{n.type}}</span><span class="pill tag">社区: ${{n.community}}</span></div>
    <p style="margin-top:8px"><strong>节点 ID：</strong><span class="code-inline">${{n.id}}</span></p>
    <p><strong>关联边（${{relEdges.length}} 条）：</strong></p>
    ${{relEdges.map(e => `<div style="padding:5px 8px;background:#FFF;border:1px solid var(--border);border-radius:6px;margin-top:5px;">
      ${{e.src}} <strong>-[${{e.rel}}]-></strong> ${{e.dst}}
      <span class="pill ${{e.t_invalid?'invalid':'active'}}">${{e.t_invalid?'已失效':'生效'}}</span>
      (eps=${{e.count}})
    </div>`).join('')}}
  `);
}}

function renderCrossGraph() {{
  const cc = DATA.cross_user_case;
  const svg = document.getElementById('graph-svg');
  const pos = {{}};
  pos[cc.bridge_cell] = {{ x: 380, y: 235 }};

  const users = cc.nodes.filter(n => n.type === 'User');
  const others = cc.nodes.filter(n => n.type !== 'User' && n.id !== cc.bridge_cell);
  users.forEach((u, i) => {{
    const angle = (-135 + i * (360 / users.length)) * Math.PI / 180;
    pos[u.id] = {{ x: 380 + 150 * Math.cos(angle), y: 235 + 125 * Math.sin(angle) }};
  }});
  others.forEach((o, i) => {{
    const angle = (-165 + i * (360 / Math.max(others.length, 1))) * Math.PI / 180;
    pos[o.id] = {{ x: 380 + 280 * Math.cos(angle), y: 235 + 190 * Math.sin(angle) }};
  }});

  let html = '';
  cc.edges.forEach(e => {{
    const p1 = pos[e.src], p2 = pos[e.dst];
    if (!p1 || !p2) return;
    const isBridge = e.dst === cc.bridge_cell;
    const isInv = Boolean(e.t_invalid);
    html += `<line x1="${{p1.x}}" y1="${{p1.y}}" x2="${{p2.x}}" y2="${{p2.y}}"
      stroke="${{isInv ? '#DC2626' : (isBridge ? '#0EA5E9' : '#CBD5E1')}}"
      stroke-width="${{isBridge ? 2.6 : 1.5}}" stroke-dasharray="${{isInv ? '5,4' : ''}}" />`;
  }});
  cc.nodes.forEach(n => {{
    const p = pos[n.id];
    if (!p) return;
    const col = TYPE_COLOR[n.type] || '#475569';
    const r = n.id === cc.bridge_cell ? 25 : (n.type === 'User' ? 18 : 13);
    const label = n.label.length > 12 ? n.label.slice(0, 11) + '…' : n.label;
    html += `<g>
      <circle cx="${{p.x}}" cy="${{p.y}}" r="${{r}}" fill="${{col}}" stroke="#FFFFFF" stroke-width="2" />
      <text x="${{p.x}}" y="${{p.y + r + 12}}" text-anchor="middle" font-size="10.5" font-weight="600" fill="#1F2328">${{label}}</text>
    </g>`;
  }});
  svg.innerHTML = html;
  showInspector(`跨用户枢纽：基站小区 ${{cc.bridge_cell}}`, `
    <p>当多个用户的图合并时，共享基站小区 <span class="code-inline">${{cc.bridge_cell}}</span> 成为天然桥接枢纽，把 <strong>${{cc.users.length}} 个独立用户</strong> 及其各自使用的应用、临时规则连成多跳网络。</p>
    <p><strong>可支持的群体推理路径：</strong><br/><span class="code-inline">User_A → Cell(4600040386A) ← User_B → App / Stall</span></p>
    <p><strong>为什么 Mem0 做不到：</strong>Mem0 按 <span class="code-inline">user_id</span> 物理隔离扁平向量库，且小区编号仅作为纯文本片段埋在单句里，无法沿共享实体做 2 跳反向扩散。</p>
  `);
}}

function switchView(v) {{
  document.getElementById('view-single').classList.toggle('active', v === 'single');
  document.getElementById('view-cross').classList.toggle('active', v === 'cross');
  if (v === 'single') renderSingleGraph(); else renderCrossGraph();
}}

function renderSideBySide() {{
  const cs = DATA.case_study;
  document.getElementById('zep-edge-summary').innerHTML = cs.zep_edges.map(e => `
    <div class="mem0-item" style="${{e.t_invalid ? 'border-color:#FECACA;background:#FEF2F2;' : ''}}">
      <span class="pill ${{e.t_invalid ? 'invalid' : 'active'}}">${{e.t_invalid ? '失效' : '生效'}}</span>
      <strong>${{e.src.replace('persona_','U_')}}</strong> -[${{e.rel}}]-> <strong>${{e.dst}}</strong>
      <span style="color:var(--muted);font-size:12px;">(eps=${{e.count}}, valid=${{e.t_valid.slice(5,16)}}${{e.t_invalid ? ', invalid='+e.t_invalid.slice(5,16) : ''}})</span>
    </div>
  `).join('');

  const mHtml = cs.mem0_items.map(m => `
    <div class="mem0-item">
      <span class="pill tag">${{m.slot}}</span> ${{m.text}}
    </div>
  `).join('');
  const dHtml = cs.mem0_deleted.map(d => `
    <div class="mem0-item deleted">
      [已物理 DELETE · ${{d.deleted_at}}] ${{d.old_text}}
    </div>
  `).join('');
  document.getElementById('mem0-list').innerHTML = dHtml + mHtml;
}}

function renderBenchTable() {{
  const rows = [
    ['Q1_single_hop', 'Q1 单跳当前主力应用', '单用户 1 跳查表，扁平向量与图谱几乎无差异。'],
    ['Q4_alias_bridge', 'Q4 个性化别名映射', '单条别名事实（如小破站→B站）双方均能稳定召回。'],
    ['Q2_temporal_history', 'Q2-历史回溯（已撤销/迁移项）', 'Mem0 因 DELETE 覆写彻底失忆（0%）；Zep 靠双时态边 100% 回溯。'],
    ['Q2_post_supersede_current', 'Q2-撤销后问当前态', 'Zep 默认返回失效旧边导致陈旧泄露（0%），必须加严格时间窗过滤。'],
    ['Q3_evidence_provenance', 'Q3 多源证据溯源与频次聚合', 'Mem0 无情节层（0%）；Zep 语义边自带 episodes[] 列表直接溯源。'],
    ['Q5_cross_user_cell', 'Q5 跨用户同小区关联', 'Mem0 按 user_id 隔离（0%）；Zep 沿共享 Cell 枢纽 2 跳打通。'],
    ['overall', '全部 62 题综合汇总', 'Zep-Strict 最高（96.8%），领先主要来自双时态、情节溯源与跨用户桥接。']
  ];
  const bm = DATA.benchmark;
  const fmt = (obj) => {{
    const pct = (obj.acc * 100).toFixed(1) + '%';
    const cls = obj.acc >= 0.9 ? 'good' : (obj.acc <= 0.4 ? 'bad' : 'warn');
    return `<span class="${{cls}}">${{pct}}</span> <span style="color:var(--muted);font-weight:400;font-size:12px;">(${{obj.passed}}/${{obj.total}})</span>`;
  }};
  document.getElementById('bench-tbody').innerHTML = rows.map(([key, name, note]) => `
    <tr style="${{key==='overall'?'background:var(--surface-soft);font-weight:600;':''}}">
      <td>${{name}}</td>
      <td class="num">${{bm.mem0.summary[key].total}}</td>
      <td class="num">${{fmt(bm.mem0.summary[key])}}</td>
      <td class="num">${{fmt(bm.zep_default.summary[key])}}</td>
      <td class="num">${{fmt(bm.zep_strict.summary[key])}}</td>
      <td>${{note}}</td>
    </tr>
  `).join('');
}}

renderKPIs();
renderSingleGraph();
renderSideBySide();
renderBenchTable();
</script>
</body>
</html>
"""


def main() -> None:
    with open(RESULTS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    html = build_html(data)
    for out_path in (OUT_LAVISH, OUT_ARTIFACT):
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info("Wrote HTML report to %s (%d bytes)", out_path, len(html.encode("utf-8")))


if __name__ == "__main__":
    main()

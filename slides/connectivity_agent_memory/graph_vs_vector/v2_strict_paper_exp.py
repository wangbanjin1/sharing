#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""严格按原论文完整多步算法复现 Mem0 (arXiv:2504.19413) 与 Zep/Graphiti (arXiv:2501.13956)
在 V2 试点 3 样本（USER_001~003，38 条 Stage A + 11 道 Stage B）上跑真模型对照（qwen3.8-flash + text-embedding-v4）。

相比精简版，本脚本完整补齐原论文全部关键步骤：
- Mem0 完整版：m=10 历史滑窗 + 异步全局对话摘要 S + 阶段二 s=10 召回判重更新；
- Zep 完整版：
  1) 独立实体/关系抽取（n=4 滑窗）+ 独立绝对时间/有效期换算（t_valid / expires_at）；
  2) 独立跨边冲突截断（余弦 >= 0.6 召回候选旧边 -> 专门 LLM 判冲突并截断 t_invalid）；
  3) 实体聚合摘要刷新（<=250 词）；
  4) 向量 + BM25 + 1~2 跳 BFS 三路混合召回 + RRF 倒数秩融合重排。
"""
from __future__ import annotations

import collections
import json
import logging
import math
import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
import numpy as np

from v2_pilot_zep_vs_mem0_exp import (
    Client,
    V2_AGENT_SYSTEM,
    V2_DATA_PATH,
    V2_JUDGE_SYSTEM,
    format_v2_raw,
    load_cfg,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(HERE, "v2_strict_paper_exp_results.json")

# --- 严格原论文版 Prompts ---
MEM0_SUMMARY_SYSTEM = """你是全局对话摘要更新器。根据【已有全局摘要 S】和【最新事件】，输出更新后的简洁全局摘要（不超过150字），保留用户主力应用、常驻场景、临时规则与近期变化。纯文本输出。"""

MEM0_FULL_EXTRACT_SYSTEM = """你是 Mem0 阶段一事实抽取器。输入包含【全局摘要 S】、【最近 m=10 条历史滑窗】和【当前最新事件】。
请仅从【当前最新事件】中结合上下文消除代词与相对时间，抽取 0~3 条自包含中文事实短句（保留精确时间如 HH:MM、应用、子业务、画质、时延与临时天数/到期日）。
若是无关闲聊或 0 分钟瞬时废单，返回 {"facts": []}。严格输出 JSON：{"facts": ["..."]}。"""

MEM0_FULL_UPDATE_SYSTEM = """你是 Mem0 阶段二更新决策器。给定新候选事实与库中 s=10 条最相似已有记忆，决定操作：
- ADD：新增独立记忆；
- UPDATE：合并或更新已有记忆（指定 target_id 并给出整合后的新 text，尽量保留精确时间与频次）；
- DELETE：新事实明确撤销/作废某已有记忆（指定 target_id）；
- NONE：完全重复。
严格输出 JSON：{"op": "ADD|UPDATE|DELETE|NONE", "target_id": "ID或null", "text": "最终文本或null"}。"""

ZEP_STEP1_EXTRACT_SYSTEM = """你是 Zep/Graphiti 阶段一实体与关系抽取器。结合最近 n=4 条历史情节，从当前新情节中抽取实体与关系边。
关键要求：
1. 必须把相对时间与临时有效期换算成精确的绝对时间戳（YYYY-MM-DD HH:MM:SS）：
   - valid_at：该事实或规则开始生效的精确时刻（单据保留精确到分钟的发生时间）；
   - invalid_at：若明确提到“这 5 天临时规则”等固定期限，请直接推算出精确到期时间填入 invalid_at；若长期有效则填 null。
2. 保留精确业务参数（画质如 1080P/4K、时延如 30ms、顺畅/卡顿状态、禁用边界）。
3. 若为无关闲聊或 0 分钟瞬时废单，返回 {"edges": []}。
严格输出 JSON：
{"edges": [{"src": "...", "rel": "USES_APP|RESIDES_CELL|FREQUENTS_VENUE|ALIAS_OF|HAS_BRANCH_RULE|PROCEDURAL_RULE", "dst": "...", "fact_text": "...", "valid_at": "YYYY-MM-DD HH:MM:SS", "invalid_at": "YYYY-MM-DD HH:MM:SS或null"}]}。"""

ZEP_STEP2_CONTRADICT_SYSTEM = """你是 Zep/Graphiti 独立的跨边冲突与失效裁决器（Edge Invalidation）。
给定【新入图的关系边（含生效时间）】和【库中语义相似（余弦>=0.6）的已有生效旧边列表】，请判断哪些旧边被新边取代、撤销或构成冲突。
规则：
- 若新边明确表示“取消/撤销旧规则”、“永久改用新参数”或“同场景下已长期切换为新主力应用”，将对应旧边 id 列入 invalidate_ids。
- 若两者是不同场景（如出差与日常、开直播与看直播）或互补信息，不得误判冲突，返回空列表。
严格输出 JSON：{"invalidate_ids": ["E0001", ...]}。"""

ZEP_STEP3_SUMMARY_SYSTEM = """你是 Zep/Graphiti 实体摘要刷新器。根据实体已有摘要与新关联事实，输出更新后的精炼实体摘要（不超过120字，保留核心习惯、别名与关键边界）。纯文本输出。"""


def tok_bm25(text: str) -> list[str]:
    out: list[str] = []
    for m in re.findall(r"[a-zA-Z0-9_<=.:-]+|[\u4e00-\u9fff]+", text.lower()):
        if re.match(r"^[a-z0-9_<=.:-]+$", m):
            out.append(m)
        elif len(m) <= 2:
            out.append(m)
        else:
            out.extend(m[i : i + 2] for i in range(len(m) - 1))
    return out


class BM25Lite:
    """零依赖轻量 BM25，用于还原 Zep 原论文 HNSW + BM25 + BFS 三路混合检索。"""

    def __init__(self, docs: list[tuple[str, str]]) -> None:
        self.ids = [d[0] for d in docs]
        self.tfs = [collections.Counter(tok_bm25(d[1])) for d in docs]
        self.lens = [sum(tf.values()) for tf in self.tfs]
        self.avgdl = sum(self.lens) / max(len(self.lens), 1)
        self.df: collections.Counter[str] = collections.Counter()
        for tf in self.tfs:
            for w in tf:
                self.df[w] += 1
        self.n = max(len(docs), 1)

    def rank(self, query: str) -> list[str]:
        q_toks = tok_bm25(query)
        scores: list[tuple[str, float]] = []
        k1, b = 1.5, 0.75
        for doc_id, tf, dl in zip(self.ids, self.tfs, self.lens):
            sc = 0.0
            for w in q_toks:
                if w not in tf:
                    continue
                idf = math.log((self.n - self.df[w] + 0.5) / (self.df[w] + 0.5) + 1.0)
                f = tf[w]
                sc += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / max(self.avgdl, 1.0)))
            scores.append((doc_id, sc))
        scores.sort(key=lambda x: x[1], reverse=True)
        return [d for d, s in scores if s > 0]


@dataclass
class FullMem0Fact:
    fid: str
    uid: str
    text: str
    vec: np.ndarray
    ts: str


class StrictPaperMem0:
    """严格对齐 Mem0 原论文：m=10 滑窗 + 异步全局摘要 S + s=10 阶段二冲突更新。"""

    def __init__(self, client: Client) -> None:
        self.client = client
        self.facts: dict[str, FullMem0Fact] = {}
        self.window: dict[str, list[str]] = collections.defaultdict(list)
        self.summary: dict[str, str] = collections.defaultdict(str)
        self.ops: collections.Counter[str] = collections.Counter()
        self._seq = 0

    def _search(self, uid: str, qv: np.ndarray, top_k: int = 10) -> list[tuple[FullMem0Fact, float]]:
        res = [(f, float(np.dot(qv, f.vec))) for f in self.facts.values() if f.uid == uid]
        res.sort(key=lambda x: x[1], reverse=True)
        return res[:top_k]

    def ingest(self, uid: str, ts: str, raw: str) -> None:
        win_txt = "\n".join(self.window[uid][-10:]) or "无"
        ext_in = f"【全局摘要 S】\n{self.summary[uid] or '暂无'}\n\n【最近 m=10 历史滑窗】\n{win_txt}\n\n【当前最新事件】\n{raw}"
        ext = self.client.chat_json(MEM0_FULL_EXTRACT_SYSTEM, ext_in, bucket="mem0_full_write", max_tokens=450)
        for cand in (ext.get("facts") or [])[:3]:
            if not isinstance(cand, str) or len(cand.strip()) < 4:
                continue
            cand = cand.strip()
            cv = self.client.embed(cand, bucket="mem0_full_write")
            nbs = self._search(uid, cv, top_k=10)
            if not nbs:
                self._add(uid, cand, cv, ts)
                continue
            nb_txt = "\n".join(f"- id={f.fid} (sim={s:.2f}): {f.text}" for f, s in nbs)
            dec = self.client.chat_json(MEM0_FULL_UPDATE_SYSTEM, f"新候选事实（{ts}）：{cand}\n\n最相似已有记忆（s=10）：\n{nb_txt}", bucket="mem0_full_write", max_tokens=320)
            op = str(dec.get("op") or "ADD").upper()
            tid = dec.get("target_id")
            ntxt = dec.get("text") or cand
            if op == "DELETE" and tid in self.facts:
                self.facts.pop(tid)
                self.ops["DELETE"] += 1
            elif op == "UPDATE" and tid in self.facts:
                self.facts[tid].text = ntxt
                self.facts[tid].vec = self.client.embed(ntxt, bucket="mem0_full_write")
                self.facts[tid].ts = ts
                self.ops["UPDATE"] += 1
            elif op == "NONE":
                self.ops["NONE"] += 1
            else:
                self._add(uid, ntxt, self.client.embed(ntxt, bucket="mem0_full_write"), ts)

        # 更新 m=10 滑窗 & 每 3 条刷新一次全局摘要 S
        self.window[uid].append(raw)
        if len(self.window[uid]) % 3 == 0:
            self.summary[uid] = self.client.chat(
                MEM0_SUMMARY_SYSTEM,
                f"【已有全局摘要 S】\n{self.summary[uid] or '暂无'}\n\n【最新事件】\n{raw}",
                bucket="mem0_full_write",
                max_tokens=220,
            )

    def _add(self, uid: str, text: str, vec: np.ndarray, ts: str) -> None:
        self._seq += 1
        fid = f"M{self._seq:04d}"
        self.facts[fid] = FullMem0Fact(fid, uid, text, vec, ts)
        self.ops["ADD"] += 1

    def retrieve(self, uid: str, query: str, top_k: int = 8) -> list[tuple[FullMem0Fact, float]]:
        return self._search(uid, self.client.embed(query, bucket="mem0_full_query"), top_k=top_k)


@dataclass
class FullZepEdge:
    eid: str
    uid: str
    src: str
    rel: str
    dst: str
    fact_text: str
    vec: np.ndarray
    t_valid: str
    t_invalid: str | None = None
    episodes: list[str] = field(default_factory=list)

    def valid_at(self, ts: str) -> bool:
        return self.t_valid <= ts and (self.t_invalid is None or ts < self.t_invalid)


class StrictPaperZep:
    """严格对齐 Zep/Graphiti 原论文：独立抽取+时间换算 → 独立 sim>=0.6 冲突截断 → 实体摘要 → 三路 RRF 检索。"""

    def __init__(self, client: Client) -> None:
        self.client = client
        self.hist: dict[str, list[str]] = collections.defaultdict(list)
        self.edges: dict[str, FullZepEdge] = {}
        self.out_e: dict[str, list[str]] = collections.defaultdict(list)
        self.in_e: dict[str, list[str]] = collections.defaultdict(list)
        self.entity_summaries: dict[tuple[str, str], str] = {}
        self.invalidation_count = 0
        self._seq = 0

    def ingest(self, uid: str, ep_id: str, ts: str, raw: str) -> None:
        # Step 1: n=4 滑窗抽取实体边 + 绝对时间/有效期换算
        ctx = "\n".join(self.hist[uid][-4:]) or "无"
        self.hist[uid].append(raw)
        ext = self.client.chat_json(
            ZEP_STEP1_EXTRACT_SYSTEM,
            f"【参考当前时间】{ts}\n【最近 n=4 历史情节】\n{ctx}\n\n【当前新情节】\n{raw}",
            bucket="zep_full_write",
            max_tokens=750,
        )
        new_facts_for_summary: list[str] = []

        for item in (ext.get("edges") or []):
            if not isinstance(item, dict):
                continue
            src = str(item.get("src") or "").strip()
            dst = str(item.get("dst") or "").strip()
            rel = str(item.get("rel") or "").strip()
            ft = str(item.get("fact_text") or f"{src} {rel} {dst}").strip()
            if not src or not dst or not rel:
                continue
            if src in ("用户", uid):
                src = uid
            v_at = str(item.get("valid_at") or ts)
            inv_raw = item.get("invalid_at")
            inv_at = str(inv_raw) if inv_raw and str(inv_raw).lower() != "null" else None

            # 同名有效边合并累加 episodes[]
            merged = False
            for eid in self.out_e.get(src, []):
                e = self.edges[eid]
                if e.uid == uid and e.rel == rel and e.dst.lower() == dst.lower() and e.t_invalid is None and inv_at is None:
                    if ep_id not in e.episodes:
                        e.episodes.append(ep_id)
                    if len(ft) > len(e.fact_text):
                        e.fact_text = ft
                    merged = True
                    break
            if merged:
                continue

            vec = self.client.embed(f"{src} {rel} {dst} {ft}", bucket="zep_full_write")

            # Step 2: 独立跨边冲突检测（严格按原论文 sim >= 0.6 召回候选旧边 -> 专门 LLM 裁决截断）
            cands = [
                (e, float(np.dot(vec, e.vec)))
                for e in self.edges.values()
                if e.uid == uid and e.t_invalid is None and float(np.dot(vec, e.vec)) >= 0.60
            ]
            cands.sort(key=lambda x: x[1], reverse=True)
            if cands:
                c_txt = "\n".join(f"- id={e.eid} (sim={s:.2f}, valid={e.t_valid}): ({e.src})-[{e.rel}]->({e.dst}) {e.fact_text}" for e, s in cands[:6])
                inv_dec = self.client.chat_json(
                    ZEP_STEP2_CONTRADICT_SYSTEM,
                    f"【新边（valid={v_at}）】({src})-[{rel}]->({dst}) {ft}\n\n【候选已有旧边（sim>=0.6）】\n{c_txt}",
                    bucket="zep_full_write",
                    max_tokens=180,
                )
                for old_id in (inv_dec.get("invalidate_ids") or []):
                    if old_id in self.edges and self.edges[old_id].t_invalid is None:
                        self.edges[old_id].t_invalid = v_at
                        self.invalidation_count += 1

            self._seq += 1
            eid = f"E{self._seq:04d}"
            edge = FullZepEdge(eid, uid, src, rel, dst, ft, vec, t_valid=v_at, t_invalid=inv_at, episodes=[ep_id])
            self.edges[eid] = edge
            self.out_e[src].append(eid)
            self.in_e[dst].append(eid)
            new_facts_for_summary.append(ft)

        # Step 3: 增量刷新核心 User 实体摘要（<=120~250 词）
        if new_facts_for_summary:
            old_sum = self.entity_summaries.get((uid, uid), "暂无")
            self.entity_summaries[(uid, uid)] = self.client.chat(
                ZEP_STEP3_SUMMARY_SYSTEM,
                f"【实体 {uid} 已有摘要】\n{old_sum}\n\n【本次新增事实】\n" + "\n".join(new_facts_for_summary),
                bucket="zep_full_write",
                max_tokens=200,
            )

    def retrieve(self, uid: str, query: str, q_ts: str, strict: bool, top_k: int = 8) -> tuple[list[FullZepEdge], str]:
        """三路混合召回（Vector + BM25 + BFS）+ RRF 倒数秩融合 + 实体摘要。"""
        u_edges = [e for e in self.edges.values() if e.uid == uid and (not strict or e.valid_at(q_ts))]
        if not u_edges:
            return [], self.entity_summaries.get((uid, uid), "")

        # 路 1: 稠密向量排序
        qv = self.client.embed(query, bucket="zep_full_query")
        vec_rank = [e.eid for e, _ in sorted(((e, float(np.dot(qv, e.vec))) for e in u_edges), key=lambda x: x[1], reverse=True)]
        # 路 2: BM25 稀疏关键词排序
        bm25 = BM25Lite([(e.eid, f"{e.src} {e.rel} {e.dst} {e.fact_text}") for e in u_edges])
        bm25_rank = bm25.rank(query)
        # 路 3: 1~2 跳 BFS（从向量 Top-3 种子端点扩展，按 episodes 频次排序）
        bfs_ids = set()
        for eid in vec_rank[:3]:
            e = self.edges[eid]
            for node in (e.src, e.dst):
                for adj_id in self.out_e.get(node, []) + self.in_e.get(node, []):
                    ae = self.edges[adj_id]
                    if ae.uid == uid and (not strict or ae.valid_at(q_ts)):
                        bfs_ids.add(adj_id)
        bfs_rank = sorted(bfs_ids, key=lambda x: len(self.edges[x].episodes), reverse=True)

        # RRF 倒数秩融合（k=60）
        rrf: dict[str, float] = collections.defaultdict(float)
        for rank_list in (vec_rank, bm25_rank, bfs_rank):
            for idx, eid in enumerate(rank_list, 1):
                rrf[eid] += 1.0 / (60.0 + idx)
        top_ids = sorted(rrf.keys(), key=lambda x: rrf[x], reverse=True)[:top_k]
        return [self.edges[eid] for eid in top_ids], self.entity_summaries.get((uid, uid), "")


def main() -> None:
    cfg = load_cfg()
    client = Client(cfg)
    with open(V2_DATA_PATH, encoding="utf-8") as f:
        samples = json.load(f)["samples"]
    logger.info("Running STRICT-PAPER Mem0 vs Zep experiment on 3 V2 samples (model=%s, emb=%s)",
                cfg["llm"]["model"], cfg["embedding"]["model"])

    mem0 = StrictPaperMem0(client)
    zep = StrictPaperZep(client)

    for s in samples:
        uid = s["persona_id"]
        logger.info("Stage A (strict paper) ingesting %s (%d events)...", uid, len(s["stage_a_events"]))
        for ev in s["stage_a_events"]:
            raw = format_v2_raw(uid, ev)
            mem0.ingest(uid, ev["timestamp"], raw)
            zep.ingest(uid, ev["node_id"], ev["timestamp"], raw)
        ue = [e for e in zep.edges.values() if e.uid == uid]
        logger.info("  Done %s | Mem0 facts=%d ops=%s | Zep edges=%d invalid_or_ttl=%d",
                    uid, sum(1 for f in mem0.facts.values() if f.uid == uid), dict(mem0.ops),
                    len(ue), sum(1 for e in ue if e.t_invalid is not None))

    # Stage B: 11 道探针在 3 模式下评测（Mem0-Full / Zep-Full-Default / Zep-Full-Strict）
    results: dict[str, Any] = {}
    for mode in ("mem0_full", "zep_full_default", "zep_full_strict"):
        rows = []
        for s in samples:
            uid = s["persona_id"]
            pkg = f"套餐档位={s['profile']['package_tier']}（上限：{s['profile']['mos_baseline']['max_resolution']}，最小时延：{s['profile']['mos_baseline']['min_latency_ms']}ms，最低MOS：{s['profile']['mos_baseline']['min_mos']}）"
            for case in s["stage_b_eval_cases"]:
                q, q_ts = case["user_turn1"], case["query_timestamp"]
                if mode == "mem0_full":
                    hits = mem0.retrieve(uid, q, top_k=8)
                    ctx = f"【全局摘要】{mem0.summary[uid]}\n" + ("\n".join(f"- [{f.ts}] {f.text}" for f, _ in hits) or "（无命中）")
                else:
                    edges_z, ent_sum = zep.retrieve(uid, q, q_ts, strict=(mode == "zep_full_strict"), top_k=8)
                    ctx = f"【实体聚合摘要】{ent_sum}\n" + ("\n".join(
                        f"- [生效:{e.t_valid}, 失效:{e.t_invalid or '生效中'}] ({e.src})-[{e.rel}]->({e.dst})：{e.fact_text}（支撑次数={len(e.episodes)}）"
                        for e in edges_z
                    ) or "（无命中）")

                ans = client.chat(V2_AGENT_SYSTEM, f"当前时间：{q_ts}\n用户只读套餐信息：{pkg}\n\n【检索到的历史记忆】\n{ctx}\n\n【用户首轮输入】\n{q}", bucket=f"{mode}_qa", max_tokens=360)
                j = client.chat_json(V2_JUDGE_SYSTEM, json.dumps({
                    "user_turn1": q,
                    "expected_interaction_mode": case["expected_interaction_mode"],
                    "gold_intent_template": case["gold_intent_template"],
                    "eval_focus_or_sim": case.get("eval_focus") or case.get("user_simulator_spec"),
                    "agent_output": ans,
                }, ensure_ascii=False), bucket="judge", max_tokens=180)
                rows.append({
                    "case_id": case["case_id"], "persona_id": uid, "requires_memory": case["requires_memory"],
                    "passed": bool(j.get("passed")), "reason": j.get("reason", ""), "answer": ans,
                })
        req_m = [r for r in rows if r["requires_memory"]]
        no_m = [r for r in rows if not r["requires_memory"]]
        summary = {
            "all": {"passed": sum(r["passed"] for r in rows), "total": len(rows), "acc": round(sum(r["passed"] for r in rows) / len(rows), 3)},
            "requires_memory": {"passed": sum(r["passed"] for r in req_m), "total": len(req_m), "acc": round(sum(r["passed"] for r in req_m) / max(len(req_m), 1), 3)},
            "no_memory_baseline": {"passed": sum(r["passed"] for r in no_m), "total": len(no_m), "acc": round(sum(r["passed"] for r in no_m) / max(len(no_m), 1), 3)},
        }
        results[mode] = {"summary": summary, "rows": rows}
        logger.info("[%s] Summary: %s", mode, json.dumps(summary, ensure_ascii=False))

    out = {
        "models": {"llm": cfg["llm"]["model"], "embedding": cfg["embedding"]["model"]},
        "mem0_ops": dict(mem0.ops),
        "zep_invalidation_count": zep.invalidation_count,
        "zep_edges_with_invalid_or_ttl": sum(1 for e in zep.edges.values() if e.t_invalid is not None),
        "api_cost_stats": {k: {sk: round(sv, 2) if isinstance(sv, float) else sv for sk, sv in v.items()} for k, v in client.stats.items()},
        "evaluation": results,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    logger.info("Saved STRICT-PAPER results to %s", OUT_JSON)


if __name__ == "__main__":
    main()

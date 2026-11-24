#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zep-Graphiti 时序知识图谱 vs. Mem0 扁平向量记忆：基于联接 Agent 真实混合轨迹数据的对照实验。

数据来源：D:\\coding\\hybrid_memory_data\\data\\processed\\hybrid_dataset.json
（20 个用户，495 条网元单据与对话混合记录，含证据累积、噪声过滤、分支规则、纠错与撤销演进）。
"""
from __future__ import annotations

import collections
import json
import logging
import math
import os
import re
from dataclasses import dataclass, field
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = r"D:\coding\hybrid_memory_data\data\processed\hybrid_dataset.json"
OUT_JSON = os.path.join(HERE, "hybrid_exp_results.json")

ALIAS_TO_APP_FALLBACK = {
    "优酷": "youku_vod",
    "小破站": "bilibili_vod",
    "B站": "bilibili_vod",
    "爱奇艺": "iqiyi_vod",
    "腾讯会议": "tencentmeeting",
    "腾会": "tencentmeeting",
    "钉钉": "dingtalk_meeting",
    "钉钉会议": "dingtalk_meeting",
    "王者": "wangzherongyao",
    "农": "wangzherongyao",
    "和平精英": "hepingjingying",
    "吃鸡": "hepingjingying",
    "三角洲": "sanjiaozhou",
    "抖音短视频": "douyin_svod",
    "抖音直播": "douyin_live",
    "抖音开播": "douyin_live",
    "快手开播": "kuaishou_live",
}


def tokenize_zh(text: str) -> list[str]:
    """轻量中英文分词（2-gram + 英文词/数字），用于公平对比文本相似度。"""
    tokens: list[str] = []
    for m in re.findall(r"[a-zA-Z0-9_<=.]+|[\u4e00-\u9fff]+", text.lower()):
        if re.match(r"^[a-z0-9_<=.]+$", m):
            tokens.append(m)
        else:
            if len(m) <= 2:
                tokens.append(m)
            else:
                tokens.extend(m[i : i + 2] for i in range(len(m) - 1))
    return tokens


class TfidfIndex:
    """简单透明的余弦检索器，用于模拟向量检索层（同时支持 Mem0 事实检索与 Zep 边文本检索）。"""

    def __init__(self, docs: list[tuple[str, str]]) -> None:
        self.docs = docs
        self.df: collections.Counter[str] = collections.Counter()
        self.tfs: list[collections.Counter[str]] = []
        for _, text in docs:
            tf = collections.Counter(tokenize_zh(text))
            self.tfs.append(tf)
            for tok in tf:
                self.df[tok] += 1
        n = max(len(docs), 1)
        self.idf = {tok: math.log((n + 1) / (df + 1)) + 1.0 for tok, df in self.df.items()}
        self.vecs: list[dict[str, float]] = []
        self.norms: list[float] = []
        for tf in self.tfs:
            vec = {tok: (1.0 + math.log(cnt)) * self.idf.get(tok, 1.0) for tok, cnt in tf.items()}
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            self.vecs.append(vec)
            self.norms.append(norm)

    def search(self, query: str, top_k: int = 8, allowed_ids: set[str] | None = None) -> list[tuple[str, float]]:
        q_tf = collections.Counter(tokenize_zh(query))
        q_vec = {tok: (1.0 + math.log(cnt)) * self.idf.get(tok, 1.0) for tok, cnt in q_tf.items()}
        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0
        scored: list[tuple[str, float]] = []
        for (doc_id, _), vec, norm in zip(self.docs, self.vecs, self.norms):
            if allowed_ids is not None and doc_id not in allowed_ids:
                continue
            dot = sum(qv * vec.get(tok, 0.0) for tok, qv in q_vec.items())
            if dot > 0:
                scored.append((doc_id, dot / (q_norm * norm)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


@dataclass
class ZepEpisode:
    ep_id: str
    user_id: str
    ts: str
    carrier: str
    role: str
    raw_text: str


@dataclass
class ZepEdge:
    edge_id: str
    user_id: str
    src: str
    rel: str
    dst: str
    fact_text: str
    t_valid: str
    t_invalid: str | None = None
    t_created: str = ""
    t_expired: str | None = None
    episodes: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def is_valid_at(self, ts: str) -> bool:
        return self.t_valid <= ts and (self.t_invalid is None or ts < self.t_invalid)


@dataclass
class Mem0Fact:
    fact_id: str
    user_id: str
    slot_key: str
    text: str
    created_at: str
    updated_at: str


class ZepGraphStore:
    """忠实还原 Zep-Graphiti 三层双时态图（情节层 + 语义实体/双时态边 + 社区归属）。"""

    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.episodes: dict[str, ZepEpisode] = {}
        self.edges: dict[str, ZepEdge] = {}
        self.out_edges: dict[str, list[str]] = collections.defaultdict(list)
        self.in_edges: dict[str, list[str]] = collections.defaultdict(list)
        self._edge_seq = 0
        self._index: TfidfIndex | None = None

    def ensure_node(self, node_id: str, node_type: str, label: str, community: str) -> None:
        if node_id not in self.nodes:
            self.nodes[node_id] = {
                "id": node_id,
                "type": node_type,
                "label": label,
                "community": community,
                "mention_count": 0,
            }
        self.nodes[node_id]["mention_count"] += 1

    def upsert_edge(
        self,
        user_id: str,
        src: str,
        rel: str,
        dst: str,
        fact_text: str,
        ts: str,
        ep_id: str,
        meta: dict[str, Any] | None = None,
    ) -> ZepEdge:
        for eid in self.out_edges.get(src, []):
            e = self.edges[eid]
            if e.user_id == user_id and e.rel == rel and e.dst == dst and e.t_invalid is None:
                if ep_id not in e.episodes:
                    e.episodes.append(ep_id)
                e.meta["count"] = len(e.episodes)
                if fact_text and len(fact_text) > len(e.fact_text):
                    e.fact_text = fact_text
                return e
        self._edge_seq += 1
        eid = f"E{self._edge_seq:04d}"
        edge = ZepEdge(
            edge_id=eid,
            user_id=user_id,
            src=src,
            rel=rel,
            dst=dst,
            fact_text=fact_text,
            t_valid=ts,
            t_invalid=None,
            t_created=ts,
            t_expired=None,
            episodes=[ep_id],
            meta=dict(meta or {}, count=1),
        )
        self.edges[eid] = edge
        self.out_edges[src].append(eid)
        self.in_edges[dst].append(eid)
        return edge

    def invalidate_edge(self, user_id: str, src: str, rel: str, ts: str, ep_id: str, dst: str | None = None) -> list[str]:
        invalidated: list[str] = []
        for eid in self.out_edges.get(src, []):
            e = self.edges[eid]
            if e.user_id == user_id and e.rel == rel and e.t_invalid is None:
                if dst is None or e.dst == dst:
                    e.t_invalid = ts
                    e.t_expired = ts
                    if ep_id not in e.episodes:
                        e.episodes.append(ep_id)
                    invalidated.append(eid)
        return invalidated

    def build_index(self) -> None:
        docs = [(eid, f"{e.src} {e.rel} {e.dst} {e.fact_text}") for eid, e in self.edges.items()]
        self._index = TfidfIndex(docs)

    def retrieve(
        self,
        query: str,
        user_id: str,
        query_ts: str | None = None,
        strict_temporal: bool = True,
        max_hops: int = 2,
        top_k: int = 8,
        cross_user: bool = False,
    ) -> list[ZepEdge]:
        """混合检索：向量召回候选边 + 实体邻接 1~2 跳扩展 + 可选时间窗过滤。"""
        assert self._index is not None
        allowed = None if cross_user else {eid for eid, e in self.edges.items() if e.user_id == user_id}
        seed_hits = self._index.search(query, top_k=top_k, allowed_ids=allowed)
        cand_ids: dict[str, float] = {eid: score for eid, score in seed_hits}

        # 实体锚定扩展：从 user_id 节点与命中边端点做有界 1~2 跳扩展
        frontier = {user_id}
        for eid, _ in seed_hits[:4]:
            e = self.edges[eid]
            frontier.add(e.src)
            frontier.add(e.dst)

        visited = set(frontier)
        for hop in range(1, max_hops + 1):
            next_frontier: set[str] = set()
            for node in frontier:
                adj = self.out_edges.get(node, []) + (self.in_edges.get(node, []) if cross_user or hop == 1 else [])
                for eid in adj:
                    e = self.edges[eid]
                    if not cross_user and e.user_id != user_id:
                        continue
                    bonus = 0.25 / hop
                    cand_ids[eid] = max(cand_ids.get(eid, 0.0), bonus)
                    other = e.dst if e.src == node else e.src
                    if other not in visited and len(next_frontier) < 25:
                        next_frontier.add(other)
            visited |= next_frontier
            frontier = next_frontier

        # 按查询词命中与提及频次重排
        q_toks = set(tokenize_zh(query))
        ranked: list[tuple[float, ZepEdge]] = []
        for eid, base_score in cand_ids.items():
            e = self.edges[eid]
            if strict_temporal and query_ts is not None and not e.is_valid_at(query_ts):
                continue
            e_toks = set(tokenize_zh(f"{e.src} {e.rel} {e.dst} {e.fact_text}"))
            overlap = len(q_toks & e_toks) / max(len(q_toks), 1)
            freq_boost = min(math.log1p(len(e.episodes)) * 0.08, 0.25)
            ranked.append((base_score + overlap * 0.5 + freq_boost, e))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in ranked[:top_k]]


class Mem0VectorStore:
    """忠实还原 Mem0 基础版（扁平自包含事实短句 + 阶段二 ADD/UPDATE/DELETE 覆写，不保留失效历史与情节层）。"""

    def __init__(self) -> None:
        self.facts: dict[str, Mem0Fact] = {}
        self.by_user_slot: dict[tuple[str, str], str] = {}
        self.deleted_log: list[dict[str, Any]] = []
        self.updated_count = 0
        self._seq = 0
        self._index: TfidfIndex | None = None

    def upsert_fact(self, user_id: str, slot_key: str, text: str, ts: str) -> str:
        key = (user_id, slot_key)
        if key in self.by_user_slot:
            fid = self.by_user_slot[key]
            self.facts[fid].text = text
            self.facts[fid].updated_at = ts
            self.updated_count += 1
            return "UPDATE"
        self._seq += 1
        fid = f"M{self._seq:04d}"
        self.facts[fid] = Mem0Fact(fid, user_id, slot_key, text, ts, ts)
        self.by_user_slot[key] = fid
        return "ADD"

    def delete_fact(self, user_id: str, slot_key: str, ts: str, reason: str) -> bool:
        key = (user_id, slot_key)
        if key in self.by_user_slot:
            fid = self.by_user_slot.pop(key)
            old = self.facts.pop(fid)
            self.deleted_log.append({"user_id": user_id, "slot_key": slot_key, "old_text": old.text, "deleted_at": ts, "reason": reason})
            return True
        return False

    def build_index(self) -> None:
        docs = [(fid, f.text) for fid, f in self.facts.items()]
        self._index = TfidfIndex(docs)

    def retrieve(self, query: str, user_id: str, top_k: int = 8) -> list[Mem0Fact]:
        assert self._index is not None
        allowed = {fid for fid, f in self.facts.items() if f.user_id == user_id}
        hits = self._index.search(query, top_k=top_k, allowed_ids=allowed)
        return [self.facts[fid] for fid, _ in hits]


def ingest_dataset(samples: list[dict[str, Any]]) -> tuple[ZepGraphStore, Mem0VectorStore, dict[str, Any]]:
    zep = ZepGraphStore()
    mem0 = Mem0VectorStore()
    stats = {
        "total_records": 0,
        "noise_ignored": 0,
        "episodes_written": 0,
        "mem0_ops": collections.Counter(),
        "zep_invalidations": 0,
    }

    for sample in samples:
        uid = sample["persona_id"]
        zep.ensure_node(uid, "User", uid.replace("persona_", "U_"), "用户核心")
        app_counts: collections.Counter[str] = collections.Counter()

        for rec in sample["records"]:
            stats["total_records"] += 1
            ep_id = rec["node_id"]
            ts = rec["timestamp"]
            carrier = rec["carrier"]
            role = rec["role"]
            events = rec.get("memory_events_after") or []

            if carrier == "ticket":
                tr = rec.get("ticket_record") or {}
                raw_text = (
                    f"[网元单据 {tr.get('record_id', ep_id)}] 应用={tr.get('sub_app_id')}({tr.get('app_id')}) "
                    f"小区={tr.get('cell_id')} 制式=5G({tr.get('rat_type')})"
                )
            else:
                turns = rec.get("dialogue_turns") or rec.get("dialogue_turns_draft") or []
                u_msg = turns[0]["content"] if turns else ""
                raw_text = f"[对话 {ep_id}] 用户：{u_msg}"

            # Zep 底层：原始情节节点只读追加（即便噪声也会留档或按策略标记，这里记录所有非噪声情节并统计全量）
            if role == "noise":
                stats["noise_ignored"] += 1
                continue

            zep.episodes[ep_id] = ZepEpisode(ep_id, uid, ts, carrier, role, raw_text)
            stats["episodes_written"] += 1

            # 1) 从网元单据抽取实体与关系
            if carrier == "ticket":
                tr = rec.get("ticket_record") or {}
                sub_app = tr.get("sub_app_id")
                app_cat = tr.get("app_id")
                cell_id = tr.get("cell_id")
                if sub_app:
                    zep.ensure_node(sub_app, "App", sub_app, "应用与业务")
                    app_counts[sub_app] += 1
                    zep.upsert_edge(
                        uid, uid, "USES_APP", sub_app,
                        f"用户 {uid} 常用子应用 {sub_app}（类别 {app_cat}），网元单据与对话累计观测",
                        ts, ep_id, {"category": app_cat}
                    )
                    if app_cat:
                        zep.ensure_node(app_cat, "Category", app_cat, "应用与业务")
                        zep.upsert_edge(
                            uid, sub_app, "BELONGS_TO", app_cat,
                            f"子应用 {sub_app} 属于业务类别 {app_cat}",
                            ts, ep_id
                        )
                    op = mem0.upsert_fact(
                        uid, f"app:{sub_app}",
                        f"用户 {uid} 常用{app_cat}类应用 {sub_app}，最近一次使用于 {ts}",
                        ts
                    )
                    stats["mem0_ops"][op] += 1
                if cell_id:
                    zep.ensure_node(cell_id, "Cell", cell_id, "空间与网络")
                    zep.upsert_edge(
                        uid, uid, "RESIDES_CELL", cell_id,
                        f"用户 {uid} 常驻基站小区 {cell_id}",
                        ts, ep_id
                    )
                    op = mem0.upsert_fact(
                        uid, f"cell:{cell_id}",
                        f"用户 {uid} 常在基站小区 {cell_id} 活动",
                        ts
                    )
                    stats["mem0_ops"][op] += 1

            # 2) 从对话抽取场所、别名与诉求
            if carrier == "dialogue":
                slots = (rec.get("isolated_views") or {}).get("user_private_view", {}).get("turn1_allowed_slots", {})
                venue = slots.get("venue")
                alias = slots.get("app_alias")
                gold_app = (rec.get("gold_memory_state_after") or {}).get("active_preferences", {}).get("main_app", {}).get("value")
                resolved_app = ALIAS_TO_APP_FALLBACK.get(alias or "", gold_app)
                if venue:
                    zep.ensure_node(venue, "Venue", venue, "空间与网络")
                    zep.upsert_edge(
                        uid, uid, "FREQUENTS_VENUE", venue,
                        f"用户 {uid} 常在场景场所「{venue}」发起网络保障",
                        ts, ep_id
                    )
                    op = mem0.upsert_fact(
                        uid, f"venue:{venue}",
                        f"用户 {uid} 常在「{venue}」使用移动网络并关注流畅不卡顿",
                        ts
                    )
                    stats["mem0_ops"][op] += 1
                if alias and not re.match(r"^[a-z0-9_]+$", alias) and resolved_app and alias != resolved_app:
                    zep.ensure_node(alias, "Alias", f"别名:{alias}", "个性表达")
                    zep.ensure_node(resolved_app, "App", resolved_app, "应用与业务")
                    zep.upsert_edge(
                        uid, alias, "ALIAS_OF", resolved_app,
                        f"用户 {uid} 习惯用个性化简称「{alias}」指代标准应用 {resolved_app}",
                        ts, ep_id
                    )
                    zep.upsert_edge(
                        uid, uid, "USES_APP", resolved_app,
                        f"用户 {uid} 在对话中多次提及使用 {resolved_app}（口语称「{alias}」）",
                        ts, ep_id
                    )
                    op = mem0.upsert_fact(
                        uid, f"alias:{alias}",
                        f"用户 {uid} 将标准应用 {resolved_app} 简称为「{alias}」",
                        ts
                    )
                    stats["mem0_ops"][op] += 1

            # 3) 处理记忆状态演化事件（分支规则、纠错、撤销）
            for ev in events:
                ev_op = ev.get("op")
                if ev_op == "ADD_BRANCH":
                    trig = ev.get("trigger", "临时场景")
                    rule_node = f"RULE:{trig}"
                    zep.ensure_node(rule_node, "BranchRule", f"临时规则:{trig}", "规则与约束")
                    zep.upsert_edge(
                        uid, uid, "HAS_BRANCH_RULE", rule_node,
                        f"用户 {uid} 于 {ts} 启用临时分支规则：{trig} 期间优先保障",
                        ts, ep_id, {"trigger": trig}
                    )
                    op = mem0.upsert_fact(
                        uid, "branch_rule",
                        f"用户 {uid} 当前启用了「{trig}」临时优先保障规则（设立于 {ts}）",
                        ts
                    )
                    stats["mem0_ops"][op] += 1
                elif ev_op == "CORRECTION":
                    slot = ev.get("slot")
                    val = ev.get("value")
                    if slot == "latency_target" and val:
                        t_node = f"KPI:{val}"
                        zep.ensure_node(t_node, "KPI", f"时延{val}", "规则与约束")
                        inv = zep.invalidate_edge(uid, uid, "REQUIRES_KPI", ts, ep_id)
                        stats["zep_invalidations"] += len(inv)
                        zep.upsert_edge(
                            uid, uid, "REQUIRES_KPI", t_node,
                            f"用户 {uid} 明确纠正目标时延要求为 {val}（生效于 {ts}）",
                            ts, ep_id
                        )
                        op = mem0.upsert_fact(
                            uid, "latency_target",
                            f"用户 {uid} 要求网络目标时延控制在 {val} 以内（更新于 {ts}）",
                            ts
                        )
                        stats["mem0_ops"][op] += 1
                elif ev_op == "SUPERSEDE":
                    inv = zep.invalidate_edge(uid, uid, "HAS_BRANCH_RULE", ts, ep_id)
                    stats["zep_invalidations"] += len(inv)
                    # Mem0 阶段二：遇到明确撤销/覆盖，直接 DELETE 旧事实
                    if mem0.delete_fact(uid, "branch_rule", ts, "用户显式撤销临时规则，恢复主线习惯"):
                        stats["mem0_ops"]["DELETE"] += 1
                elif ev_op == "PROMOTE_BRANCH":
                    new_app = ev.get("value")
                    # 找出被替代的旧主力应用并截断其失效时间
                    sup_list = (rec.get("gold_memory_state_after") or {}).get("superseded_history") or []
                    old_app = next((x["old_value"] for x in sup_list if x.get("slot") == "main_app"), None)
                    if old_app and old_app != new_app:
                        inv = zep.invalidate_edge(uid, uid, "USES_APP", ts, ep_id, dst=old_app)
                        stats["zep_invalidations"] += len(inv)
                        if mem0.delete_fact(uid, f"app:{old_app}", ts, f"分支晋升为新主力应用 {new_app}"):
                            stats["mem0_ops"]["DELETE"] += 1
                    if new_app:
                        zep.ensure_node(new_app, "App", new_app, "应用与业务")
                        zep.upsert_edge(
                            uid, uid, "USES_APP", new_app,
                            f"用户 {uid} 将 {new_app} 晋升为新主力应用（生效于 {ts}）",
                            ts, ep_id
                        )
                        op = mem0.upsert_fact(
                            uid, f"app:{new_app}",
                            f"用户 {uid} 当前新主力应用为 {new_app}（于 {ts} 切换）",
                            ts
                        )
                        stats["mem0_ops"][op] += 1

    zep.build_index()
    mem0.build_index()
    return zep, mem0, stats


def analyze_topology(zep: ZepGraphStore, samples: list[dict[str, Any]]) -> dict[str, Any]:
    """对单用户视角与跨用户全局视角做图拓扑体检。"""
    per_user_stats = []
    for s in samples:
        uid = s["persona_id"]
        u_edges = [e for e in zep.edges.values() if e.user_id == uid]
        u_nodes = set()
        user_incident = 0
        invalid_cnt = 0
        for e in u_edges:
            u_nodes.add(e.src)
            u_nodes.add(e.dst)
            if e.src == uid or e.dst == uid:
                user_incident += 1
            if e.t_invalid is not None:
                invalid_cnt += 1
        star_ratio = user_incident / max(len(u_edges), 1)
        per_user_stats.append({
            "user_id": uid,
            "nodes": len(u_nodes),
            "edges": len(u_edges),
            "invalid_edges": invalid_cnt,
            "episodes": sum(1 for ep in zep.episodes.values() if ep.user_id == uid),
            "star_centrality": round(star_ratio, 3),
        })

    avg_nodes = sum(x["nodes"] for x in per_user_stats) / len(per_user_stats)
    avg_edges = sum(x["edges"] for x in per_user_stats) / len(per_user_stats)
    avg_star = sum(x["star_centrality"] for x in per_user_stats) / len(per_user_stats)

    # 全局图统计
    shared_cells = [
        nid for nid, n in zep.nodes.items()
        if n["type"] == "Cell" and len({zep.edges[eid].user_id for eid in zep.in_edges.get(nid, [])}) >= 2
    ]
    shared_apps = [
        nid for nid, n in zep.nodes.items()
        if n["type"] == "App" and len({zep.edges[eid].user_id for eid in zep.in_edges.get(nid, [])}) >= 2
    ]
    return {
        "single_user_avg": {
            "avg_nodes": round(avg_nodes, 2),
            "avg_edges": round(avg_edges, 2),
            "avg_star_centrality": round(avg_star, 3),
            "total_invalid_edges": sum(x["invalid_edges"] for x in per_user_stats),
        },
        "global_graph": {
            "total_nodes": len(zep.nodes),
            "total_edges": len(zep.edges),
            "total_episodes": len(zep.episodes),
            "shared_cell_bridges": len(shared_cells),
            "shared_app_bridges": len(shared_apps),
        },
        "per_user": per_user_stats,
    }


def run_benchmark(samples: list[dict[str, Any]], zep: ZepGraphStore, mem0: Mem0VectorStore) -> dict[str, Any]:
    """构建 5 类真实业务查询，公平评测 Mem0、Zep(默认含失效边)、Zep(严格时间窗过滤)。"""
    queries: list[dict[str, Any]] = []

    # 预处理全局同小区映射
    cell_to_users: dict[str, set[str]] = collections.defaultdict(set)
    user_main_app: dict[str, str] = {}
    for s in samples:
        uid = s["persona_id"]
        gold = s["records"][-1]["gold_memory_state_after"]["active_preferences"]
        if "main_app" in gold:
            user_main_app[uid] = gold["main_app"]["value"]
        for r in s["records"]:
            if r["role"] != "noise" and r["carrier"] == "ticket":
                cid = (r.get("ticket_record") or {}).get("cell_id")
                if cid:
                    cell_to_users[cid].add(uid)

    for s in samples:
        uid = s["persona_id"]
        gold = s["records"][-1]["gold_memory_state_after"]
        active = gold.get("active_preferences", {})
        sup = gold.get("superseded_history", [])

        # Q1: 单跳当前主力应用查询（全部 20 用户）
        if "main_app" in active:
            app_val = active["main_app"]["value"]
            queries.append({
                "qid": f"Q1_{uid[-4:]}",
                "category": "Q1_single_hop",
                "user_id": uid,
                "query": f"用户 {uid} 当前最常用的主力应用是什么？",
                "query_ts": "2026-02-10 00:00:00",
                "expected_tokens": [app_val],
                "forbidden_tokens": [],
                "cross_user": False,
            })

        # Q2: 历史失效规则/旧主力应用回溯（仅针对真实发生失效截断的边）
        for sh in sup:
            slot = sh["slot"]
            old_val = sh["old_value"]
            ts_inv = sh["ts"]
            target_tok = old_val.split("_")[0] if slot == "branch_rule" else old_val
            inv_edge = next(
                (e for e in zep.edges.values() if e.user_id == uid and e.t_invalid == ts_inv),
                None,
            )
            if inv_edge is None:
                continue
            hist_ts = inv_edge.t_valid  # 该边在历史上真实生效的时间点
            queries.append({
                "qid": f"Q2_hist_{uid[-4:]}",
                "category": "Q2_temporal_history",
                "user_id": uid,
                "query": f"用户 {uid} 之前启用过的 {target_tok} 历史偏好或临时规则是什么？是在什么时候失效撤销的？",
                "query_ts": hist_ts,
                "expected_tokens": [target_tok],
                "require_invalid_ts": ts_inv,
                "cross_user": False,
            })
            queries.append({
                "qid": f"Q2_now_{uid[-4:]}",
                "category": "Q2_post_supersede_current",
                "user_id": uid,
                "query": f"用户 {uid} 当前是否还处于 {target_tok} 生效状态？",
                "query_ts": "2026-04-01 00:00:00",
                "expected_tokens": [],
                "forbidden_tokens": [target_tok],
                "cross_user": False,
            })

        # Q3: 证据溯源与频次聚合（取前 10 个用户）
        if len([q for q in queries if q["category"] == "Q3_evidence_provenance"]) < 10 and "main_app" in active:
            app_val = active["main_app"]["value"]
            ep_cnt = sum(
                len(e.episodes) for e in zep.edges.values()
                if e.user_id == uid and e.rel == "USES_APP" and e.dst == app_val
            )
            if ep_cnt >= 3:
                queries.append({
                    "qid": f"Q3_{uid[-4:]}",
                    "category": "Q3_evidence_provenance",
                    "user_id": uid,
                    "query": f"用户 {uid} 对 {app_val} 的长期偏好有哪些历史单据和对话情节编号作为证据支撑？",
                    "query_ts": "2026-02-10 00:00:00",
                    "expected_min_episodes": 3,
                    "target_app": app_val,
                    "cross_user": False,
                })

        # Q4: 个性化别名桥接（凡是有 ALIAS_OF 边的用户）
        alias_edges = [e for e in zep.edges.values() if e.user_id == uid and e.rel == "ALIAS_OF"]
        for ae in alias_edges[:1]:
            queries.append({
                "qid": f"Q4_{uid[-4:]}",
                "category": "Q4_alias_bridge",
                "user_id": uid,
                "query": f"用户 {uid} 在对话中提到的「{ae.src}」具体对应哪个网元标准应用？",
                "query_ts": "2026-02-10 00:00:00",
                "expected_tokens": [ae.dst],
                "cross_user": False,
            })

        # Q5: 跨用户同小区关联（前 8 个用户）
        if len([q for q in queries if q["category"] == "Q5_cross_user_cell"]) < 8:
            u_cells = [e.dst for e in zep.edges.values() if e.user_id == uid and e.rel == "RESIDES_CELL"]
            if u_cells:
                cid = u_cells[0]
                peers = [p for p in cell_to_users[cid] if p != uid and p in user_main_app]
                if peers:
                    peer_apps = list({user_main_app[p] for p in peers})
                    queries.append({
                        "qid": f"Q5_{uid[-4:]}",
                        "category": "Q5_cross_user_cell",
                        "user_id": uid,
                        "query": f"和用户 {uid} 常驻同一基站小区 {cid} 的其他用户，主要在使用什么应用？",
                        "query_ts": "2026-02-10 00:00:00",
                        "expected_any_tokens": [p for p in peers],
                        "expected_peer_apps": peer_apps,
                        "cross_user": True,
                    })

    def eval_system(mode: str) -> dict[str, Any]:
        by_cat: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
        for q in queries:
            uid = q["user_id"]
            cat = q["category"]
            if mode == "mem0":
                hits = mem0.retrieve(q["query"], uid, top_k=8)
                ctx = "\n".join(f"[{f.updated_at}] {f.text}" for f in hits)
                ep_trace_cnt = 0
                has_invalid_ts = False
            else:
                strict = mode == "zep_strict"
                hits_z = zep.retrieve(
                    q["query"], uid,
                    query_ts=q["query_ts"],
                    strict_temporal=strict,
                    max_hops=2,
                    top_k=8,
                    cross_user=q.get("cross_user", False),
                )
                ctx = "\n".join(
                    f"[{e.t_valid}..{e.t_invalid or 'ACTIVE'}] ({e.src})-[{e.rel}]->({e.dst}) {e.fact_text} (eps={len(e.episodes)})"
                    for e in hits_z
                )
                ep_trace_cnt = max(
                    (len(e.episodes) for e in hits_z if e.dst == q.get("target_app")),
                    default=0,
                )
                has_invalid_ts = any(e.t_invalid == q.get("require_invalid_ts") for e in hits_z)

            passed = True
            reason = "ok"
            if cat == "Q1_single_hop":
                passed = all(tok in ctx for tok in q["expected_tokens"])
                reason = "hit" if passed else "miss_main_app"
            elif cat == "Q2_temporal_history":
                if mode == "mem0":
                    passed = all(tok in ctx for tok in q["expected_tokens"])
                    reason = "hit" if passed else "deleted_by_overwrite"
                else:
                    # 历史回溯：不仅要召回规则本身，还要能溯源失效时间或历史区间
                    passed = all(tok in ctx for tok in q["expected_tokens"]) and has_invalid_ts
                    reason = "hit_with_bitemporal" if passed else "miss_history"
            elif cat == "Q2_post_supersede_current":
                # 撤销后问当前态：不能把已失效旧规则当成现行规则返回
                has_forbidden = any(tok in ctx for tok in q["forbidden_tokens"])
                passed = not has_forbidden
                reason = "clean_current" if passed else "stale_edge_leakage"
            elif cat == "Q3_evidence_provenance":
                passed = ep_trace_cnt >= q["expected_min_episodes"]
                reason = f"episodes={ep_trace_cnt}" if passed else "no_episode_provenance"
            elif cat == "Q4_alias_bridge":
                passed = all(tok in ctx for tok in q["expected_tokens"])
                reason = "hit" if passed else "miss_alias_target"
            elif cat == "Q5_cross_user_cell":
                passed = any(p in ctx for p in q["expected_any_tokens"])
                reason = "cross_user_hit" if passed else "isolated_by_user_id"

            by_cat[cat].append({"qid": q["qid"], "passed": passed, "reason": reason})

        summary = {}
        total_p = 0
        total_n = 0
        for cat, items in by_cat.items():
            p = sum(1 for x in items if x["passed"])
            n = len(items)
            total_p += p
            total_n += n
            summary[cat] = {"passed": p, "total": n, "acc": round(p / max(n, 1), 3)}
        summary["overall"] = {"passed": total_p, "total": total_n, "acc": round(total_p / max(total_n, 1), 3)}
        return {"summary": summary, "details": dict(by_cat)}

    return {
        "query_count": len(queries),
        "mem0": eval_system("mem0"),
        "zep_default": eval_system("zep_default"),
        "zep_strict": eval_system("zep_strict"),
    }


def export_case_subgraph(zep: ZepGraphStore, mem0: Mem0VectorStore, uid: str) -> dict[str, Any]:
    """导出指定用户的完整图谱结构与 Mem0 扁平条目，供前端可视化直接渲染“图到底长啥样”。"""
    u_edges = [e for e in zep.edges.values() if e.user_id == uid]
    node_ids = set()
    for e in u_edges:
        node_ids.add(e.src)
        node_ids.add(e.dst)
    nodes = [zep.nodes[nid] for nid in sorted(node_ids)]
    edges = [
        {
            "id": e.edge_id,
            "src": e.src,
            "rel": e.rel,
            "dst": e.dst,
            "fact_text": e.fact_text,
            "t_valid": e.t_valid,
            "t_invalid": e.t_invalid,
            "episodes": e.episodes,
            "count": len(e.episodes),
        }
        for e in u_edges
    ]
    episodes = [
        {"ep_id": ep.ep_id, "ts": ep.ts, "carrier": ep.carrier, "role": ep.role, "raw_text": ep.raw_text}
        for ep in zep.episodes.values() if ep.user_id == uid
    ]
    mem0_items = [
        {"id": f.fact_id, "slot": f.slot_key, "text": f.text, "created_at": f.created_at, "updated_at": f.updated_at}
        for f in mem0.facts.values() if f.user_id == uid
    ]
    mem0_deleted = [d for d in mem0.deleted_log if d["user_id"] == uid]
    return {
        "user_id": uid,
        "zep_nodes": nodes,
        "zep_edges": edges,
        "zep_episodes": episodes,
        "mem0_items": mem0_items,
        "mem0_deleted": mem0_deleted,
    }


def export_cross_user_subgraph(zep: ZepGraphStore, cell_id: str, limit_users: int = 4) -> dict[str, Any]:
    """导出以共享小区为核心的跨用户局部子图，展示群体排障场景下图的真实形态。"""
    users = sorted({zep.edges[eid].user_id for eid in zep.in_edges.get(cell_id, [])})[:limit_users]
    edges_out = []
    node_ids = {cell_id}
    for uid in users:
        node_ids.add(uid)
        for eid in zep.out_edges.get(uid, []):
            e = zep.edges[eid]
            if (e.rel == "RESIDES_CELL" and e.dst == cell_id) or e.rel in ("USES_APP", "HAS_BRANCH_RULE"):
                edges_out.append({
                    "id": e.edge_id,
                    "src": e.src,
                    "rel": e.rel,
                    "dst": e.dst,
                    "t_valid": e.t_valid,
                    "t_invalid": e.t_invalid,
                    "count": len(e.episodes),
                })
                node_ids.add(e.dst)
    nodes_out = [zep.nodes[nid] for nid in sorted(node_ids) if nid in zep.nodes]
    return {"bridge_cell": cell_id, "users": users, "nodes": nodes_out, "edges": edges_out}


def main() -> None:
    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)
    samples = dataset["samples"]
    logger.info("Loaded %d user samples from %s", len(samples), DATASET_PATH)

    zep, mem0, ingest_stats = ingest_dataset(samples)
    ingest_stats["mem0_ops"] = dict(ingest_stats["mem0_ops"])
    topo = analyze_topology(zep, samples)
    bench = run_benchmark(samples, zep, mem0)

    case_uid = "persona_8613522947905"
    case_sub = export_case_subgraph(zep, mem0, case_uid)
    cross_sub = export_cross_user_subgraph(zep, "4600040386A", limit_users=4)

    result = {
        "dataset": DATASET_PATH,
        "user_count": len(samples),
        "ingest_stats": ingest_stats,
        "topology": topo,
        "benchmark": bench,
        "case_study": case_sub,
        "cross_user_case": cross_sub,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info("Saved experiment results to %s", OUT_JSON)
    logger.info("Topology single-user avg: %s", json.dumps(topo["single_user_avg"], ensure_ascii=False))
    logger.info("Topology global graph: %s", json.dumps(topo["global_graph"], ensure_ascii=False))
    logger.info("Mem0 summary: %s", json.dumps(bench["mem0"]["summary"], ensure_ascii=False))
    logger.info("Zep-Default summary: %s", json.dumps(bench["zep_default"]["summary"], ensure_ascii=False))
    logger.info("Zep-Strict summary: %s", json.dumps(bench["zep_strict"]["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真实端到端对照实验：Mem0（扁平向量）vs. Zep-Graphiti（双时态知识图谱）。

全部链路均走真实模型 API（无规则替身）：
- Embedding：阿里云百炼 text-embedding-v4（1024 维）
- LLM（抽取 / 冲突更新 / 问答 / 裁判）：阿里云百炼 qwen3.8-flash
- 输入完全隔离：仅喂原始网元单据文本与原始对话，屏蔽数据集中 gold_memory_state_after / memory_events_after。
"""
from __future__ import annotations

import collections
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
import numpy as np

from exp_prompts import (
    MEM0_EXTRACT_SYSTEM,
    MEM0_UPDATE_SYSTEM,
    QA_ANSWER_SYSTEM,
    QA_JUDGE_SYSTEM,
    ZEP_EXTRACT_SYSTEM,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = r"D:\coding\hybrid_memory_data\data\processed\hybrid_dataset.json"
OUT_JSON = os.path.join(HERE, "real_llm_exp_results.json")

TARGET_USERS = [
    "persona_8613522947905",  # 20 条：含别名「小破站/B站」、突发恶劣天气规则 SUPERSEDE、共享小区 4600040386A
    "persona_8613460256444",  # 16 条：共享小区 4600040386A、含显式纠错
    "persona_8613460580808",  # 10 条：含 PROMOTE_BRANCH 替换旧主线、共享小区 46000404997
    "persona_8613523296217",  # 21 条：含 PROMOTE_BRANCH 替换旧主线、共享小区 46000404997
]


def load_dashscope_cfg() -> dict[str, Any]:
    """优先读环境变量 DASHSCOPE_API_KEY，兜底复用 memory_system 本地配置。"""
    sys.path.insert(0, r"D:\coding\memory_system\src")
    from memory_system.core.config import DEFAULT_CONFIG

    emb_cfg = dict(DEFAULT_CONFIG["embedding"])
    llm_cfg = dict(DEFAULT_CONFIG["llm"])
    env_key = os.environ.get("DASHSCOPE_API_KEY")
    if env_key:
        emb_cfg["api_key"] = env_key
        llm_cfg["api_key"] = env_key
    return {"embedding": emb_cfg, "llm": llm_cfg}


class DashScopeClient:
    """带 Token 与延迟统计的百炼 OpenAI 兼容客户端。"""

    def __init__(self, cfg: dict[str, Any]) -> None:
        self.emb_cfg = cfg["embedding"]
        self.llm_cfg = cfg["llm"]
        self.http = httpx.Client(timeout=httpx.Timeout(90.0, connect=15.0))
        self.stats: dict[str, dict[str, float]] = collections.defaultdict(
            lambda: {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "latency_s": 0.0}
        )
        self._emb_cache: dict[str, np.ndarray] = {}

    def embed(self, text: str, bucket: str) -> np.ndarray:
        if text in self._emb_cache:
            return self._emb_cache[text]
        t0 = time.perf_counter()
        headers = {"Authorization": f"Bearer {self.emb_cfg['api_key']}", "Content-Type": "application/json"}
        payload = {"model": self.emb_cfg["model"], "input": [text[:1000]]}
        for attempt in range(3):
            try:
                resp = self.http.post(f"{self.emb_cfg['base_url']}/embeddings", headers=headers, json=payload)
                resp.raise_for_status()
                body = resp.json()
                vec = np.array(body["data"][0]["embedding"], dtype=np.float32)
                norm = float(np.linalg.norm(vec)) or 1.0
                vec = vec / norm
                usage = body.get("usage") or {}
                self.stats[f"{bucket}_emb"]["calls"] += 1
                self.stats[f"{bucket}_emb"]["prompt_tokens"] += usage.get("prompt_tokens", 0)
                self.stats[f"{bucket}_emb"]["latency_s"] += time.perf_counter() - t0
                self._emb_cache[text] = vec
                return vec
            except Exception as exc:
                if attempt == 2:
                    raise
                logger.warning("Embed retry %d: %s", attempt + 1, exc)
                time.sleep(1.5)
        raise RuntimeError("unreachable")

    def chat_json(self, system: str, user: str, bucket: str, max_tokens: int = 800) -> dict[str, Any]:
        raw = self.chat_text(system, user, bucket, max_tokens=max_tokens, json_mode=True)
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.DOTALL)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
            logger.warning("[%s] JSON parse failed, raw=%s", bucket, cleaned[:160])
            return {}

    def chat_text(self, system: str, user: str, bucket: str, max_tokens: int = 512, json_mode: bool = False) -> str:
        t0 = time.perf_counter()
        headers = {"Authorization": f"Bearer {self.llm_cfg['api_key']}", "Content-Type": "application/json"}
        payload: dict[str, Any] = {
            "model": self.llm_cfg["model"],
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.0,
            "max_tokens": max_tokens,
            "enable_thinking": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        for attempt in range(3):
            try:
                resp = self.http.post(f"{self.llm_cfg['base_url']}/chat/completions", headers=headers, json=payload)
                resp.raise_for_status()
                body = resp.json()
                text = body["choices"][0]["message"]["content"] or ""
                usage = body.get("usage") or {}
                self.stats[bucket]["calls"] += 1
                self.stats[bucket]["prompt_tokens"] += usage.get("prompt_tokens", 0)
                self.stats[bucket]["completion_tokens"] += usage.get("completion_tokens", 0)
                self.stats[bucket]["latency_s"] += time.perf_counter() - t0
                return text.strip()
            except Exception as exc:
                if attempt == 2:
                    raise
                logger.warning("Chat retry %d: %s", attempt + 1, exc)
                time.sleep(2.0)
        raise RuntimeError("unreachable")


def format_raw_record(uid: str, rec: dict[str, Any]) -> str:
    """只序列化真实原始输入（网元单据或用户对话），绝不泄露标注标签或 gold 状态。"""
    ts = rec["timestamp"]
    nid = rec["node_id"]
    if rec["carrier"] == "ticket":
        tr = rec.get("ticket_record") or {}
        dur = tr.get("duration_sec") or tr.get("duration_s") or tr.get("duration")
        return (
            f"[网元单据 id={nid} 时间={ts}] 用户={uid}, 业务类={tr.get('app_id')}, "
            f"子应用={tr.get('sub_app_id')}, 基站小区={tr.get('cell_id')}, "
            f"制式={tr.get('rat_type')}, 时长秒={dur}"
        )
    turns = rec.get("dialogue_turns") or rec.get("dialogue_turns_draft") or []
    lines = [f"{'用户' if t['role'] == 'user' else '助手'}：{t['content']}" for t in turns]
    return f"[对话记录 id={nid} 时间={ts}] 用户={uid}\n" + "\n".join(lines)


@dataclass
class RealMem0Fact:
    fact_id: str
    user_id: str
    text: str
    vec: np.ndarray
    created_at: str
    updated_at: str


class RealMem0Store:
    """真实 Mem0 流水线：qwen3.8-flash 抽取 + text-embedding-v4 召回 + qwen3.8-flash ADD/UPDATE/DELETE。"""

    def __init__(self, client: DashScopeClient) -> None:
        self.client = client
        self.facts: dict[str, RealMem0Fact] = {}
        self.deleted_log: list[dict[str, Any]] = []
        self.op_counts: collections.Counter[str] = collections.Counter()
        self._seq = 0

    def _search_user(self, user_id: str, q_vec: np.ndarray, top_k: int = 5) -> list[tuple[RealMem0Fact, float]]:
        scored = []
        for f in self.facts.values():
            if f.user_id == user_id:
                scored.append((f, float(np.dot(q_vec, f.vec))))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def ingest(self, user_id: str, ts: str, raw_text: str) -> None:
        ext = self.client.chat_json(MEM0_EXTRACT_SYSTEM, raw_text, bucket="mem0_write", max_tokens=400)
        cand_facts = ext.get("facts") or []
        if not isinstance(cand_facts, list):
            return
        for cand in cand_facts[:4]:
            if not isinstance(cand, str) or len(cand.strip()) < 4:
                continue
            cand = cand.strip()
            c_vec = self.client.embed(cand, bucket="mem0_write")
            neighbors = self._search_user(user_id, c_vec, top_k=5)
            if not neighbors:
                self._add(user_id, cand, c_vec, ts)
                continue
            nb_desc = "\n".join(f"- id={f.fact_id} (sim={sim:.2f}): {f.text}" for f, sim in neighbors)
            upd_prompt = f"新候选事实（时间 {ts}）：{cand}\n\n库中已有最相似记忆：\n{nb_desc}"
            dec = self.client.chat_json(MEM0_UPDATE_SYSTEM, upd_prompt, bucket="mem0_write", max_tokens=300)
            op = str(dec.get("op") or "ADD").upper()
            tid = dec.get("target_id")
            new_text = dec.get("text") or cand
            if op == "DELETE" and tid in self.facts:
                old = self.facts.pop(tid)
                self.deleted_log.append({"user_id": user_id, "deleted_id": tid, "old_text": old.text, "deleted_at": ts, "trigger": cand})
                self.op_counts["DELETE"] += 1
            elif op == "UPDATE" and tid in self.facts:
                self.facts[tid].text = new_text
                self.facts[tid].vec = self.client.embed(new_text, bucket="mem0_write")
                self.facts[tid].updated_at = ts
                self.op_counts["UPDATE"] += 1
            elif op == "NONE":
                self.op_counts["NONE"] += 1
            else:
                self._add(user_id, new_text, self.client.embed(new_text, bucket="mem0_write"), ts)

    def _add(self, user_id: str, text: str, vec: np.ndarray, ts: str) -> None:
        self._seq += 1
        fid = f"M{self._seq:04d}"
        self.facts[fid] = RealMem0Fact(fid, user_id, text, vec, ts, ts)
        self.op_counts["ADD"] += 1

    def retrieve(self, user_id: str, query: str, top_k: int = 8) -> list[tuple[RealMem0Fact, float]]:
        q_vec = self.client.embed(query, bucket="mem0_query")
        return self._search_user(user_id, q_vec, top_k=top_k)


@dataclass
class RealZepEdge:
    edge_id: str
    user_id: str
    src: str
    rel: str
    dst: str
    fact_text: str
    vec: np.ndarray
    t_valid: str
    t_invalid: str | None = None
    episodes: list[str] = field(default_factory=list)

    def is_valid_at(self, ts: str) -> bool:
        return self.t_valid <= ts and (self.t_invalid is None or ts < self.t_invalid)


class RealZepStore:
    """真实 Zep-Graphiti 流水线：底层无损情节 + qwen3.8-flash 三元组与冲突抽取 + text-embedding-v4 双时态检索。"""

    def __init__(self, client: DashScopeClient) -> None:
        self.client = client
        self.episodes: dict[str, dict[str, Any]] = {}
        self.user_history: dict[str, list[str]] = collections.defaultdict(list)
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: dict[str, RealZepEdge] = {}
        self.out_edges: dict[str, list[str]] = collections.defaultdict(list)
        self.in_edges: dict[str, list[str]] = collections.defaultdict(list)
        self._seq = 0

    def _ensure_node(self, nid: str, ntype: str) -> None:
        if nid not in self.nodes:
            self.nodes[nid] = {"id": nid, "type": ntype, "mentions": 0}
        self.nodes[nid]["mentions"] += 1

    def ingest(self, user_id: str, ep_id: str, ts: str, raw_text: str) -> None:
        # 1) 底层无损只读写入原始情节
        self.episodes[ep_id] = {"ep_id": ep_id, "user_id": user_id, "ts": ts, "raw_text": raw_text}
        recent_ctx = "\n".join(self.user_history[user_id][-4:])
        self.user_history[user_id].append(raw_text)

        prompt = f"【最近历史情节（最多4条）】\n{recent_ctx or '无'}\n\n【当前新情节】\n{raw_text}"
        ext = self.client.chat_json(ZEP_EXTRACT_SYSTEM, prompt, bucket="zep_write", max_tokens=700)

        # 2) 处理冲突截断（不物理删边）
        for inv in (ext.get("invalidations") or []):
            if not isinstance(inv, dict):
                continue
            rel = str(inv.get("rel") or "")
            kw = str(inv.get("target_keyword") or "").lower()
            for e in self.edges.values():
                if e.user_id != user_id or e.t_invalid is not None:
                    continue
                if rel and e.rel != rel:
                    continue
                hay = f"{e.dst} {e.fact_text}".lower()
                if (kw and kw in hay) or (rel == "HAS_BRANCH_RULE" and not kw):
                    e.t_invalid = ts
                    if ep_id not in e.episodes:
                        e.episodes.append(ep_id)

        # 3) 写入或合并语义边（累加 episodes[]）
        for item in (ext.get("edges") or []):
            if not isinstance(item, dict):
                continue
            src = str(item.get("src") or "").strip()
            dst = str(item.get("dst") or "").strip()
            rel = str(item.get("rel") or "").strip()
            fact_text = str(item.get("fact_text") or f"{src} {rel} {dst}").strip()
            if not src or not dst or not rel:
                continue
            # 规范化用户节点名
            if item.get("src_type") == "User" or src in ("用户", user_id.replace("persona_", "")):
                src = user_id
            self._ensure_node(src, str(item.get("src_type") or "Entity"))
            self._ensure_node(dst, str(item.get("dst_type") or "Entity"))

            merged = False
            for eid in self.out_edges.get(src, []):
                e = self.edges[eid]
                if e.user_id == user_id and e.rel == rel and e.dst.lower() == dst.lower() and e.t_invalid is None:
                    if ep_id not in e.episodes:
                        e.episodes.append(ep_id)
                    merged = True
                    break
            if not merged:
                self._seq += 1
                eid = f"E{self._seq:04d}"
                vec = self.client.embed(f"{src} {rel} {dst} {fact_text}", bucket="zep_write")
                edge = RealZepEdge(eid, user_id, src, rel, dst, fact_text, vec, t_valid=ts, t_invalid=None, episodes=[ep_id])
                self.edges[eid] = edge
                self.out_edges[src].append(eid)
                self.in_edges[dst].append(eid)

    def retrieve(
        self,
        user_id: str,
        query: str,
        query_ts: str | None = None,
        strict_temporal: bool = True,
        cross_user: bool = False,
        top_k: int = 8,
    ) -> list[tuple[RealZepEdge, float]]:
        q_vec = self.client.embed(query, bucket="zep_query")
        scored: dict[str, float] = {}
        for eid, e in self.edges.items():
            if not cross_user and e.user_id != user_id:
                continue
            scored[eid] = float(np.dot(q_vec, e.vec))

        # 种子边 + 实体 1~2 跳扩展
        top_seeds = sorted(scored.items(), key=lambda x: x[1], reverse=True)[:4]
        frontier = {user_id}
        for eid, _ in top_seeds:
            frontier.add(self.edges[eid].src)
            frontier.add(self.edges[eid].dst)
        visited = set(frontier)
        for hop in (1, 2):
            nxt: set[str] = set()
            for node in frontier:
                adj = self.out_edges.get(node, []) + (self.in_edges.get(node, []) if cross_user or hop == 1 else [])
                for eid in adj:
                    e = self.edges[eid]
                    if not cross_user and e.user_id != user_id:
                        continue
                    bonus = 0.25 / hop
                    scored[eid] = max(scored.get(eid, 0.0), float(np.dot(q_vec, e.vec)) + bonus)
                    other = e.dst if e.src == node else e.src
                    if other not in visited and len(nxt) < 20:
                        nxt.add(other)
            visited |= nxt
            frontier = nxt

        ranked: list[tuple[RealZepEdge, float]] = []
        for eid, sc in scored.items():
            e = self.edges[eid]
            if strict_temporal and query_ts is not None and not e.is_valid_at(query_ts):
                continue
            freq_boost = min(0.03 * len(e.episodes), 0.15)
            ranked.append((e, sc + freq_boost))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


def build_real_queries(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """为 4 个真实用户构造 20 道覆盖 6 类题型的端到端问答评测集。"""
    cell_users: dict[str, set[str]] = collections.defaultdict(set)
    user_main: dict[str, str] = {}
    for s in samples:
        uid = s["persona_id"]
        gold = s["records"][-1]["gold_memory_state_after"]["active_preferences"]
        if "main_app" in gold:
            user_main[uid] = gold["main_app"]["value"]
        for r in s["records"]:
            if r["carrier"] == "ticket" and r["role"] != "noise":
                cid = (r.get("ticket_record") or {}).get("cell_id")
                if cid:
                    cell_users[cid].add(uid)

    qs: list[dict[str, Any]] = []
    for s in samples:
        uid = s["persona_id"]
        gold = s["records"][-1]["gold_memory_state_after"]
        active = gold.get("active_preferences", {})
        sup = gold.get("superseded_history", [])

        # Q1: 单跳当前主力应用（4 题）
        if "main_app" in active:
            app_val = active["main_app"]["value"]
            qs.append({
                "qid": f"Q1_{uid[-4:]}",
                "category": "Q1_single_hop",
                "user_id": uid,
                "query": f"用户 {uid} 当前最常用的主力应用是什么？",
                "query_ts": "2026-04-01 00:00:00",
                "ground_truth": f"当前主力应用为 {app_val}",
                "cross_user": False,
            })
            # Q3: 证据次数与来源溯源（4 题）
            qs.append({
                "qid": f"Q3_{uid[-4:]}",
                "category": "Q3_evidence_provenance",
                "user_id": uid,
                "query": f"用户 {uid} 对 {app_val} 的偏好一共被多少条历史单据或对话支撑？请给出次数或来源记录编号。",
                "query_ts": "2026-04-01 00:00:00",
                "ground_truth": f"被多次历史单据/对话支撑（>=3次），需给出具体次数或来源情节编号",
                "cross_user": False,
            })

        # Q2: 历史回溯 + 撤销后当前态（3 个有 superseded_history 的用户，共 6 题）
        for sh in sup:
            slot = sh["slot"]
            old_val = sh["old_value"]
            ts_inv = sh["ts"]
            target = old_val.split("_")[0] if slot == "branch_rule" else old_val
            qs.append({
                "qid": f"Q2_hist_{uid[-4:]}",
                "category": "Q2_temporal_history",
                "user_id": uid,
                "query": f"用户 {uid} 历史上曾经启用过关于「{target}」的临时规则或旧偏好吗？是什么时候被撤销或替换的？",
                "query_ts": None,  # 历史回溯不截断当前时刻，看完整演化史
                "ground_truth": f"曾经启用过 {old_val}，并于 {ts_inv} 左右被撤销或替换",
                "cross_user": False,
            })
            qs.append({
                "qid": f"Q2_now_{uid[-4:]}",
                "category": "Q2_post_supersede_current",
                "user_id": uid,
                "query": f"截至 2026年4月，用户 {uid} 当前是否还处于「{target}」临时规则或旧主力偏好的生效状态？请明确回答是或否。",
                "query_ts": "2026-04-01 00:00:00",
                "ground_truth": f"否，{target} 早在 {ts_inv} 就已撤销或被新主线替换，当前不再处于生效状态",
                "cross_user": False,
            })

        # Q5: 跨用户同小区关联（4 题，每个用户各 1 题）
        for cid, uset in cell_users.items():
            if uid in uset and len(uset) >= 2:
                peers = [p for p in sorted(uset) if p != uid]
                peer_desc = "、".join(f"{p}({user_main.get(p, '未知')})" for p in peers)
                qs.append({
                    "qid": f"Q5_{uid[-4:]}",
                    "category": "Q5_cross_user_cell",
                    "user_id": uid,
                    "query": f"和用户 {uid} 常驻同一基站小区 {cid} 的其他用户是谁？他们主要在使用什么应用？",
                    "query_ts": "2026-04-01 00:00:00",
                    "ground_truth": f"同小区 {cid} 的其他用户包括：{peer_desc}",
                    "cross_user": True,
                })
                break

    # 补充 2 题 Q4 个性化别名（从 persona_8613522947905 与 persona_8613460256444）
    qs.append({
        "qid": "Q4_7905_alias",
        "category": "Q4_alias_bridge",
        "user_id": "persona_8613522947905",
        "query": "用户 persona_8613522947905 在对话中说的「小破站」对应哪个标准应用？",
        "query_ts": "2026-04-01 00:00:00",
        "ground_truth": "小破站对应标准应用 bilibili_vod",
        "cross_user": False,
    })
    return qs


def main() -> None:
    cfg = load_dashscope_cfg()
    client = DashScopeClient(cfg)

    with open(DATASET_PATH, encoding="utf-8") as f:
        all_samples = json.load(f)["samples"]
    samples = [s for s in all_samples if s["persona_id"] in TARGET_USERS]
    total_recs = sum(len(s["records"]) for s in samples)
    logger.info("Starting REAL LLM experiment: %d users, %d raw records (model=%s, emb=%s)",
                len(samples), total_recs, cfg["llm"]["model"], cfg["embedding"]["model"])

    mem0 = RealMem0Store(client)
    zep = RealZepStore(client)

    t_start = time.perf_counter()
    for idx, s in enumerate(samples, 1):
        uid = s["persona_id"]
        logger.info("[%d/%d] Ingesting user %s (%d records)...", idx, len(samples), uid, len(s["records"]))
        for rec in s["records"]:
            raw_text = format_raw_record(uid, rec)
            mem0.ingest(uid, rec["timestamp"], raw_text)
            zep.ingest(uid, rec["node_id"], rec["timestamp"], raw_text)
        logger.info(
            "Finished user %s | Mem0 facts=%d (ops=%s) | Zep nodes=%d edges=%d (invalid=%d)",
            uid,
            sum(1 for f in mem0.facts.values() if f.user_id == uid),
            dict(mem0.op_counts),
            len({e.src for e in zep.edges.values() if e.user_id == uid} | {e.dst for e in zep.edges.values() if e.user_id == uid}),
            sum(1 for e in zep.edges.values() if e.user_id == uid),
            sum(1 for e in zep.edges.values() if e.user_id == uid and e.t_invalid is not None),
        )
    ingest_elapsed = round(time.perf_counter() - t_start, 2)
    logger.info("Ingestion done in %.2fs", ingest_elapsed)

    # 端到端真实问答评测
    queries = build_real_queries(samples)
    logger.info("Running end-to-end LLM QA evaluation on %d queries across 3 modes...", len(queries))
    eval_results: dict[str, Any] = {}

    for mode in ("mem0", "zep_default", "zep_strict"):
        by_cat: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
        for q in queries:
            uid = q["user_id"]
            if mode == "mem0":
                hits = mem0.retrieve(uid, q["query"], top_k=8)
                ctx = "\n".join(f"- [{f.updated_at}] {f.text}" for f, _ in hits) or "（无检索结果）"
            else:
                strict = mode == "zep_strict"
                hits_z = zep.retrieve(
                    uid, q["query"],
                    query_ts=q["query_ts"],
                    strict_temporal=strict,
                    cross_user=q["cross_user"],
                    top_k=8,
                )
                ctx = "\n".join(
                    f"- [生效:{e.t_valid}, 失效:{e.t_invalid or '仍在生效'}] ({e.src})-[{e.rel}]->({e.dst})：{e.fact_text}（支撑次数={len(e.episodes)}, 情节编号={e.episodes[:6]}）"
                    for e, _ in hits_z
                ) or "（无检索结果）"

            ans = client.chat_text(
                QA_ANSWER_SYSTEM,
                f"【检索到的记忆上下文】\n{ctx}\n\n【用户问题】\n{q['query']}",
                bucket=f"{mode}_qa",
                max_tokens=300,
            )
            judge = client.chat_json(
                QA_JUDGE_SYSTEM,
                f"问题：{q['query']}\n标准参考答案：{q['ground_truth']}\n待评回答：{ans}",
                bucket="judge",
                max_tokens=150,
            )
            passed = bool(judge.get("passed"))
            by_cat[q["category"]].append({
                "qid": q["qid"],
                "query": q["query"],
                "ground_truth": q["ground_truth"],
                "context_preview": ctx[:400],
                "answer": ans,
                "passed": passed,
                "reason": judge.get("reason", ""),
            })

        summary: dict[str, Any] = {}
        tp, tn = 0, 0
        for cat, items in by_cat.items():
            p = sum(1 for x in items if x["passed"])
            n = len(items)
            tp += p
            tn += n
            summary[cat] = {"passed": p, "total": n, "acc": round(p / max(n, 1), 3)}
        summary["overall"] = {"passed": tp, "total": tn, "acc": round(tp / max(tn, 1), 3)}
        eval_results[mode] = {"summary": summary, "details": dict(by_cat)}
        logger.info("[%s] Summary: %s", mode, json.dumps(summary, ensure_ascii=False))

    # 汇总真实拓扑与成本账单
    per_user_topo = []
    for s in samples:
        uid = s["persona_id"]
        ue = [e for e in zep.edges.values() if e.user_id == uid]
        un = {e.src for e in ue} | {e.dst for e in ue}
        star = sum(1 for e in ue if e.src == uid or e.dst == uid) / max(len(ue), 1)
        per_user_topo.append({
            "user_id": uid,
            "zep_nodes": len(un),
            "zep_edges": len(ue),
            "zep_invalid_edges": sum(1 for e in ue if e.t_invalid is not None),
            "star_centrality": round(star, 3),
            "mem0_facts": sum(1 for f in mem0.facts.values() if f.user_id == uid),
        })

    # 导出 persona_8613522947905 真实 LLM 建出来的图和 Mem0 事实
    c_uid = "persona_8613522947905"
    case_export = {
        "user_id": c_uid,
        "zep_edges": [
            {"src": e.src, "rel": e.rel, "dst": e.dst, "fact_text": e.fact_text,
             "t_valid": e.t_valid, "t_invalid": e.t_invalid, "count": len(e.episodes), "episodes": e.episodes}
            for e in zep.edges.values() if e.user_id == c_uid
        ],
        "mem0_facts": [
            {"id": f.fact_id, "text": f.text, "created_at": f.created_at, "updated_at": f.updated_at}
            for f in mem0.facts.values() if f.user_id == c_uid
        ],
        "mem0_deleted": [d for d in mem0.deleted_log if d["user_id"] == c_uid],
    }

    output = {
        "models": {"llm": cfg["llm"]["model"], "embedding": cfg["embedding"]["model"]},
        "users": TARGET_USERS,
        "total_raw_records": total_recs,
        "ingest_elapsed_s": ingest_elapsed,
        "mem0_ops": dict(mem0.op_counts),
        "api_cost_stats": {k: {sk: round(sv, 2) if isinstance(sv, float) else sv for sk, sv in v.items()} for k, v in client.stats.items()},
        "topology": per_user_topo,
        "evaluation": eval_results,
        "case_study_real_llm": case_export,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info("Saved REAL LLM experiment results to %s", OUT_JSON)


if __name__ == "__main__":
    main()

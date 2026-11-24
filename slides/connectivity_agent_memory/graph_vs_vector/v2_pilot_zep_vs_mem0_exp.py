#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在全新 V2（对齐表 1~表 5、零载体 Bug）3 样本上重跑真实端到端对比实验：
No-Mem vs. Mem0（扁平向量）vs. Zep-Default vs. Zep-Strict。

全部模型真实调用：deepseek-v4.1-flash（百炼兼容） + text-embedding-v4（1024 维）。
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

from exp_prompts import MEM0_EXTRACT_SYSTEM, MEM0_UPDATE_SYSTEM, ZEP_EXTRACT_SYSTEM

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

HERE = os.path.dirname(os.path.abspath(__file__))
V2_DATA_PATH = r"D:\coding\hybrid_memory_data\data\processed\v2_pilot_3samples.json"
OUT_JSON = os.path.join(HERE, "v2_pilot_exp_results.json")

V2_AGENT_SYSTEM = """你是联接 Agent 意图理解助手。请根据当前时间、用户套餐只读信息（若需要）以及检索到的历史记忆，对用户首轮输入做出决策。
规则：
1. 若信息完整（或可通过唯一稳定的历史记忆/私有简称直接补全），直接输出最终保障方案（动作=DIRECT_TEMPLATE），写明应用、子业务、起止时间、画质与时延要求。
2. 若缺失关键槽位且记忆中无记录（或同应用存在多个易混子业务如抖音开播与观看），必须发起精准追问（动作=CLARIFY），禁止盲猜。
3. 若用户需求超出其当前套餐档位能力，需说明套餐上限并给出档内可行平替协商（动作=NEGOTIATE）。
4. 若为日常闲聊/半闲聊/域外诉求，礼貌说明边界并简洁引导或收口（动作=REJECT_OR_CLOSE），不得输出保障模板。
5. 若用户当前明确指定了合法参数，绝不可用历史长期习惯反向篡改。
请用简洁中文作答，第一行先写【动作：DIRECT_TEMPLATE|CLARIFY|NEGOTIATE|REJECT_OR_CLOSE】，下一行给出具体回复或结构化保障方案。"""

V2_JUDGE_SYSTEM = """你是严格客观的评测裁判。给定测试探针的用户输入、期望交互模式、标准答案/评测要点，以及待评测 Agent 的实际输出，请判断是否通过。
核心红线：
1. 需澄清题（I2.1/I2.2）：若 Agent 未澄清直接盲猜出模板，判 False；若精准追问缺失项/歧义项（不重问已知项），判 True。
2. 单轮直通题（I1.1/I1.2/I1.3）：必须直接输出完整准确的保障方案，且应用、子业务、时间（含平移计算）、画质/时延全部与标准答案一致；若多余追问或参数被历史习惯篡改或未回退过期临时规则，判 False。
3. 套餐协商题（I2.6）：必须指出标准档上限并给出档内平替（1080P/40ms），不可盲目承诺 4K/15ms。
4. 半闲聊收口题（I2.11）：不可输出保障模板，须简短共情并闭合引导。
严格输出 JSON：{"passed": true/false, "reason": "不超过35字的客观归因"}。"""


def load_cfg() -> dict[str, Any]:
    sys.path.insert(0, r"D:\coding\memory_system\src")
    from memory_system.core.config import DEFAULT_CONFIG

    emb_cfg = dict(DEFAULT_CONFIG["embedding"])
    llm_cfg = dict(DEFAULT_CONFIG["llm"])
    llm_cfg["model"] = "qwen3.8-flash"
    env_key = os.environ.get("DASHSCOPE_API_KEY")
    if env_key:
        emb_cfg["api_key"] = env_key
        llm_cfg["api_key"] = env_key
    return {"embedding": emb_cfg, "llm": llm_cfg}


class Client:
    def __init__(self, cfg: dict[str, Any]) -> None:
        self.emb_cfg = cfg["embedding"]
        self.llm_cfg = cfg["llm"]
        self.http = httpx.Client(timeout=httpx.Timeout(90.0, connect=15.0))
        self.stats: dict[str, dict[str, float]] = collections.defaultdict(
            lambda: {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "latency_s": 0.0}
        )
        self._cache: dict[str, np.ndarray] = {}

    def embed(self, text: str, bucket: str) -> np.ndarray:
        if text in self._cache:
            return self._cache[text]
        t0 = time.perf_counter()
        headers = {"Authorization": f"Bearer {self.emb_cfg['api_key']}", "Content-Type": "application/json"}
        for attempt in range(3):
            try:
                r = self.http.post(
                    f"{self.emb_cfg['base_url']}/embeddings",
                    headers=headers,
                    json={"model": self.emb_cfg["model"], "input": [text[:1000]]},
                )
                r.raise_for_status()
                body = r.json()
                v = np.array(body["data"][0]["embedding"], dtype=np.float32)
                v = v / (float(np.linalg.norm(v)) or 1.0)
                u = body.get("usage") or {}
                self.stats[f"{bucket}_emb"]["calls"] += 1
                self.stats[f"{bucket}_emb"]["prompt_tokens"] += u.get("prompt_tokens", 0)
                self.stats[f"{bucket}_emb"]["latency_s"] += time.perf_counter() - t0
                self._cache[text] = v
                return v
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(1.5)
        raise RuntimeError("unreachable")

    def chat(self, system: str, user: str, bucket: str, json_mode: bool = False, max_tokens: int = 600) -> str:
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
                r = self.http.post(f"{self.llm_cfg['base_url']}/chat/completions", headers=headers, json=payload)
                r.raise_for_status()
                body = r.json()
                txt = (body["choices"][0]["message"]["content"] or "").strip()
                u = body.get("usage") or {}
                self.stats[bucket]["calls"] += 1
                self.stats[bucket]["prompt_tokens"] += u.get("prompt_tokens", 0)
                self.stats[bucket]["completion_tokens"] += u.get("completion_tokens", 0)
                self.stats[bucket]["latency_s"] += time.perf_counter() - t0
                return txt
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2.0)
        raise RuntimeError("unreachable")

    def chat_json(self, system: str, user: str, bucket: str, max_tokens: int = 700) -> dict[str, Any]:
        raw = self.chat(system, user, bucket, json_mode=True, max_tokens=max_tokens)
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.DOTALL)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
            return {}


def format_v2_raw(uid: str, ev: dict[str, Any]) -> str:
    """只序列化 V2 原始单据或原始对话（严格遵守 U6.2 位置物理隔离，绝不泄露标注字段）。"""
    ts, nid = ev["timestamp"], ev["node_id"]
    if ev["carrier"] == "ticket":
        tp = ev["ticket_payload"]
        return (
            f"[网元单据 id={nid} 时间={ts}] 用户={uid}, 应用={tp['app_id']}, 子业务={tp['sub_service']}, "
            f"基站小区={tp['cell_id']}, 持续分钟={tp['duration_min']}, 制式={tp['rat_type']}, "
            f"时延ms={tp['delay_ms']}, 卡顿秒={tp['stalling_duration_s']}, 运行状态={tp['run_status']}"
        )
    lines = [f"{'用户' if t['role'] == 'user' else '助手'}：{t['content']}" for t in ev["dialogue_turns"]]
    return f"[对话记录 id={nid} 时间={ts} 场所={ev.get('venue')}] 用户={uid}\n" + "\n".join(lines)


@dataclass
class Mem0Fact:
    fid: str
    uid: str
    text: str
    vec: np.ndarray
    ts: str


class RealMem0:
    def __init__(self, client: Client) -> None:
        self.client = client
        self.facts: dict[str, Mem0Fact] = {}
        self.ops: collections.Counter[str] = collections.Counter()
        self._seq = 0

    def _search(self, uid: str, qv: np.ndarray, top_k: int = 6) -> list[tuple[Mem0Fact, float]]:
        res = [(f, float(np.dot(qv, f.vec))) for f in self.facts.values() if f.uid == uid]
        res.sort(key=lambda x: x[1], reverse=True)
        return res[:top_k]

    def ingest(self, uid: str, ts: str, raw: str) -> None:
        ext = self.client.chat_json(MEM0_EXTRACT_SYSTEM, raw, bucket="mem0_write", max_tokens=400)
        for cand in (ext.get("facts") or [])[:4]:
            if not isinstance(cand, str) or len(cand.strip()) < 4:
                continue
            cand = cand.strip()
            cv = self.client.embed(cand, bucket="mem0_write")
            nbs = self._search(uid, cv, top_k=5)
            if not nbs:
                self._add(uid, cand, cv, ts)
                continue
            nb_txt = "\n".join(f"- id={f.fid} (sim={s:.2f}): {f.text}" for f, s in nbs)
            dec = self.client.chat_json(MEM0_UPDATE_SYSTEM, f"新候选事实（时间 {ts}）：{cand}\n\n已有相似记忆：\n{nb_txt}", bucket="mem0_write", max_tokens=300)
            op = str(dec.get("op") or "ADD").upper()
            tid = dec.get("target_id")
            ntxt = dec.get("text") or cand
            if op == "DELETE" and tid in self.facts:
                self.facts.pop(tid)
                self.ops["DELETE"] += 1
            elif op == "UPDATE" and tid in self.facts:
                self.facts[tid].text = ntxt
                self.facts[tid].vec = self.client.embed(ntxt, bucket="mem0_write")
                self.facts[tid].ts = ts
                self.ops["UPDATE"] += 1
            elif op == "NONE":
                self.ops["NONE"] += 1
            else:
                self._add(uid, ntxt, self.client.embed(ntxt, bucket="mem0_write"), ts)

    def _add(self, uid: str, text: str, vec: np.ndarray, ts: str) -> None:
        self._seq += 1
        fid = f"M{self._seq:04d}"
        self.facts[fid] = Mem0Fact(fid, uid, text, vec, ts)
        self.ops["ADD"] += 1

    def retrieve(self, uid: str, query: str, top_k: int = 8) -> list[tuple[Mem0Fact, float]]:
        return self._search(uid, self.client.embed(query, bucket="mem0_query"), top_k=top_k)


@dataclass
class ZepEdge:
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


class RealZep:
    def __init__(self, client: Client) -> None:
        self.client = client
        self.hist: dict[str, list[str]] = collections.defaultdict(list)
        self.edges: dict[str, ZepEdge] = {}
        self.out_e: dict[str, list[str]] = collections.defaultdict(list)
        self.in_e: dict[str, list[str]] = collections.defaultdict(list)
        self._seq = 0

    def ingest(self, uid: str, ep_id: str, ts: str, raw: str) -> None:
        ctx = "\n".join(self.hist[uid][-4:])
        self.hist[uid].append(raw)
        ext = self.client.chat_json(
            ZEP_EXTRACT_SYSTEM,
            f"【最近历史情节】\n{ctx or '无'}\n\n【当前新情节】\n{raw}",
            bucket="zep_write",
            max_tokens=700,
        )
        for inv in (ext.get("invalidations") or []):
            if not isinstance(inv, dict):
                continue
            rel = str(inv.get("rel") or "")
            kw = str(inv.get("target_keyword") or "").lower()
            for e in self.edges.values():
                if e.uid != uid or e.t_invalid is not None:
                    continue
                if rel and e.rel != rel:
                    continue
                if (kw and kw in f"{e.dst} {e.fact_text}".lower()) or (rel == "HAS_BRANCH_RULE" and not kw):
                    e.t_invalid = ts
                    if ep_id not in e.episodes:
                        e.episodes.append(ep_id)

        for item in (ext.get("edges") or []):
            if not isinstance(item, dict):
                continue
            src = str(item.get("src") or "").strip()
            dst = str(item.get("dst") or "").strip()
            rel = str(item.get("rel") or "").strip()
            ft = str(item.get("fact_text") or f"{src} {rel} {dst}").strip()
            if not src or not dst or not rel:
                continue
            if item.get("src_type") == "User" or src in ("用户", uid):
                src = uid
            merged = False
            for eid in self.out_e.get(src, []):
                e = self.edges[eid]
                if e.uid == uid and e.rel == rel and e.dst.lower() == dst.lower() and e.t_invalid is None:
                    if ep_id not in e.episodes:
                        e.episodes.append(ep_id)
                    merged = True
                    break
            if not merged:
                self._seq += 1
                eid = f"E{self._seq:04d}"
                vec = self.client.embed(f"{src} {rel} {dst} {ft}", bucket="zep_write")
                edge = ZepEdge(eid, uid, src, rel, dst, ft, vec, t_valid=ts, episodes=[ep_id])
                self.edges[eid] = edge
                self.out_e[src].append(eid)
                self.in_e[dst].append(eid)

    def retrieve(self, uid: str, query: str, q_ts: str, strict: bool, top_k: int = 8) -> list[tuple[ZepEdge, float]]:
        qv = self.client.embed(query, bucket="zep_query")
        scored = {eid: float(np.dot(qv, e.vec)) for eid, e in self.edges.items() if e.uid == uid}
        seeds = sorted(scored.items(), key=lambda x: x[1], reverse=True)[:4]
        frontier = {uid} | {self.edges[eid].dst for eid, _ in seeds}
        for node in frontier:
            for eid in self.out_e.get(node, []) + self.in_e.get(node, []):
                e = self.edges[eid]
                if e.uid == uid:
                    scored[eid] = max(scored.get(eid, 0.0), float(np.dot(qv, e.vec)) + 0.15)
        ranked = []
        for eid, sc in scored.items():
            e = self.edges[eid]
            if strict and not e.valid_at(q_ts):
                continue
            ranked.append((e, sc + min(0.03 * len(e.episodes), 0.15)))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


def main() -> None:
    cfg = load_cfg()
    client = Client(cfg)
    with open(V2_DATA_PATH, encoding="utf-8") as f:
        ds = json.load(f)
    samples = ds["samples"]
    total_a = sum(len(s["stage_a_events"]) for s in samples)
    logger.info("Running V2 pilot real experiment: %d users, %d Stage-A events (model=%s, emb=%s)",
                len(samples), total_a, cfg["llm"]["model"], cfg["embedding"]["model"])

    mem0 = RealMem0(client)
    zep = RealZep(client)

    # Stage A: 冷启动流式建库
    for s in samples:
        uid = s["persona_id"]
        logger.info("Stage A ingesting %s (%d events)...", uid, len(s["stage_a_events"]))
        for ev in s["stage_a_events"]:
            raw = format_v2_raw(uid, ev)
            mem0.ingest(uid, ev["timestamp"], raw)
            zep.ingest(uid, ev["node_id"], ev["timestamp"], raw)
        u_edges = [e for e in zep.edges.values() if e.uid == uid]
        u_nodes = {e.src for e in u_edges} | {e.dst for e in u_edges}
        star = sum(1 for e in u_edges if e.src == uid or e.dst == uid) / max(len(u_edges), 1)
        logger.info("  Done %s | Mem0 facts=%d (ops=%s) | Zep nodes=%d edges=%d inv=%d star=%.3f",
                    uid, sum(1 for f in mem0.facts.values() if f.uid == uid), dict(mem0.ops),
                    len(u_nodes), len(u_edges), sum(1 for e in u_edges if e.t_invalid), star)

    # Stage B: 11 道探针在 4 模式下端到端评测（No-Mem / Mem0 / Zep-Default / Zep-Strict）
    results: dict[str, Any] = {}
    for mode in ("no_mem", "mem0", "zep_default", "zep_strict"):
        rows = []
        for s in samples:
            uid = s["persona_id"]
            pkg = f"套餐档位={s['profile']['package_tier']}（上限：{s['profile']['mos_baseline']['max_resolution']}，最小时延：{s['profile']['mos_baseline']['min_latency_ms']}ms，最低MOS：{s['profile']['mos_baseline']['min_mos']}）"
            for case in s["stage_b_eval_cases"]:
                q = case["user_turn1"]
                q_ts = case["query_timestamp"]
                if mode == "no_mem":
                    ctx = "（无历史记忆）"
                elif mode == "mem0":
                    hits = mem0.retrieve(uid, q, top_k=8)
                    ctx = "\n".join(f"- [{f.ts}] {f.text}" for f, _ in hits) or "（无命中）"
                else:
                    hits_z = zep.retrieve(uid, q, q_ts, strict=(mode == "zep_strict"), top_k=8)
                    ctx = "\n".join(
                        f"- [生效:{e.t_valid}, 失效:{e.t_invalid or '生效中'}] ({e.src})-[{e.rel}]->({e.dst})：{e.fact_text}（支撑次数={len(e.episodes)}, 情节={e.episodes[:5]}）"
                        for e, _ in hits_z
                    ) or "（无命中）"

                prompt = f"当前时间：{q_ts}\n用户只读套餐信息：{pkg}\n\n【检索到的历史记忆】\n{ctx}\n\n【用户首轮输入】\n{q}"
                ans = client.chat(V2_AGENT_SYSTEM, prompt, bucket=f"{mode}_qa", max_tokens=320)
                judge_in = json.dumps({
                    "user_turn1": q,
                    "expected_interaction_mode": case["expected_interaction_mode"],
                    "gold_intent_template": case["gold_intent_template"],
                    "eval_focus_or_sim": case.get("eval_focus") or case.get("user_simulator_spec"),
                    "agent_output": ans,
                }, ensure_ascii=False)
                j = client.chat_json(V2_JUDGE_SYSTEM, judge_in, bucket="judge", max_tokens=180)
                rows.append({
                    "case_id": case["case_id"],
                    "persona_id": uid,
                    "requires_memory": case["requires_memory"],
                    "mode_expected": case["expected_interaction_mode"],
                    "passed": bool(j.get("passed")),
                    "reason": j.get("reason", ""),
                    "answer": ans,
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

    # 核算负干扰致错率 NIR（无需记忆题中：no_mem 对 → 加记忆后变错）
    no_mem_map = {r["case_id"]: r["passed"] for r in results["no_mem"]["rows"] if not r["requires_memory"]}
    nir_stats = {}
    for m in ("mem0", "zep_default", "zep_strict"):
        base_ok = [cid for cid, ok in no_mem_map.items() if ok]
        regressed = [r["case_id"] for r in results[m]["rows"] if r["case_id"] in base_ok and not r["passed"]]
        nir_stats[m] = {"regressed": regressed, "nir": round(len(regressed) / max(len(base_ok), 1), 3)}

    out = {
        "dataset": V2_DATA_PATH,
        "models": {"llm": cfg["llm"]["model"], "embedding": cfg["embedding"]["model"]},
        "mem0_ops": dict(mem0.ops),
        "api_cost_stats": {k: {sk: round(sv, 2) if isinstance(sv, float) else sv for sk, sv in v.items()} for k, v in client.stats.items()},
        "nir_stats": nir_stats,
        "evaluation": results,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    logger.info("Saved V2 pilot experiment results to %s", OUT_JSON)


if __name__ == "__main__":
    main()

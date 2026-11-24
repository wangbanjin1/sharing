#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基于真实端到端模型实验结果（real_llm_exp_results.json：qwen3.8-flash + text-embedding-v4）
生成简洁直观的 Obsidian Excalidraw 专题笔记与高清配图。
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import math
import os
import random
from typing import Any

from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

HERE = os.path.dirname(os.path.abspath(__file__))
REAL_JSON = os.path.join(HERE, "real_llm_exp_results.json")
MEM_DIR = r"D:\coding\sharing\slides\excalidraw_notes\memory"
ASSETS_DIR = os.path.join(MEM_DIR, "assets")
OUT_MD = os.path.join(MEM_DIR, "12_Graph_vs_Vector_Memory_Analysis.excalidraw.md")
OUT_RAW = os.path.join(MEM_DIR, "12_Graph_vs_Vector_Memory_Analysis.excalidraw")

FONT_REG = r"C:\Windows\Fonts\msyh.ttc"
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"

TYPE_COLOR = {
    "User": (29, 78, 216),
    "App": (21, 128, 61),
    "Cell": (14, 165, 233),
    "Venue": (217, 119, 6),
    "Alias": (124, 58, 237),
    "Category": (100, 116, 139),
    "BranchRule": (220, 38, 38),
}


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw / 2, cy - th / 2), text, font=font, fill=fill)


def infer_node_type(nid: str, rel: str, is_src: bool, uid: str) -> str:
    if nid == uid:
        return "User"
    if rel == "RESIDES_CELL" and not is_src:
        return "Cell"
    if rel == "FREQUENTS_VENUE" and not is_src:
        return "Venue"
    if rel == "HAS_BRANCH_RULE" and not is_src:
        return "BranchRule"
    if rel == "ALIAS_OF" and is_src:
        return "Alias"
    if rel == "BELONGS_TO" and not is_src:
        return "Category"
    return "App"


def render_fig1_real_compare(data: dict[str, Any], out_path: str) -> tuple[int, int]:
    """真实 LLM（qwen3.8-flash）建库产出双栏直观对照图（2x 超采样抗锯齿）。"""
    S = 2
    W, H = 2200 * S, 900 * S
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    f_title = load_font(22 * S, bold=True)
    f_sub = load_font(14 * S, bold=False)
    f_sec = load_font(17 * S, bold=True)
    f_lbl = load_font(13 * S, bold=True)
    f_sm = load_font(12 * S, bold=False)
    f_xs = load_font(10.5 * S, bold=False)

    draw.text((30 * S, 18 * S), "真实模型（qwen3.8-flash + text-embedding-v4）建库产出直观对照", font=f_title, fill=(31, 35, 40))
    draw.text((30 * S, 52 * S), "样本：persona_8613522947905（20 条原始单据与对话，完全屏蔽标注）｜ 4 用户真实建图星型中心度均值 75.6%（70.6%~84.2%）", font=f_sub, fill=(89, 99, 110))

    # 双栏边界
    draw.rounded_rectangle([28 * S, 88 * S, 1130 * S, 832 * S], radius=14 * S, fill=(252, 252, 253), outline=(208, 215, 222), width=2 * S)
    draw.rounded_rectangle([28 * S, 88 * S, 1130 * S, 136 * S], radius=14 * S, fill=(239, 246, 255), outline=(208, 215, 222), width=2 * S)
    draw.text((48 * S, 100 * S), "① Zep 真实 LLM 建出的图（15 节点 · 17 边 · 星型度 70.6% · 失效边=0）", font=f_sec, fill=(29, 78, 216))

    draw.rounded_rectangle([1156 * S, 88 * S, 2172 * S, 832 * S], radius=14 * S, fill=(252, 252, 253), outline=(208, 215, 222), width=2 * S)
    draw.rounded_rectangle([1156 * S, 88 * S, 2172 * S, 136 * S], radius=14 * S, fill=(240, 253, 244), outline=(208, 215, 222), width=2 * S)
    draw.text((1176 * S, 100 * S), "② Mem0 真实 LLM 写入的扁平短句（18 条 · 碎片化 ADD 但原话保真）", font=f_sec, fill=(21, 128, 61))

    # --- 左栏：真实 Zep 图 ---
    cs = data["case_study_real_llm"]
    uid = cs["user_id"]
    edges = cs["zep_edges"]

    nodes: dict[str, str] = {uid: "User"}
    for e in edges:
        if e["src"] not in nodes:
            nodes[e["src"]] = infer_node_type(e["src"], e["rel"], True, uid)
        if e["dst"] not in nodes:
            nodes[e["dst"]] = infer_node_type(e["dst"], e["rel"], False, uid)

    cx, cy = 570 * S, 475 * S
    pos: dict[str, tuple[float, float]] = {uid: (cx, cy)}
    groups: dict[str, list[str]] = {k: [] for k in ("App", "Cell", "Venue", "BranchRule", "Alias", "Category")}
    for nid, ntype in nodes.items():
        if nid != uid and ntype in groups:
            groups[ntype].append(nid)

    def place_arc(arr: list[str], r: float, sdeg: float, edeg: float) -> None:
        for i, nid in enumerate(arr):
            deg = (sdeg + edeg) / 2 if len(arr) == 1 else sdeg + (edeg - sdeg) * i / (len(arr) - 1)
            rad = math.radians(deg)
            pos[nid] = (cx + r * math.cos(rad), cy + r * math.sin(rad))

    place_arc(groups["App"], 205 * S, -148, -48)
    place_arc(groups["Cell"], 240 * S, -15, 52)
    place_arc(groups["Venue"], 205 * S, 95, 135)
    place_arc(groups["BranchRule"], 235 * S, 165, 200)
    place_arc(groups["Alias"], 340 * S, -162, -142)
    place_arc(groups["Category"], 335 * S, -90, -76)

    for e in edges:
        p1, p2 = pos.get(e["src"]), pos.get(e["dst"])
        if not p1 or not p2:
            continue
        is_rule = e["rel"] == "HAS_BRANCH_RULE"
        col = (220, 38, 38) if is_rule else ((29, 78, 216) if e["count"] >= 5 else (148, 163, 184))
        w = int((2.0 + min(math.log2(e["count"] + 1) * 1.1, 3.5)) * S)
        draw.line([p1, p2], fill=col, width=w)
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        tag = f"{e['rel']}({e['count']})"
        if is_rule:
            tag = "未截断旧边 · 新建规则边"
        bbox = draw.textbbox((0, 0), tag, font=f_xs)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad = 4 * S
        bg = (254, 242, 242) if is_rule else (255, 255, 255)
        bd = (252, 165, 165) if is_rule else (226, 232, 240)
        draw.rounded_rectangle([mx - tw / 2 - pad, my - th / 2 - pad / 2, mx + tw / 2 + pad, my + th / 2 + pad / 2], radius=4 * S, fill=bg, outline=bd, width=S)
        draw_centered_text(draw, mx, my, tag, f_xs, (185, 28, 28) if is_rule else (71, 85, 105))

    for nid, ntype in nodes.items():
        p = pos.get(nid)
        if not p:
            continue
        col = TYPE_COLOR.get(ntype, (71, 85, 105))
        r = (28 if ntype == "User" else 17) * S
        draw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=col, outline=(255, 255, 255), width=3 * S)
        lbl = nid.replace("persona_", "U_").replace("company_meeting_room_default", "会议室默认规则").replace("iqiyi_vod_priority_guarantee_at_cafe", "咖啡厅爱奇艺规则")
        if len(lbl) > 13:
            lbl = lbl[:12] + "…"
        draw_centered_text(draw, p[0], p[1] + r + 14 * S, lbl, f_lbl if ntype == "User" else f_sm, (31, 35, 40))

    # 左栏底部高亮注释
    draw.rounded_rectangle([46 * S, 760 * S, 1112 * S, 816 * S], radius=8 * S, fill=(254, 242, 242), outline=(252, 165, 165), width=S)
    draw.text((62 * S, 769 * S), "真实亮点：USES_APP→bilibili_vod 自动合并并累计 11 次（Q1 胜出原因）；", font=f_sm, fill=(21, 128, 61))
    draw.text((62 * S, 792 * S), "真实翻车：4 用户全部 invalid=0！LLM 没截断“突发恶劣天气”旧边，反而新抽了规则边，导致 Q2 全军覆没。", font=f_sm, fill=(185, 28, 28))

    # --- 右栏：真实 Mem0 扁平短句 ---
    mx0, my0 = 1178 * S, 154 * S
    cw = 972 * S
    facts = cs["mem0_facts"][:9]
    for item in facts:
        is_cancel = "取消" in item["text"] or "突发恶劣天气" in item["text"]
        ch = 56 * S
        bg = (240, 253, 244) if is_cancel else (246, 248, 250)
        bd = (134, 239, 172) if is_cancel else (208, 215, 222)
        draw.rounded_rectangle([mx0, my0, mx0 + cw, my0 + ch], radius=8 * S, fill=bg, outline=bd, width=2 * S if is_cancel else S)
        badge = f"[{item['id']}] 原话保真留存（Q2 反杀关键！）" if is_cancel else f"[{item['id']}] 碎片化 ADD（按日期独立存储，未聚合频次）"
        bcol = (21, 128, 61) if is_cancel else (100, 116, 139)
        draw.text((mx0 + 14 * S, my0 + 6 * S), badge, font=f_lbl, fill=bcol)
        txt = item["text"].replace("persona_8613522947905", "U_7905")
        if len(txt) > 58:
            txt = txt[:57] + "…"
        draw.text((mx0 + 14 * S, my0 + 29 * S), txt, font=f_sm, fill=(31, 35, 40))
        my0 += ch + 8 * S

    draw.rounded_rectangle([1178 * S, 760 * S, 2150 * S, 816 * S], radius=8 * S, fill=(255, 251, 235), outline=(252, 211, 77), width=S)
    draw.text((1194 * S, 769 * S), "真实亮点：自然语言短句完整保留了“取消突发恶劣天气规则”原话（Q2 当前态 100%）；", font=f_sm, fill=(21, 128, 61))
    draw.text((1194 * S, 792 * S), "真实短板：全量 ADD=53 / UPDATE=2 / DELETE=0，碎片单据没聚合，导致 Q1 问主力应用时拒答（0%）。", font=f_sm, fill=(180, 83, 9))

    # 底部图例
    ly = 864 * S
    lx = 36 * S
    for name, col in [
        ("User 用户", TYPE_COLOR["User"]),
        ("App 标准应用", TYPE_COLOR["App"]),
        ("Cell 基站小区", TYPE_COLOR["Cell"]),
        ("Venue 场所", TYPE_COLOR["Venue"]),
        ("Alias / Category", TYPE_COLOR["Alias"]),
        ("BranchRule 规则边（真实未触发失效截断）", TYPE_COLOR["BranchRule"]),
    ]:
        draw.ellipse([lx, ly - 8 * S, lx + 16 * S, ly + 8 * S], fill=col)
        draw.text((lx + 24 * S, ly - 10 * S), name, font=f_sm, fill=(51, 65, 85))
        lx += (len(name) * 13 + 72) * S

    final = img.resize((2200, 900), Image.Resampling.LANCZOS)
    final.save(out_path, "PNG")
    logger.info("Saved Fig 1 (real LLM) to %s", out_path)
    return 2200, 900


def render_fig2_real_bench_and_cost(data: dict[str, Any], out_path: str) -> tuple[int, int]:
    """左右双联：左=19 题真实端到端准确率柱状图；右=真实 Token 成本账单对比。"""
    S = 2
    W, H = 1800 * S, 740 * S
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    f_title = load_font(20 * S, bold=True)
    f_sub = load_font(13 * S, bold=False)
    f_lbl = load_font(12 * S, bold=True)
    f_sm = load_font(11 * S, bold=False)

    draw.text((28 * S, 18 * S), "真实模型端到端实测结果（qwen3.8-flash + text-embedding-v4）：准确率与 Token 成本账单", font=f_title, fill=(31, 35, 40))
    draw.text((28 * S, 48 * S), "4 用户 / 67 条原始记录 / 19 题真实问答裁判 ｜ 结论：纯 LLM 自动建图综合得分（42.1%/36.8%）反而不如扁平向量（47.4%），且更贵", font=f_sub, fill=(89, 99, 110))

    # --- 左图：准确率分组柱状图 ---
    lx0, ly0, lx1, ly1 = 76 * S, 138 * S, 1180 * S, 595 * S
    series = [
        ("Mem0（扁平向量 47.4%）", "mem0", (21, 128, 61)),
        ("Zep-Default（含失效边 42.1%）", "zep_default", (217, 119, 6)),
        ("Zep-Strict（时间窗过滤 36.8%）", "zep_strict", (29, 78, 216)),
    ]
    tx = 28 * S
    for name, _, col in series:
        draw.rounded_rectangle([tx, 90 * S, tx + 20 * S, 106 * S], radius=3 * S, fill=col)
        draw.text((tx + 26 * S, 88 * S), name, font=f_lbl, fill=(31, 35, 40))
        tx += 285 * S

    for pct in [0, 25, 50, 75, 100]:
        yy = ly1 - (ly1 - ly0) * (pct / 100.0)
        draw.line([(lx0, yy), (lx1, yy)], fill=(226, 232, 240), width=S)
        draw.text((lx0 - 46 * S, yy - 8 * S), f"{pct}%", font=f_sm, fill=(100, 116, 139))
    draw.line([(lx0, ly1), (lx1, ly1)], fill=(51, 65, 85), width=2 * S)

    cats = [
        ("Q1_single_hop", "Q1 主力应用\n(4题)"),
        ("Q2_temporal_history", "Q2 历史回溯\n(3题)"),
        ("Q2_post_supersede_current", "Q2 撤销当前态\n(3题)"),
        ("Q3_evidence_provenance", "Q3 证据溯源\n(4题)"),
        ("Q5_cross_user_cell", "Q5 跨用户小区\n(4题)"),
        ("overall", "全部 19 题\n(Overall)"),
    ]
    ev = data["evaluation"]
    gw = (lx1 - lx0) / len(cats)
    bw, gap = 34 * S, 8 * S
    for gi, (key, label) in enumerate(cats):
        gx = lx0 + gi * gw + gw / 2
        if key == "overall":
            draw.rounded_rectangle([lx0 + gi * gw + 6 * S, ly0 - 6 * S, lx0 + (gi + 1) * gw - 6 * S, ly1 + 66 * S], radius=8 * S, fill=(248, 250, 252), outline=(203, 213, 225), width=S)
        sx = gx - (3 * bw + 2 * gap) / 2
        for si, (_, skey, col) in enumerate(series):
            acc = ev[skey]["summary"][key]["acc"]
            bx1 = sx + si * (bw + gap)
            bx2 = bx1 + bw
            bh = (ly1 - ly0) * acc
            by1 = ly1 - bh
            if bh > 0:
                draw.rounded_rectangle([bx1, by1, bx2, ly1], radius=4 * S, fill=col)
            else:
                draw.rectangle([bx1, ly1 - 4 * S, bx2, ly1], fill=col)
            draw_centered_text(draw, (bx1 + bx2) / 2, by1 - 12 * S, f"{acc*100:.0f}%", f_sm, col)
        for li, line in enumerate(label.split("\n")):
            draw_centered_text(draw, gx, ly1 + (22 + li * 20) * S, line, f_lbl if li == 0 else f_sm, (31, 35, 40) if li == 0 else (100, 116, 139))

    # --- 右图：真实 Token 成本对比 ---
    draw.rounded_rectangle([1215 * S, 88 * S, 1770 * S, 662 * S], radius=12 * S, fill=(248, 250, 252), outline=(208, 215, 222), width=2 * S)
    draw.text((1240 * S, 106 * S), "真实 Token 成本账单（67 条写入 + 19 题问答）", font=f_lbl, fill=(31, 35, 40))

    st = data["api_cost_stats"]
    mem0_w = st["mem0_write"]["prompt_tokens"] + st["mem0_write"]["completion_tokens"]
    zep_w = st["zep_write"]["prompt_tokens"] + st["zep_write"]["completion_tokens"]
    mem0_q = st["mem0_qa"]["prompt_tokens"] + st["mem0_qa"]["completion_tokens"]
    zep_q = st["zep_default_qa"]["prompt_tokens"] + st["zep_default_qa"]["completion_tokens"]

    cost_rows = [
        ("写入阶段总 Token", mem0_w, zep_w, f"Zep 贵 +{(zep_w/mem0_w - 1)*100:.0f}%（输出为 2.16×）"),
        ("问答阶段总 Token", mem0_q, zep_q, f"Zep 贵 +{(zep_q/mem0_q - 1)*100:.0f}%（上下文更长）"),
        ("写入耗时（秒）", st["mem0_write"]["latency_s"] + st["mem0_write_emb"]["latency_s"],
         st["zep_write"]["latency_s"] + st["zep_write_emb"]["latency_s"], "Zep 写入延迟更高"),
    ]
    cy = 158 * S
    max_bar_w = 470 * S
    for title, mv, zv, note in cost_rows:
        draw.text((1240 * S, cy), title, font=f_lbl, fill=(31, 35, 40))
        draw.text((1430 * S, cy), note, font=f_sm, fill=(185, 28, 28))
        mx = max(mv, zv, 1.0)
        # Mem0 bar
        mw = max(int(max_bar_w * mv / mx), 10 * S)
        draw.rounded_rectangle([1240 * S, cy + 28 * S, 1240 * S + mw, cy + 56 * S], radius=5 * S, fill=(21, 128, 61))
        m_lbl = f"Mem0: {mv:,.0f}" if mv > 500 else f"Mem0: {mv:.1f}s"
        draw.text((1250 * S, cy + 34 * S), m_lbl, font=f_sm, fill=(255, 255, 255))
        # Zep bar
        zw = max(int(max_bar_w * zv / mx), 10 * S)
        draw.rounded_rectangle([1240 * S, cy + 64 * S, 1240 * S + zw, cy + 92 * S], radius=5 * S, fill=(29, 78, 216))
        z_lbl = f"Zep: {zv:,.0f}" if zv > 500 else f"Zep: {zv:.1f}s"
        draw.text((1250 * S, cy + 70 * S), z_lbl, font=f_sm, fill=(255, 255, 255))
        cy += 155 * S

    # 底部总注
    draw.rounded_rectangle([28 * S, 678 * S, 1770 * S, 722 * S], radius=8 * S, fill=(254, 242, 242), outline=(252, 165, 165), width=S)
    draw.text((46 * S, 690 * S), "核心发现：真实模型下 Zep 的 Q1 靠边合并频次胜出（75% 对 0%），但冲突截断全部漏判导致 Q2 掉到 0%，且 Token 开销高出 41%~86%。", font=f_lbl, fill=(185, 28, 28))

    final = img.resize((1800, 740), Image.Resampling.LANCZOS)
    final.save(out_path, "PNG")
    logger.info("Saved Fig 2 (real LLM bench & cost) to %s", out_path)
    return 1800, 740


class ExcalidrawBuilder:
    """Obsidian Excalidraw 笔记画布构建器。"""

    def __init__(self) -> None:
        self.elements: list[dict[str, Any]] = []
        self.text_entries: list[tuple[str, str]] = []
        self.embedded_files: list[tuple[str, str]] = []
        self.raw_files: dict[str, dict[str, Any]] = {}
        self.rng = random.Random(20261124)
        self._seq = 0

    def _next_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}_{self._seq:04d}"

    def _base(self, eid: str, etype: str, x: float, y: float, w: float, h: float, **kw: Any) -> dict[str, Any]:
        return {
            "id": eid,
            "type": etype,
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "angle": 0,
            "strokeColor": kw.get("strokeColor", "#1e1e1e"),
            "backgroundColor": kw.get("backgroundColor", "transparent"),
            "fillStyle": "solid",
            "strokeWidth": kw.get("strokeWidth", 2),
            "strokeStyle": kw.get("strokeStyle", "solid"),
            "roughness": 0,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "roundness": kw.get("roundness", {"type": 3}),
            "seed": self.rng.randint(100000, 2000000000),
            "version": 1,
            "versionNonce": self.rng.randint(100000, 2000000000),
            "isDeleted": False,
            "boundElements": None,
            "updated": 1763950000000,
            "link": None,
            "locked": False,
        }

    def add_rect(self, x: float, y: float, w: float, h: float, stroke: str = "#343a40", bg: str = "#f8f9fa", sw: float = 2.0) -> str:
        eid = self._next_id("rect")
        self.elements.append(self._base(eid, "rectangle", x, y, w, h, strokeColor=stroke, backgroundColor=bg, strokeWidth=sw))
        return eid

    def add_text(self, x: float, y: float, text: str, font_size: int = 20, color: str = "#1e1e1e", w: float = 800, h: float | None = None) -> str:
        eid = self._next_id("txt")
        lines = text.split("\n")
        calc_h = h if h is not None else max(len(lines) * font_size * 1.45, font_size * 1.45)
        el = self._base(eid, "text", x, y, w, calc_h, strokeColor=color, roundness=None)
        el.update({
            "text": text,
            "fontSize": font_size,
            "fontFamily": 3,
            "textAlign": "left",
            "verticalAlign": "top",
            "containerId": None,
            "originalText": text,
            "lineHeight": 1.35,
        })
        self.elements.append(el)
        self.text_entries.append((eid, text))
        return eid

    def add_image(self, x: float, y: float, w: float, h: float, png_path: str, wiki_name: str) -> str:
        with open(png_path, "rb") as f:
            raw = f.read()
        fid = hashlib.sha1(raw).hexdigest()
        b64 = base64.b64encode(raw).decode("ascii")
        self.embedded_files.append((fid, f"[[{wiki_name}]]"))
        self.raw_files[fid] = {
            "mimeType": "image/png",
            "id": fid,
            "dataURL": f"data:image/png;base64,{b64}",
            "created": 1763950000000,
            "lastRetrieved": 1763950000000,
        }
        eid = self._next_id("img")
        el = self._base(eid, "image", x, y, w, h, strokeColor="transparent", roundness=None)
        el.update({"status": "saved", "fileId": fid, "scale": [1, 1]})
        self.elements.append(el)
        return eid

    def add_card(self, x: float, y: float, w: float, h: float, title: str, body: str, stroke: str, bg: str, title_color: str) -> None:
        self.add_rect(x, y, w, h, stroke=stroke, bg=bg, sw=2.2)
        self.add_text(x + 22, y + 16, title, font_size=22, color=title_color, w=w - 44)
        self.add_text(x + 22, y + 54, body, font_size=17, color="#2b3035", w=w - 44, h=h - 68)

    def build_raw_json(self) -> dict[str, Any]:
        return {
            "type": "excalidraw",
            "version": 2,
            "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin/releases/tag/2.0.0",
            "elements": self.elements,
            "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
            "files": self.raw_files,
        }

    def build_obsidian_md(self) -> str:
        header = """---

excalidraw-plugin: parsed
tags: [excalidraw, agent-memory, zep, mem0, graph-vs-vector, real-llm-experiment]

---
==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠==


# Excalidraw Data

## Text Elements
"""
        txt_block = "\n\n".join(f"{txt} ^{eid}" for eid, txt in self.text_entries)
        emb_block = "\n\n".join(f"{fid}: {target}" for fid, target in self.embedded_files)
        md_json = {
            "type": "excalidraw",
            "version": 2,
            "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin/releases/tag/2.0.0",
            "elements": self.elements,
            "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
            "files": {},
        }
        return (
            header
            + txt_block
            + "\n\n## Embedded Files\n"
            + emb_block
            + "\n\n%%\n## Drawing\n```json\n"
            + json.dumps(md_json, ensure_ascii=False, indent=2)
            + "\n```\n%%\n"
        )


def main() -> None:
    os.makedirs(ASSETS_DIR, exist_ok=True)
    with open(REAL_JSON, encoding="utf-8") as f:
        data = json.load(f)

    fig1_name = "graph_vs_vector_fig1_topology_compare.png"
    fig2_name = "graph_vs_vector_fig2_benchmark_bars.png"
    fig1_path = os.path.join(ASSETS_DIR, fig1_name)
    fig2_path = os.path.join(ASSETS_DIR, fig2_name)
    render_fig1_real_compare(data, fig1_path)
    render_fig2_real_bench_and_cost(data, fig2_path)

    eb = ExcalidrawBuilder()
    W = 2240

    # 顶部紧凑标题
    eb.add_rect(40, 30, W, 118, stroke="#343a40", bg="#f8f9fa", sw=2.4)
    eb.add_text(72, 48, "记忆管理建图与否实测笔记：Zep-Graphiti (图谱) 与 Mem0 (扁平向量) 真实模型对照", font_size=30, color="#1e1e1e", w=2160)
    eb.add_text(
        72, 94,
        "真实端到端模型：qwen3.8-flash + text-embedding-v4 (1024维) ｜ 数据：hybrid_dataset.json 4 用户 67 条原始单据与对话（完全屏蔽标注）",
        font_size=18, color="#495057", w=2160
    )

    # 上半区：图 1（真实 LLM 建库产出双栏对照）
    eb.add_rect(40, 174, W, 962, stroke="#343a40", bg="#ffffff", sw=2.0)
    eb.add_text(72, 192, "一、真实模型建库直观对照：同一用户（persona_8613522947905），建图与存向量分别长什么样？", font_size=23, color="#1e1e1e", w=2160)
    eb.add_image(60, 232, 2200, 888, fig1_path, fig1_name)

    # 下半区：左放图 2（19 题实测准确率 + 成本账单），右放 3 张极简决策卡
    row2_y = 1164
    row2_h = 626
    eb.add_rect(40, row2_y, 1400, row2_h, stroke="#343a40", bg="#ffffff", sw=2.0)
    eb.add_text(64, row2_y + 14, "二、19 题真实端到端准确率与 Token 成本账单（无规则替身，首轮原始基线）", font_size=21, color="#1e1e1e", w=1340)
    eb.add_image(58, row2_y + 52, 1364, 560, fig2_path, fig2_name)

    rx, rw = 1466, 814
    eb.add_card(
        rx, row2_y, rw, 200,
        "两边各自真实管用的优势（高度互补）",
        "• Zep 真正赢在「边合并与频次计数」：同名边自动累计支撑次数，Q1 问主力应用拿到 75%（Mem0 因碎片化 ADD 拒答，0%）。\n"
        "• Mem0 真正赢在「自然语言原话保真」：老实存下“取消突发恶劣天气规则”原句，Q2 撤销后当前态拿到 100%（Zep 0%）。",
        stroke="#15803d", bg="#f0fdf4", title_color="#15803d"
    )
    eb.add_card(
        rx, row2_y + 214, rw, 204,
        "纯 LLM 自动建图暴露的 3 个真实硬伤",
        "1. 单用户高度星型化：真实建图 75.6% 边直连 User，没有复杂网状结构。\n"
        "2. 冲突截断极脆弱：4 用户全部 invalid=0，LLM 漏判撤销导致 Q2 全军覆没。\n"
        "3. 更贵且 3 跳被挤爆：写入 Token 贵 +41%、问答贵 +86%；跨用户 Q5 第 3 跳被 Top-8 挤出，得分 0%。",
        stroke="#b91c1c", bg="#fef2f2", title_color="#b91c1c"
    )
    eb.add_card(
        rx, row2_y + 432, rw, 194,
        "联接 Agent 最终落地结论（取长补短）",
        "• 不走纯 LLM 自由建图（贵且冲突截断不可靠），采用「确定性结构化双时态槽位表 + 向量原文短句库」双轨设计：\n"
        "  ① 槽位表负责确定性的应用/小区频次合并与 [t_valid, t_invalid) 状态机（拿走 Zep 的 Q1 优势）；\n"
        "  ② 向量短句库保留改口撤销等自然语言细节（拿走 Mem0 的 Q2 保真优势）。",
        stroke="#1d4ed8", bg="#eff6ff", title_color="#1d4ed8"
    )

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(eb.build_obsidian_md())
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(eb.build_raw_json(), f, ensure_ascii=False, indent=2)

    logger.info("Updated Obsidian Excalidraw note with REAL LLM results: %s", OUT_MD)


if __name__ == "__main__":
    main()

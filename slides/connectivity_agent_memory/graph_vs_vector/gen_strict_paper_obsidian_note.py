#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基于严格原论文完整复现版实验结果（v2_strict_paper_exp_results.json + No-Mem 基线），
生成干净、无精简版干扰的 Obsidian Excalidraw 专题笔记（12_Graph_vs_Vector_Memory_Analysis）。
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import random
from typing import Any

from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

HERE = os.path.dirname(os.path.abspath(__file__))
LITE_JSON = os.path.join(HERE, "v2_pilot_exp_results.json")
STRICT_JSON = os.path.join(HERE, "v2_strict_paper_exp_results.json")
MEM_DIR = r"D:\coding\sharing\slides\excalidraw_notes\memory"
ASSETS_DIR = os.path.join(MEM_DIR, "assets")
OUT_MD = os.path.join(MEM_DIR, "12_Graph_vs_Vector_Memory_Analysis.excalidraw.md")
OUT_RAW = os.path.join(MEM_DIR, "12_Graph_vs_Vector_Memory_Analysis.excalidraw")

FONT_REG = r"C:\Windows\Fonts\msyh.ttc"
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"


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


def draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    p1: tuple[float, float],
    p2: tuple[float, float],
    color: tuple[int, int, int],
    width: int = 4,
    dash: int = 14,
    gap: int = 8,
) -> None:
    import math
    x1, y1 = p1
    x2, y2 = p2
    dist = math.hypot(x2 - x1, y2 - y1)
    if dist == 0:
        return
    dx, dy = (x2 - x1) / dist, (y2 - y1) / dist
    pos = 0.0
    while pos < dist:
        end = min(pos + dash, dist)
        draw.line([(x1 + dx * pos, y1 + dy * pos), (x1 + dx * end, y1 + dy * end)], fill=color, width=width)
        pos += dash + gap


def render_fig0_mechanism_and_structure(out_path: str) -> tuple[int, int]:
    """图 0：建图（Zep/Graphiti）与扁平向量（Mem0）的实际区别——存储长相 + 写入/更新/检索全链路对照。"""
    S = 2
    W, H = 2200 * S, 940 * S
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    f_title = load_font(22 * S, bold=True)
    f_sub = load_font(14 * S, bold=False)
    f_sec = load_font(16 * S, bold=True)
    f_lbl = load_font(13 * S, bold=True)
    f_sm = load_font(12 * S, bold=False)
    f_xs = load_font(10.5 * S, bold=False)

    draw.text((30 * S, 18 * S), "建图（Zep / Graphiti）与扁平向量（Mem0）的实际区别：存储形态与读写检索机制", font=f_title, fill=(31, 35, 40))
    draw.text((30 * S, 52 * S), "以 V2 试点用户 USER_001（商务差旅 · 腾讯会议主线 + 5天出差钉钉临时规则 + 私有简称「腾会」）为例，直观看清两边存的到底有什么不同", font=f_sub, fill=(89, 99, 110))

    # --- 上半区：存储形态直观对比（左：Zep 三层双时态图 | 右：Mem0 扁平向量短句库） ---
    draw.rounded_rectangle([28 * S, 88 * S, 1110 * S, 608 * S], radius=12 * S, fill=(252, 252, 253), outline=(147, 197, 253), width=2 * S)
    draw.rounded_rectangle([28 * S, 88 * S, 1110 * S, 134 * S], radius=12 * S, fill=(239, 246, 255), outline=(147, 197, 253), width=2 * S)
    draw.text((48 * S, 99 * S), "① Zep / Graphiti 存储形态：三层双时态图（单用户呈浅星型 · 76.5% 边直连 User）", font=f_sec, fill=(29, 78, 216))

    # 左侧画 USER_001 真实双时态图结构
    cx, cy = 535 * S, 355 * S
    nodes = [
        ("USER_001", cx, cy, 30 * S, (29, 78, 216), "USER_001"),
        ("tencentmeeting", cx - 190 * S, cy - 115 * S, 20 * S, (21, 128, 61), "tencentmeeting"),
        ("腾会", cx - 375 * S, cy - 135 * S, 17 * S, (124, 58, 237), "别名:腾会"),
        ("cell_main", cx + 245 * S, cy - 110 * S, 18 * S, (14, 165, 233), "Cell 4600040386A"),
        ("venue_main", cx + 255 * S, cy + 75 * S, 18 * S, (217, 119, 6), "科技园独立会议室"),
        ("trip_rule", cx - 235 * S, cy + 105 * S, 19 * S, (220, 38, 38), "出差钉钉临时规则"),
        ("episodes", cx + 30 * S, cy + 165 * S, 17 * S, (100, 116, 139), "底层只读 Episode 层"),
    ]
    npos = {n[0]: (n[1], n[2]) for n in nodes}
    edges = [
        ("USER_001", "tencentmeeting", "USES_APP (cnt=6, 生效)", (29, 78, 216), False, 5 * S),
        ("腾会", "tencentmeeting", "ALIAS_OF", (124, 58, 237), False, 3 * S),
        ("USER_001", "cell_main", "RESIDES_CELL (cnt=7)", (14, 165, 233), False, 4 * S),
        ("USER_001", "venue_main", "FREQUENTS_VENUE", (217, 119, 6), False, 3 * S),
        ("USER_001", "trip_rule", "已过期 [01-12..01-17)", (220, 38, 38), True, 4 * S),
        ("USER_001", "episodes", "episodes[] 双向溯源", (100, 116, 139), True, 2 * S),
    ]
    for s_id, d_id, lbl, col, dashed, lw in edges:
        p1, p2 = npos[s_id], npos[d_id]
        if dashed:
            draw_dashed_line(draw, p1, p2, col, width=lw)
        else:
            draw.line([p1, p2], fill=col, width=lw)
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        bbox = draw.textbbox((0, 0), lbl, font=f_xs)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        bg = (254, 242, 242) if col == (220, 38, 38) else (255, 255, 255)
        draw.rounded_rectangle([mx - tw / 2 - 5 * S, my - th / 2 - 3 * S, mx + tw / 2 + 5 * S, my + th / 2 + 3 * S], radius=4 * S, fill=bg, outline=col, width=S)
        draw_centered_text(draw, mx, my, lbl, f_xs, col)

    for nid, nx, ny, r, col, lbl in nodes:
        draw.ellipse([nx - r, ny - r, nx + r, ny + r], fill=col, outline=(255, 255, 255), width=3 * S)
        draw_centered_text(draw, nx, ny + r + 14 * S, lbl, f_lbl if nid == "USER_001" else f_sm, (31, 35, 40))

    draw.rounded_rectangle([46 * S, 558 * S, 1090 * S, 594 * S], radius=6 * S, fill=(239, 246, 255), outline=(147, 197, 253), width=S)
    draw.text((60 * S, 567 * S), "特点：同名实体自动合并计数、保留双时间轴 [t_valid, t_invalid) 不删历史、支持跨实体/跨用户多跳；但单用户多为 1 跳星型。", font=f_sm, fill=(29, 78, 216))

    # 右侧画 Mem0 扁平向量库结构
    draw.rounded_rectangle([1136 * S, 88 * S, 2172 * S, 608 * S], radius=12 * S, fill=(252, 252, 253), outline=(134, 239, 172), width=2 * S)
    draw.rounded_rectangle([1136 * S, 88 * S, 2172 * S, 134 * S], radius=12 * S, fill=(240, 253, 244), outline=(134, 239, 172), width=2 * S)
    draw.text((1156 * S, 99 * S), "② Mem0 存储形态：按 user_id 隔离的扁平自然语言短句 + 1024 维向量", font=f_sec, fill=(21, 128, 61))

    # 全局摘要 S 卡片
    draw.rounded_rectangle([1158 * S, 150 * S, 2150 * S, 208 * S], radius=8 * S, fill=(255, 251, 235), outline=(252, 211, 77), width=2 * S)
    draw.text((1174 * S, 158 * S), "[全局对话摘要 S · 异步刷新] USER_001 为商务差旅用户，工作日早间常用腾讯会议(1080P/30ms)，曾有5天出差钉钉临时规则。", font=f_sm, fill=(180, 83, 9))
    draw.text((1174 * S, 182 * S), "作用：供阶段一抽取时做跨轮指代消解与上下文补充（配合最近 m=10 条滑窗）。", font=f_xs, fill=(120, 113, 108))

    mem0_cards = [
        ("M0001 | vec[1024]", "USER_001 工作日早间常在小区 4600040386A 使用腾讯会议开视频会议，偏好 1080P、30ms 内。", (246, 248, 250), (208, 215, 222), (31, 35, 40)),
        ("M0002 | vec[1024]", "USER_001 习惯将腾讯会议简称为「腾会」，在科技园独立会议室按「老样子」保障。", (246, 248, 250), (208, 215, 222), (31, 35, 40)),
        ("M0003 | vec[1024]", "USER_001 于 2026-01-12 因异地出差建立 5 天钉钉临时规则（720P/25ms，01-17 到期）。", (246, 248, 250), (208, 215, 222), (31, 35, 40)),
        ("M0004 | UPDATE/DELETE", "若发生显式撤销或覆盖：阶段二直接原地改写(UPDATE)或物理删除(DELETE)旧短句，不留双时态区间。", (254, 242, 242), (252, 165, 165), (185, 28, 28)),
    ]
    my = 224 * S
    for tag, txt, bg, bd, fg in mem0_cards:
        draw.rounded_rectangle([1158 * S, my, 2150 * S, my + 72 * S], radius=8 * S, fill=bg, outline=bd, width=S)
        draw.rounded_rectangle([1172 * S, my + 12 * S, 1345 * S, my + 36 * S], radius=4 * S, fill=(226, 232, 240))
        draw_centered_text(draw, 1258 * S, my + 24 * S, tag, f_xs, (31, 35, 40))
        draw.text((1172 * S, my + 43 * S), txt, font=f_sm, fill=fg)
        my += 82 * S

    draw.rounded_rectangle([1158 * S, 558 * S, 2150 * S, 594 * S], radius=6 * S, fill=(240, 253, 244), outline=(134, 239, 172), width=S)
    draw.text((1172 * S, 567 * S), "特点：自然语言短句保真度高（易留存取消/恢复原话）、实现简单；但无情节溯源边、按用户隔离无法跨用户多跳。", font=f_sm, fill=(21, 128, 61))

    # --- 下半区：写入 → 更新 → 检索 三阶段机制对比表 ---
    draw.rounded_rectangle([28 * S, 628 * S, 2172 * S, 922 * S], radius=12 * S, fill=(248, 250, 252), outline=(208, 215, 222), width=2 * S)
    draw.text((48 * S, 642 * S), "③ 核心工程机制逐环节对比：写入（抽取） → 更新（冲突裁决） → 检索（召回重排）", font=f_sec, fill=(31, 35, 40))

    rows = [
        ("1. 写入与抽取",
         "输入：当前消息 + m=10 历史滑窗 + 全局摘要 S → 抽取自包含短句（15~60字）并编码为 1024 维向量。",
         "输入：底层无损写 Episode + n=4 滑窗 → 抽实体与有向边 + 独立换算绝对 valid_at / invalid_at + 刷新实体摘要。"),
        ("2. 更新与冲突",
         "按向量召回 s=10 条最相似旧记忆 → LLM 判 ADD / UPDATE / DELETE，直接覆盖或物理删旧（丢历史区间）。",
         "同名边合并累加 episodes[]；对新边按 sim≥0.6 召回旧边 → 独立 LLM 判冲突并截断旧边 t_invalid（保留历史）。"),
        ("3. 检索与重排",
         "按 user_id 过滤后做单路稠密向量余弦 Top-K 召回（无时间窗硬过滤，无跨实体/跨用户多跳）。",
         "Vector + BM25 + 1~2 跳 BFS 三路并行召回 → RRF 倒数秩融合重排 + 实体摘要（必须配严格时间窗过滤失效边）。"),
    ]
    ry = 684 * S
    draw.rounded_rectangle([48 * S, ry, 2152 * S, ry + 36 * S], radius=6 * S, fill=(226, 232, 240))
    draw.text((66 * S, ry + 9 * S), "处理环节", font=f_lbl, fill=(31, 35, 40))
    draw.text((250 * S, ry + 9 * S), "Mem0（扁平向量路线 · arXiv:2504.19413）", font=f_lbl, fill=(21, 128, 61))
    draw.text((1210 * S, ry + 9 * S), "Zep / Graphiti（双时态知识图谱路线 · arXiv:2501.13956）", font=f_lbl, fill=(29, 78, 216))
    ry += 44 * S
    for stage, m_txt, z_txt in rows:
        draw.rounded_rectangle([48 * S, ry, 2152 * S, ry + 56 * S], radius=6 * S, fill=(255, 255, 255), outline=(226, 232, 240), width=S)
        draw.text((66 * S, ry + 18 * S), stage, font=f_lbl, fill=(31, 35, 40))
        draw.text((250 * S, ry + 18 * S), m_txt, font=f_sm, fill=(51, 65, 85))
        draw.text((1210 * S, ry + 18 * S), z_txt, font=f_sm, fill=(51, 65, 85))
        ry += 64 * S

    final = img.resize((2200, 940), Image.Resampling.LANCZOS)
    final.save(out_path, "PNG")
    logger.info("Saved Fig 0 (mechanism & structure) to %s", out_path)
    return 2200, 940


def render_fig1_accuracy_and_cost(lite: dict[str, Any], strict: dict[str, Any], out_path: str) -> tuple[int, int]:
    """图 1：4 组严格原论文版对照准确率 + 真实 Token 与耗时成本账单。"""
    S = 2
    W, H = 2200 * S, 820 * S
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    f_title = load_font(22 * S, bold=True)
    f_sub = load_font(14 * S, bold=False)
    f_sec = load_font(16 * S, bold=True)
    f_lbl = load_font(13 * S, bold=True)
    f_sm = load_font(12 * S, bold=False)

    draw.text((30 * S, 18 * S), "严格原论文复现版实测对照：Mem0 (扁平向量) 与 Zep / Graphiti (双时态图谱)", font=f_title, fill=(31, 35, 40))
    draw.text((30 * S, 52 * S), "模型：qwen3.8-flash + text-embedding-v4 (1024维) ｜ 数据：V2 试点 3 用户（38 条 Stage A 双源事件 · 11 道 Stage B 探针 · E1.2 QC 全绿）", font=f_sub, fill=(89, 99, 110))

    # --- 左图：4 组系统准确率 ---
    draw.rounded_rectangle([28 * S, 90 * S, 1380 * S, 740 * S], radius=12 * S, fill=(252, 252, 253), outline=(208, 215, 222), width=2 * S)
    draw.text((48 * S, 106 * S), "① 4 组系统端到端通过率对比（总通过率 / 需用记忆 5 题 / 无需记忆基线 6 题）", font=f_sec, fill=(31, 35, 40))

    series_meta = [
        ("全部 11 题总通过率", "all", (29, 78, 216)),
        ("需用记忆难题 (5题)", "requires_memory", (21, 128, 61)),
        ("无需记忆基线 (6题)", "no_memory_baseline", (217, 119, 6)),
    ]
    lx = 48 * S
    for name, _, col in series_meta:
        draw.rounded_rectangle([lx, 144 * S, lx + 20 * S, 160 * S], radius=3 * S, fill=col)
        draw.text((lx + 26 * S, 141 * S), name, font=f_lbl, fill=(31, 35, 40))
        lx += 245 * S

    systems = [
        ("No-Mem\n(无记忆基线)", lite["evaluation"]["no_mem"]["summary"]),
        ("Mem0\n(m=10滑窗 + 摘要S + s=10)", strict["evaluation"]["mem0_full"]["summary"]),
        ("Zep-Default\n(独立冲突 + 摘要 + 三路RRF)", strict["evaluation"]["zep_full_default"]["summary"]),
        ("Zep-Strict\n(同左 + 严格时间窗过滤)", strict["evaluation"]["zep_full_strict"]["summary"]),
    ]

    x0, y0, x1, y1 = 92 * S, 194 * S, 1340 * S, 628 * S
    for pct in [0, 25, 50, 75, 100]:
        yy = y1 - (y1 - y0) * (pct / 100.0)
        draw.line([(x0, yy), (x1, yy)], fill=(226, 232, 240), width=S)
        draw.text((x0 - 48 * S, yy - 8 * S), f"{pct}%", font=f_sm, fill=(100, 116, 139))
    draw.line([(x0, y1), (x1, y1)], fill=(51, 65, 85), width=2 * S)

    gw = (x1 - x0) / len(systems)
    bw, gap = 52 * S, 12 * S
    for gi, (slabel, smry) in enumerate(systems):
        gx = x0 + gi * gw + gw / 2
        if gi in (1, 3):
            draw.rounded_rectangle([x0 + gi * gw + 14 * S, y0 - 8 * S, x0 + (gi + 1) * gw - 14 * S, y1 + 88 * S], radius=10 * S, fill=(239, 246, 255), outline=(147, 197, 253), width=S)
        sx = gx - (3 * bw + 2 * gap) / 2
        for si, (_, skey, col) in enumerate(series_meta):
            acc = smry[skey]["acc"]
            bx1 = sx + si * (bw + gap)
            bx2 = bx1 + bw
            bh = (y1 - y0) * acc
            by1 = y1 - bh
            draw.rounded_rectangle([bx1, by1, bx2, y1], radius=5 * S, fill=col)
            draw_centered_text(draw, (bx1 + bx2) / 2, by1 - 14 * S, f"{acc*100:.1f}%", f_lbl, col)
        for li, line in enumerate(slabel.split("\n")):
            draw_centered_text(draw, gx, y1 + (26 + li * 22) * S, line, f_lbl if li == 0 else f_sm, (31, 35, 40) if li == 0 else (71, 85, 105))

    # --- 右图：真实 Token 与耗时成本账单 ---
    draw.rounded_rectangle([1408 * S, 90 * S, 2172 * S, 740 * S], radius=12 * S, fill=(248, 250, 252), outline=(208, 215, 222), width=2 * S)
    draw.text((1434 * S, 106 * S), "② 真实写入与问答成本账单（38 条写入 + 11 题问答）", font=f_sec, fill=(31, 35, 40))

    ss = strict["api_cost_stats"]
    mem0_w = ss["mem0_full_write"]["prompt_tokens"] + ss["mem0_full_write"]["completion_tokens"]
    zep_w = ss["zep_full_write"]["prompt_tokens"] + ss["zep_full_write"]["completion_tokens"]
    cost_blocks = [
        ("Stage A 写入总 Token（Mem0 滑窗 m=10 vs Zep 滑窗 n=4）", [
            ("Mem0 原论文版", mem0_w, (21, 128, 61)),
            ("Zep 原论文版", zep_w, (29, 78, 216)),
        ]),
        ("Stage A 写入 LLM 耗时（秒）", [
            ("Mem0 原论文版 (87次调用)", ss["mem0_full_write"]["latency_s"], (21, 128, 61)),
            ("Zep 原论文版 (80次调用)", ss["zep_full_write"]["latency_s"], (29, 78, 216)),
        ]),
        ("Stage B 问答阶段输入 Token（11 题）", [
            ("Mem0 原论文版", ss["mem0_full_qa"]["prompt_tokens"], (21, 128, 61)),
            ("Zep-Strict 原论文版", ss["zep_full_strict_qa"]["prompt_tokens"], (29, 78, 216)),
        ]),
    ]

    cy = 162 * S
    max_w = 680 * S
    for title, items in cost_blocks:
        draw.text((1434 * S, cy), title, font=f_lbl, fill=(31, 35, 40))
        cy += 30 * S
        mx = max(v for _, v, _ in items) or 1.0
        for name, val, col in items:
            w = max(int(max_w * val / mx), 120 * S)
            draw.rounded_rectangle([1434 * S, cy, 1434 * S + w, cy + 38 * S], radius=6 * S, fill=col)
            vtxt = f"{val:,.0f}" if val > 500 else f"{val:.1f}s"
            draw.text((1448 * S, cy + 9 * S), f"{name}: {vtxt}", font=f_lbl, fill=(255, 255, 255))
            cy += 48 * S
        cy += 36 * S

    draw.rounded_rectangle([28 * S, 758 * S, 2172 * S, 804 * S], radius=8 * S, fill=(240, 253, 244), outline=(134, 239, 172), width=S)
    draw.text((48 * S, 770 * S), "核心实证：严格按原论文复现后，Mem0 与 Zep-Strict 在总通过率（72.7%）、需用记忆难题（60.0%）与写入耗时（~140s）上全面打平；Zep 不滤失效边则掉至 63.6%。", font=f_lbl, fill=(21, 128, 61))

    final = img.resize((2200, 820), Image.Resampling.LANCZOS)
    final.save(out_path, "PNG")
    logger.info("Saved Fig 1 to %s", out_path)
    return 2200, 820


def render_fig2_case_matrix(lite: dict[str, Any], strict: dict[str, Any], out_path: str) -> tuple[int, int]:
    """图 2：11 道 V2 探针在 4 组系统下的逐题通过热力矩阵与失败根因总览（无精简版干扰）。"""
    S = 2
    W, H = 2200 * S, 860 * S
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    f_title = load_font(22 * S, bold=True)
    f_sub = load_font(14 * S, bold=False)
    f_lbl = load_font(13 * S, bold=True)
    f_sm = load_font(12 * S, bold=False)

    draw.text((30 * S, 18 * S), "11 道 V2 探针逐题通过矩阵（严格原论文版对照：一眼定位共同天花板与失效边干扰）", font=f_title, fill=(31, 35, 40))
    draw.text((30 * S, 52 * S), "绿块 = 通过（OK）｜ 红块 = 失败（FAIL）｜ 右侧列出 Mem0 与 Zep-Strict 的真实失败归因", font=f_sub, fill=(89, 99, 110))

    cols = [
        ("No-Mem\n基线", lite["evaluation"]["no_mem"]["rows"]),
        ("Mem0\n原论文版", strict["evaluation"]["mem0_full"]["rows"]),
        ("Zep-Default\n含失效边", strict["evaluation"]["zep_full_default"]["rows"]),
        ("Zep-Strict\n时间过滤", strict["evaluation"]["zep_full_strict"]["rows"]),
    ]
    case_labels = {
        "U001_P01_ALIAS_AND_TTL_FALLBACK": ("U001_P01 私有简称 + 5天TTL到期回退", "需记忆"),
        "U001_P02_CROSS_CHANNEL_SMOOTH_VS_STALL": ("U001_P02 跨通道单据时间平移(09:05+30m)", "需记忆"),
        "U001_P03_NEW_APP_NO_GUESS": ("U001_P03 新应用无记录防盲猜(I2.1)", "基线"),
        "U001_P04_EXPLICIT_OVERRIDE_NO_TAMPER": ("U001_P04 显式指定参数防记忆篡改", "基线"),
        "U002_P01_IMPLICIT_MIGRATION_AND_SKIP_CONSULT": ("U002_P01 纯单据隐式迁移(4K/30ms)", "需记忆"),
        "U002_P02_CONCURRENT_AND_TRADEOFF": ("U002_P02 前后台并发与多指标权衡", "基线"),
        "U002_P03_CROSS_INTENT_NEGATION_PROTECT": ("U002_P03 跨意图显式否定保护(L1.3)", "基线"),
        "U003_P01_PROCEDURAL_CLOSED_CLARIFY": ("U003_P01 抖音子业务闭合追问(I2.2)", "需记忆"),
        "U003_P02_FORBIDDEN_BOUNDARY_5G_SKIP": ("U003_P02 5G稳定覆盖禁用边界自检", "需记忆"),
        "U003_P03_PACKAGE_MOS_NEGOTIATION": ("U003_P03 超标准档套餐协商(I2.6)", "基线"),
        "U003_P04_NEAR_MISS_OOD_AND_SEMI_CHITCHAT": ("U003_P04 半闲聊礼貌闭合收口(I2.11)", "基线"),
    }

    x_name = 32 * S
    x_tag = 450 * S
    x_mat = 548 * S
    col_w = 160 * S
    x_note = x_mat + len(cols) * col_w + 20 * S
    y_hdr = 94 * S
    row_h = 58 * S

    draw.rounded_rectangle([28 * S, y_hdr, 2172 * S, y_hdr + 54 * S], radius=8 * S, fill=(241, 245, 249), outline=(203, 213, 225), width=S)
    draw.text((x_name + 10 * S, y_hdr + 16 * S), "V2 测试探针（按表 2 × 表 3 × 表 4）", font=f_lbl, fill=(31, 35, 40))
    draw.text((x_tag + 8 * S, y_hdr + 16 * S), "类别", font=f_lbl, fill=(31, 35, 40))
    for ci, (cname, _) in enumerate(cols):
        cx = x_mat + ci * col_w + col_w / 2
        lines = cname.split("\n")
        for li, line in enumerate(lines):
            draw_centered_text(draw, cx, y_hdr + (16 + li * 20) * S, line, f_lbl, (29, 78, 216) if ci in (1, 3) else (31, 35, 40))
    draw.text((x_note + 8 * S, y_hdr + 16 * S), "真实失败归因（共同天花板 vs. 单边失误）", font=f_lbl, fill=(31, 35, 40))

    base_rows = lite["evaluation"]["no_mem"]["rows"]
    for ri, brow in enumerate(base_rows):
        cid = brow["case_id"]
        yy = y_hdr + 60 * S + ri * row_h
        bg = (255, 255, 255) if ri % 2 == 0 else (248, 250, 252)
        draw.rectangle([28 * S, yy, 2172 * S, yy + row_h], fill=bg)
        draw.line([(28 * S, yy + row_h), (2172 * S, yy + row_h)], fill=(226, 232, 240), width=S)

        cn_name, tag = case_labels.get(cid, (cid, "需记忆"))
        draw.text((x_name + 10 * S, yy + 18 * S), cn_name, font=f_lbl, fill=(31, 35, 40))
        tbg = (239, 246, 255) if tag == "需记忆" else (241, 245, 249)
        tfg = (29, 78, 216) if tag == "需记忆" else (71, 85, 105)
        draw.rounded_rectangle([x_tag, yy + 15 * S, x_tag + 78 * S, yy + 43 * S], radius=12 * S, fill=tbg)
        draw_centered_text(draw, x_tag + 39 * S, yy + 29 * S, tag, f_sm, tfg)

        for ci, (_, crows) in enumerate(cols):
            ok = crows[ri]["passed"]
            bx1 = x_mat + ci * col_w + 18 * S
            bx2 = x_mat + (ci + 1) * col_w - 18 * S
            fill_c = (220, 252, 231) if ok else (254, 226, 226)
            bd_c = (134, 239, 172) if ok else (252, 165, 165)
            txt_c = (21, 128, 61) if ok else (185, 28, 28)
            draw.rounded_rectangle([bx1, yy + 11 * S, bx2, yy + row_h - 11 * S], radius=7 * S, fill=fill_c, outline=bd_c, width=S)
            draw_centered_text(draw, (bx1 + bx2) / 2, yy + row_h / 2, "OK" if ok else "FAIL", f_lbl, txt_c)

        m_row = strict["evaluation"]["mem0_full"]["rows"][ri]
        z_row = strict["evaluation"]["zep_full_strict"]["rows"][ri]
        if m_row["passed"] and z_row["passed"]:
            note = "Mem0 与 Zep-Strict 均稳定通过"
            ncol = (21, 128, 61)
        elif not m_row["passed"] and not z_row["passed"]:
            note = f"【共同天花板】Mem0: {m_row['reason'][:32]}｜Zep: {z_row['reason'][:32]}"
            ncol = (185, 28, 28)
        elif not m_row["passed"]:
            note = f"仅 Mem0 失败：{m_row['reason'][:66]}"
            ncol = (180, 83, 9)
        else:
            note = f"仅 Zep-Strict 失败：{z_row['reason'][:66]}"
            ncol = (29, 78, 216)
        draw.text((x_note + 8 * S, yy + 18 * S), note, font=f_sm, fill=ncol)

    draw.rounded_rectangle([28 * S, 804 * S, 2172 * S, 846 * S], radius=8 * S, fill=(254, 242, 242), outline=(252, 165, 165), width=S)
    draw.text((48 * S, 816 * S), "共同天花板：U001_P02（单据精确分钟 09:05→09:30）与 U002_P01（隐式迁移 4K/30ms 参数丢失）两边均失败，证明网元单据必须走确定性结构化直写。", font=f_lbl, fill=(185, 28, 28))

    final = img.resize((2200, 860), Image.Resampling.LANCZOS)
    final.save(out_path, "PNG")
    logger.info("Saved Fig 2 to %s", out_path)
    return 2200, 860


class ExcalidrawBuilder:
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
            "id": eid, "type": etype, "x": x, "y": y, "width": w, "height": h, "angle": 0,
            "strokeColor": kw.get("strokeColor", "#1e1e1e"),
            "backgroundColor": kw.get("backgroundColor", "transparent"),
            "fillStyle": "solid", "strokeWidth": kw.get("strokeWidth", 2),
            "strokeStyle": kw.get("strokeStyle", "solid"), "roughness": 0, "opacity": 100,
            "groupIds": [], "frameId": None, "roundness": kw.get("roundness", {"type": 3}),
            "seed": self.rng.randint(100000, 2000000000), "version": 1,
            "versionNonce": self.rng.randint(100000, 2000000000), "isDeleted": False,
            "boundElements": None, "updated": 1763950000000, "link": None, "locked": False,
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
            "text": text, "fontSize": font_size, "fontFamily": 3, "textAlign": "left",
            "verticalAlign": "top", "containerId": None, "originalText": text, "lineHeight": 1.38,
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
            "mimeType": "image/png", "id": fid, "dataURL": f"data:image/png;base64,{b64}",
            "created": 1763950000000, "lastRetrieved": 1763950000000,
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
            "type": "excalidraw", "version": 2,
            "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin/releases/tag/2.0.0",
            "elements": self.elements,
            "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
            "files": self.raw_files,
        }

    def build_obsidian_md(self) -> str:
        header = """---

excalidraw-plugin: parsed
tags: [excalidraw, agent-memory, zep, mem0, graph-vs-vector, strict-paper-experiment]

---
==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠==


# Excalidraw Data

## Text Elements
"""
        txt_block = "\n\n".join(f"{txt} ^{eid}" for eid, txt in self.text_entries)
        emb_block = "\n\n".join(f"{fid}: {target}" for fid, target in self.embedded_files)
        md_json = {
            "type": "excalidraw", "version": 2,
            "source": "https://github.com/zsviczian/obsidian-excalidraw-plugin/releases/tag/2.0.0",
            "elements": self.elements,
            "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
            "files": {},
        }
        return (
            header + txt_block + "\n\n## Embedded Files\n" + emb_block
            + "\n\n%%\n## Drawing\n```json\n" + json.dumps(md_json, ensure_ascii=False, indent=2) + "\n```\n%%\n"
        )


def main() -> None:
    os.makedirs(ASSETS_DIR, exist_ok=True)
    with open(LITE_JSON, encoding="utf-8") as f:
        lite = json.load(f)
    with open(STRICT_JSON, encoding="utf-8") as f:
        strict = json.load(f)

    fig0_name = "graph_vs_vector_fig0_mechanism_and_structure.png"
    fig1_name = "graph_vs_vector_fig1_topology_compare.png"
    fig2_name = "graph_vs_vector_fig2_benchmark_bars.png"
    fig0_path = os.path.join(ASSETS_DIR, fig0_name)
    fig1_path = os.path.join(ASSETS_DIR, fig1_name)
    fig2_path = os.path.join(ASSETS_DIR, fig2_name)
    render_fig0_mechanism_and_structure(fig0_path)
    render_fig1_accuracy_and_cost(lite, strict, fig1_path)
    render_fig2_case_matrix(lite, strict, fig2_path)

    eb = ExcalidrawBuilder()
    W = 2260

    eb.add_rect(40, 30, W, 134, stroke="#343a40", bg="#f8f9fa", sw=2.6)
    eb.add_text(72, 48, "记忆管理建图与否实证笔记 · Mem0 (扁平向量) 与 Zep / Graphiti (双时态图谱) 全面对照", font_size=30, color="#1e1e1e", w=2180)
    eb.add_text(
        72, 98,
        "覆盖：存储形态与机制差异 + 严格原论文复现版实测（V2 3 用户 38 条事件 · 11 道探针 · qwen3.8-flash + text-embedding-v4）+ 联接 Agent 落地方案",
        font_size=18, color="#495057", w=2180
    )

    bw = 734
    badges = [
        ("核心区别 · 不是图库对比向量库，而是三处机制取舍", "两边都用向量相似度；真正分水岭在于：是否保留底层 Episode 溯源、冲突时覆写删旧还是双时态截断、以及是否按共享实体建跨跳关联。", "#1d4ed8", "#eff6ff"),
        ("实测结论 · 单用户场景下两者全面打平（72.7%）", "严格按原论文复现后，Mem0 与 Zep-Strict 总通过率（72.7%）、需记忆难题（60%）与写入耗时（~140s）全面打平；Zep 不滤失效边则掉至 63.6%。", "#15803d", "#f0fdf4"),
        ("共同天花板 · 纯 LLM 抽取难以无损保真精确单据", "精确单据分钟时间平移（09:05→09:30）与隐式迁移精确参数（4K/30ms 丢失）两边均失败，证明网元单据必须走确定性结构化直写。", "#b91c1c", "#fef2f2"),
    ]
    for i, (t, b, sc, bg) in enumerate(badges):
        eb.add_card(40 + i * (bw + 29), 188, bw, 168, t, b, stroke=sc, bg=bg, title_color=sc)

    # 模块一：实际存储形态与写入/更新/检索机制区别
    eb.add_rect(40, 384, W, 1016, stroke="#343a40", bg="#ffffff", sw=2.0)
    eb.add_text(72, 404, "一、建图与扁平向量的实际区别：同一用户数据怎么存？写入、更新与检索怎么跑？", font_size=24, color="#1e1e1e", w=2180)
    eb.add_image(70, 448, 2200, 940, fig0_path, fig0_name)

    # 模块二：4 组严格原论文版实测准确率与成本账单
    eb.add_rect(40, 1428, W, 896, stroke="#343a40", bg="#ffffff", sw=2.0)
    eb.add_text(72, 1448, "二、4 组严格原论文版实测准确率与真实 Token / 延迟成本账单", font_size=24, color="#1e1e1e", w=2180)
    eb.add_image(70, 1492, 2200, 820, fig1_path, fig1_name)

    # 模块三：11 道 V2 探针逐题通过矩阵
    eb.add_rect(40, 2352, W, 936, stroke="#343a40", bg="#ffffff", sw=2.0)
    eb.add_text(72, 2372, "三、11 道 V2 探针逐题通过矩阵与共同天花板根因定位（对齐表 2 × 表 3 × 表 4）", font_size=24, color="#1e1e1e", w=2180)
    eb.add_image(70, 2416, 2200, 860, fig2_path, fig2_name)

    # 模块四：深度复盘
    eb.add_rect(40, 3316, W, 380, stroke="#343a40", bg="#f8f9fa", sw=2.0)
    eb.add_text(72, 3338, "四、深度复盘：建图相对扁平向量的真实优势与边界在哪里？", font_size=24, color="#1e1e1e", w=2180)
    cw = 724
    analysis_cards = [
        ("1. 单用户图谱的真实长相：浅星型结构",
         "• 20 用户数据与 V2 试点均证实：单用户图平均 11~18 节点、10~19 边，72%~76% 的边直接挂在 User 节点上（浅星型），并非复杂多跳网。\n"
         "• 因此单用户日常补全中，Zep-Strict 与 Mem0 准确率完全打平（72.7%），建图本身不产生代差优势。\n"
         "• 只有当多用户共享基站小区（Cell）与标准应用（App）做群体排障时，图才真正长出多跳网络骨架。",
         "#1d4ed8", "#ffffff"),
        ("2. Zep 建图真正有价值的 3 个基因",
         "• 基因① 双时态区间 [t_valid, t_invalid)：保留历史演进与 TTL 到期自动回退（如 5 天出差规则），前提是独立冲突裁决 + 查询时间窗过滤。\n"
         "• 基因② 情节溯源 episodes[]：同名边自动合并计数，能区分单次偶发与 >=N_min 长期稳定习惯。\n"
         "• 基因③ 三路 RRF 混合检索：向量 + BM25 + BFS 融合对精确关键词（如私有简称“腾会”）召回更稳。",
         "#15803d", "#ffffff"),
        ("3. 纯 LLM 建图与纯向量共同的 3 个硬伤",
         "• 硬伤① 精确数值与分钟时刻失真：网元单据的 09:05、4K/30ms 经 LLM 文本改写后极易压成 09:00 或被套餐上限覆盖（U001_P02 / U002_P01 双双失败）。\n"
         "• 硬伤② 否定与隐含前提易丢：三元组擅长正向关系 A→B，不擅长表达“取消一个库里尚未建出的规则”。\n"
         "• 硬伤③ 写入重且耗时高：完整原论文流水线 38 条写入均耗时 ~140s、消耗 5.7万~7.2万 Token。",
         "#b91c1c", "#ffffff"),
    ]
    for i, (t, b, sc, bg) in enumerate(analysis_cards):
        eb.add_card(66 + i * (cw + 18), 3388, cw, 286, t, b, stroke=sc, bg=bg, title_color=sc)

    # 模块五：联接 Agent 最终落地方案
    eb.add_rect(40, 3724, W, 330, stroke="#15803d", bg="#f0fdf4", sw=2.4)
    eb.add_text(72, 3748, "五、联接 Agent 长期记忆最终落地方案：确定性结构化双时态槽位表 + 向量原文短句库（按需挂接共享枢纽图）", font_size=24, color="#15803d", w=2180)
    eb.add_card(
        70, 3800, 1085, 232,
        "轨道 A · 确定性结构化双时态槽位表（接管全部网元单据与状态机）",
        "• 网元单据零 LLM 直写：精确留存毫秒/分钟时间戳（彻底解决 U001_P02）、精确画质/时延参数（彻底解决 U002_P01）、顺畅/卡顿运行状态与被动弱覆盖标记；\n"
        "• 吸收 Zep 最值钱基因：每条偏好按 (app, sub_service, scope) 隔离，确定性维护 [t_valid, t_invalid)、ttl_days 到期自动回退与 source_episodes[] 频次计数（>=N_min 晋升），查当前态默认硬过滤失效项，零 LLM 冲突漏判、零 Token 写入成本。",
        stroke="#15803d", bg="#ffffff", title_color="#15803d"
    )
    eb.add_card(
        1185, 3800, 1085, 232,
        "轨道 B · 向量语义短句库 + 程序记忆库（兜底对话表达与演进多跳）",
        "• 对话侧自然语言高保真：用轻量向量库留存用户私有简称（expression）、改口撤销原话与假设咨询上下文，结合 BM25 + 向量 RRF 召回；\n"
        "• 程序记忆独立三段式管理：沉淀闭合式澄清策略与弱覆盖避错规则，显式携带 forbidden_boundary（如 5G 稳定覆盖禁用），避免三元组压扁多轮交互细节；\n"
        "• 演进扩展：当业务进入基站小区级群体排障时，仅以共享 Cell / App 为枢纽建轻量邻接图索引。",
        stroke="#1d4ed8", bg="#ffffff", title_color="#1d4ed8"
    )

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(eb.build_obsidian_md())
    with open(OUT_RAW, "w", encoding="utf-8") as f:
        json.dump(eb.build_raw_json(), f, ensure_ascii=False, indent=2)

    logger.info("Updated clean strict-paper Obsidian note: %s", OUT_MD)


if __name__ == "__main__":
    main()

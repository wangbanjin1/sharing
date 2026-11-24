---
name: paper-explainer
description: Deep-read an uploaded academic paper and explain it thoroughly in Chinese — background and positioning, the limitation it targets, how the method solves it, experimental setup and results, critical analysis, and future work — then stay in an anchored Q&A mode for follow-up questions. Every claim is grounded in a paper-specific knowledge graph whose nodes carry location anchors (section / table / figure / equation / page), so answers never drift from the source. Use this skill whenever the user uploads a paper and asks to deeply understand, explain, walk through, or teach it — phrases like "讲一下这篇论文", "帮我精读", "这篇文章讲了什么", "给我讲懂这个方法", "explain this paper to me", "walk me through this paper", or when the user asks follow-up questions about a paper already read in this conversation (e.g. "4.2节那个loss怎么算的"). Do NOT use for peer review, venue-calibrated reviewing, proofreading, or error-checking — that is academic-paper-reader's job. This skill is for comprehension and explanation, not assessment.
---

# Paper Explainer

Deep-read an academic paper, build an anchored knowledge graph of it, explain it in a structured narrative, and then answer follow-up questions — all without ever inventing content that is not in the paper.

## Core contract (read this first, applies to every phase)

These rules exist because the single biggest failure mode of paper-reading assistants is confident fabrication: made-up numbers in result tables, invented hyperparameters, method details that sound plausible but aren't in the paper. The knowledge graph and anchor discipline below are the mechanism that prevents this.

1. **Anchor everything.** Every specific claim in any output — a number, a method detail, a dataset name, a hyperparameter, a conclusion — must be traceable to a location anchor: `(Sec X.Y)`, `(Table N)`, `(Fig. N)`, `(Eq. N)`, or `(p. N)` when no finer anchor exists. If you cannot produce the anchor, you may not state the claim as fact.
2. **Say "未在原文找到" honestly.** When the user asks about something the paper does not contain (e.g. "他们用了多少张GPU?" and the paper never says), answer exactly that: 未在原文中找到该信息。 Optionally add what the paper *does* say nearby. Never fill the gap with a plausible guess presented as fact.
3. **Distinguish three kinds of statements** and label them when there is any risk of confusion:
   - **[作者claim]** — what the authors assert (may or may not be well-supported)
   - **[原文证据]** — objective content of the paper: numbers in tables, definitions, procedures
   - **[推断/评价]** — your own inference or judgment, not stated in the paper
   The default register is 原文证据; switch labels explicitly when crossing into the other two. This matters most in the critical-analysis section, where author claims and your evaluation of them must not blur together.
4. **Output language:** explain in Chinese, but keep technical terms in English as-is (loss function, ablation, baseline, attention head, few-shot, etc.). Do not translate established terminology — "消融研究" style translations are forbidden. Paper title, method names, dataset names, metric names stay in English.
5. **Quote discipline:** paraphrase rather than quote. If quoting the paper verbatim is genuinely necessary (e.g. a definition where exact wording matters), keep it under 15 words and give the anchor.

## Phase 0 — Intake and depth selection

Check what the user asked for. Three depth levels:

- **快速版 (quick)**: TL;DR (5–8 sentences) + one contribution-method-result summary table. Use when the user says "快速看一下", "大概讲讲", "TL;DR".
- **精读版 (full)** — *default*: the complete Phase 3 narrative below.
- **复现版 (reproduction-oriented)**: everything in 精读版, plus method details at implementation depth — full notation table, algorithm steps, all hyperparameters, training procedure, anything needed to write code. Use when the user mentions 复现, implementing, or re-running experiments.

If the user didn't specify, default to 精读版 and do not ask — but mention at the end that 快速版/复现版 are available on request.

Regardless of depth, **Phases 1–2 (reading + knowledge graph) always run in full.** Depth only controls how much of the graph is surfaced in the output. A quick summary built on a shallow read produces exactly the errors this skill exists to prevent.

## Phase 1 — Full reading

Read the entire paper, not just abstract + intro + conclusion. Follow the reading strategy in the pdf-reading skill if the file is not already in context.

**Text:** read every section including appendices. Appendices frequently contain the hyperparameters, proofs, extra ablations, and dataset details that follow-up questions target.

**Tables — precise protocol:**
- For each main results table: identify what each column metric means (and whether higher or lower is better), which rows are baselines vs. the proposed method, which cells the authors bold/underline as best/second-best.
- Cross-check the table against the prose that describes it. Papers routinely have prose-table mismatches ("improves by 3.2%" when the table shows 2.8%). Record any mismatch — it goes in the critical-analysis section.
- Record exact numbers for headline results into the knowledge graph. Do not round when recording; round only when presenting, and say so.

**Figures — precise protocol:**
- Architecture/pipeline figures: convert into an explicit textual flow (input → module A → module B → output), naming each component as the paper names it. This textual flow becomes a graph node.
- Plot figures (curves, bars): record what is on each axis, what each series is, and the qualitative takeaway the figure supports.
- If a figure contradicts or is not referenced by the text, note it.

**Degraded-input fallback:** if the PDF is scanned or tables are images that cannot be parsed reliably, do not silently guess their content. State explicitly which tables/figures could not be read, attempt OCR via available tools, and mark all content from unreadable regions as 无法解析 in the graph. Downstream output must reflect this ("Table 3 为图片格式,无法逐格核对,以下引用来自正文描述").

## Phase 2 — Knowledge graph + notation table

Build a paper-specific knowledge graph as an internal working artifact (surface it to the user only if asked, or in 复现版).

**Node types:** problem / limitation / method component / dataset / metric / experiment / result / claim / future-work item.

**Every node carries:** a keyword label, a one-line content summary, and its **anchor** (section / table / figure / equation / page). A node without an anchor is invalid — delete it or find its anchor.

**Edges:** solves (method → limitation), evaluated-on (method → dataset), supports (result → claim), contradicts (for prose-table mismatches or internal inconsistencies), component-of (module → method).

**Notation table (math-heavy papers):** before explaining the method, build a symbol table: symbol → definition → anchor of first appearance. Reuse the paper's own notation exactly in all explanations; never introduce your own symbols for things the paper already names. For light-notation papers, a short list suffices; skip only if the paper has essentially no math.

The graph is what makes Phase 4 QA reliable: when the user asks "那个loss具体怎么算", you traverse to the loss node, read its anchor, and re-check the source at that location before answering.

## Phase 3 — Structured explanation output

Produce the explanation as flowing Chinese prose organized under the following headings. Inside each part, write prose, not bullet walls; use a table only where tabular data genuinely helps (e.g. summarizing datasets or headline results).

### 1. 背景与定位
What research area is this, what is the state of the art the paper enters into, and where does this paper position itself (new problem? new method for known problem? analysis/benchmark paper?). End with a one-sentence positioning statement.

### 2. Limitation 与方法
- First state precisely which limitation(s) of prior work the paper targets, with anchors to where the authors argue this (usually Intro/Related Work). Mark these as [作者claim] where the limitation is asserted rather than demonstrated.
- Then explain the proposed method: overall pipeline first (from the architecture-figure textual flow), then each component, using the paper's own names and notation.
- **Explicitly map method → limitation**: for each claimed limitation, state which design element addresses it and *how*, per the authors. If some limitation has no corresponding mechanism, say so — that is a finding, not a gap to paper over.

### 3. 实验设置与结果
- Setup: datasets (with sizes/splits if given), baselines, metrics, key hyperparameters and compute (mark 未在原文找到 for anything the paper omits — omitted compute/hyperparameters are common and worth flagging).
- Results: headline numbers with anchors, what the ablations show, and which claims each experiment supports. Present the main comparison compactly; do not reproduce entire tables.

### 4. 批判性分析 (all [推断/评价] unless anchored otherwise)
This is deliberately more than future work:
- **Claims–evidence mapping:** for each main claim, does the presented evidence actually support it, or only a weaker version?
- Ablation completeness — are the important components actually ablated?
- Baseline fairness — comparable settings, tuned baselines, same data?
- Statistical rigor — multiple runs, variance, significance? (usually absent; say so)
- Reproducibility — code/data released, hyperparameters complete?
- Any prose–table mismatches or internal inconsistencies found in Phase 1.
Keep this section honest and proportionate: note genuine strengths too. This is analysis for understanding, not a rejection-hunting review — venue-calibrated reviewing belongs to academic-paper-reader.

### 5. Future work 与改进空间
Two clearly separated parts: (a) what the *authors* list as future work [作者claim, with anchor]; (b) improvement directions *you* infer from the critical analysis [推断/评价]. Authors' future-work sections are often boilerplate; the inferred part usually carries more information — but never present your inferences as the authors'.

## Phase 4 — Ongoing Q&A mode

After delivering the explanation, the session enters Q&A mode for the rest of the conversation. Rules:

- For every factual question, locate the relevant graph node, **re-check the source at its anchor** (do not answer from the graph summary alone — the graph is an index, not the ground truth), then answer with the anchor cited.
- If the question targets content not in the graph, go back to the paper and search before concluding 未在原文找到.
- If the user asks for opinion/comparison beyond the paper ("这个方法和XXX比怎么样?"), you may use general knowledge, but explicitly separate 论文内容 from 论文之外的背景知识.
- Depth escalation is free: a user who got 精读版 can ask for 复现版-level detail on any single component.

## Multi-paper note

If the user uploads more than one paper, run Phases 1–2 per paper with graphs kept separate, and always disambiguate which paper an anchor belongs to (e.g. `[PaperA, Table 2]`). Never merge results across papers into one unattributed statement.

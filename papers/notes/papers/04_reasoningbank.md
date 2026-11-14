# 4. ReasoningBank (`arXiv:2509.25140`, Google Cloud AI Research & UIUC Sep 2025) — 精读与源码对账笔记

- **论文信息**：Siru Ouyang, Jun Yan, I-Hung Hsu, Yanfei Chen, Ke Jiang, Zifeng Wang, Rujun Han, Long T. Le, Samira Daruki, Xiangru Tang, Vishy Tirumalashetty, George Lee, Mahsan Rofouei, Hangfei Lin, Jiawei Han, Chen-Yu Lee, Tomas Pfister (Google Cloud AI Research / UIUC / Yale). *ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory*. `arXiv:2509.25140v2`, 29 Sep 2025.
- **本地归档路径**：
  - PDF 原文：[ReasoningBank_2025.pdf](file:///D:/coding/sharing/papers/procedural_memory/ReasoningBank_2025.pdf)（同 [2509.25140.pdf](file:///D:/coding/sharing/papers/procedural_memory/2509.25140/pdf/2509.25140.pdf)）
  - Markdown 转换稿：[2509.25140.md](file:///D:/coding/sharing/papers/procedural_memory/2509.25140/2509.25140.md)
  - LaTeX 源码：`D:\coding\sharing\papers\procedural_memory\2509.25140\source\`（含 `sections/01_introduction.tex` 至 `05_analysis.tex`、`appendix.tex` 及全部 Prompt 原图 `figures/*.pdf`）
  - 开源仓库克隆：`D:\coding\sharing\papers\repos\reasoning-bank`（`https://github.com/google-research/reasoning-bank`）
- **在 P0–P3 矩阵中的定位**：**`P0` 程序性/推理经验记忆主干（从成功与失败双轨迹蒸馏推理策略 + 记忆感知测试时扩展 `MaTTS` 代表）** —— 打破以往经验记忆仅存储原始轨迹（`Synapse`）或仅归纳成功工作流（`AWM`）的局限，通过无监督 `LLM-as-a-Judge` 自评信号从**成功轨迹（正向有效策略）与失败轨迹（反向避坑护栏）**中双向蒸馏三段式结构化推理单元 `{title, description, content}`，并首次将测试时计算扩展（Test-Time Scaling）与经验记忆闭环耦合为 `MaTTS`（并行多轨迹自对比 + 串行多步自精炼）。

---

## 4.1 背景定位与针对的核心缺陷 (Background & Targeted Limitations)

1. **流式无标签测试时学习（Streaming Test-Time Learning）中的“经验遗忘与错误复现”**：
   - 真实部署的持久化 Agent 面对连续到达的任务序列 $\mathcal{Q} = \{q_1, q_2, \dots, q_N\}$，在测试阶段没有任何外部 Ground-Truth 反馈标签（`Sec 3.1`, `03-method.tex` / `2509.25140.md:55`）。若每次孤立求解，Agent 会反复踩入相同的执行陷阱、丢弃已探索出的领域洞察，缺乏跨任务自我演进能力（`Sec 1`, `2509.25140.md:22`）。
2. **既有经验记忆（Raw Trajectories 与 Success-Only Workflows）的两大结构性短板**：
   - **粒度过低、缺乏高层可迁移推理抽象**：以 `Synapse`（Zheng et al., 2024）为代表的轨迹记忆直接拼接历史原始轨迹 $(o_{0:t}, a_{0:t})$，充斥页面 DOM 噪声；以 `AWM`（Wang et al., 2025）为代表的工作流记忆硬性提取多步动作序列子例程（Action Sub-routines），强依赖固定动作空间与相似页面结构，在跨网站/跨领域（如 `WebArena-Multi`）或开放式动作空间（如 `SWE-Bench` Bash 环境）下严重退化甚至无法适用（`Sec 1`, `2509.25140.md:24`；`Appendix B.2 Footnote 8`, `appendix.tex:139`）。
   - **盲目丢弃失败轨迹（Survivorship Bias）**：`Synapse` 与 `AWM` 仅从成功案例中构建记忆；若把失败轨迹直接塞入 `AWM`，其成功率反而从 `44.4%` 跌至 `42.2%`（`Sec 5`, `2509.25140.md:258`）。大量失败尝试中蕴含的“为什么错、如何提前规避”的反事实信号被完全浪费。
3. **传统测试时扩展（Vanilla Test-Time Scaling, TTS）与记忆机制割裂**：
   - 现有 Agent TTS（如 Best-of-$N$ 采样、束搜索）仅在单题内部盲目撒网，没有利用历史记忆引导探索方向；反之，就算简单把多条采样轨迹各自独立转成记忆条目（Vanilla TTS + Memory，见论文 `Fig. 3(a)`），也完全忽略了**同一问题下多条成功/失败轨迹天然构成的强对比信号（Self-Contrast Signal）**（`Sec 3.3`, `2509.25140.md:74`）。

---

## 4.2 核心架构：ReasoningBank 闭环与 MaTTS 协同扩展 (`Sec 3`, `2509.25140.md:47-88`)

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│             ReasoningBank 流式闭环自演进与 MaTTS (Memory-aware TTS) 架构                  │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│  Step 1: 记忆检索与显式门控注入 (Memory Retrieval & Explicit Gating)                      │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 新任务查询 q_i ──► gemini-embedding-001 (3072 维, 源码加 Instruct 前缀)            │  │
│  │               ──► 检索 Top-k 历史任务经验 (默认 k=1, 取其关联的 ≤3 条 Memory Items) │  │
│  │               ──► 注入 Agent System Prompt，强制要求每步 <think> 先显式讨论：       │  │
│  │                   "explicitly discuss if you want to use each memory item or not" │  │
│  └─────────────────────────────────────────┬─────────────────────────────────────────┘  │
│                                            ▼                                            │
│  Step 2: 环境交互与 MaTTS 深度经验扩展 (Interaction & Memory-Aware Test-Time Scaling)    │
│  ┌─────────────────────────────────────────┴─────────────────────────────────────────┐  │
│  │ • 基础单轨模式 (k=1): ReAct 循环生成单条轨迹 τ = (<think>_t, <action>_t)_{t=1..T}  │  │
│  │ • MaTTS 并行扩展 (Parallel Scaling, k=5):                                          │  │
│  │     在同一记忆引导下并发采样 k 条轨迹 {τ^(1)..τ^(k)} ──► 多轨迹自对比 (Self-Contrast)│  │
│  │ • MaTTS 串行扩展 (Sequential Scaling, k=5):                                        │  │
│  │     单轨迹完成后执行 k 步自检修正 (Self-Refinement: First-time / Follow-up Check) │  │
│  └─────────────────────────────────────────┬─────────────────────────────────────────┘  │
│                                            ▼                                            │
│  Step 3: 无真值自评与双通道策略蒸馏 (Self-Judged Dual-Path Memory Extraction)            │
│  ┌─────────────────────────────────────────┴─────────────────────────────────────────┐  │
│  │ LLM-as-a-Judge (Temp=0.0): 输入 (q_i, τ, 最终页面状态 cap, 回复) ──► Thoughts +    │  │
│  │                            二元判定 Status ∈ {Success, Failure}                   │  │
│  │   ├─► 若 Success ──► SUCCESSFUL_SI (Temp=1.0): 分析成功原因，提取 ≤3 条有效推理策略 │  │
│  │   └─► 若 Failure ──► FAILED_SI (Temp=1.0): 反思失败根因，提取 ≤3 条预防性避坑策略   │  │
│  │   [MaTTS 并行模式直接输入 k 条混合轨迹调用 PARALLEL_SI 一次性自对比提取 ≤5 条策略]  │  │
│  │                                                                                   │  │
│  │ 三段式记忆单元 Schema (Markdown / JSON):                                           │  │
│  │   • Title:       核心策略或推理模式的简短标识                                      │  │
│  │   • Description: 一句话概述该策略的适用/不适用边界 ("when or when NOT to use")     │  │
│  │   • Content:     1~3 句（MaTTS 1~5 句）可跨站迁移的抽象推理步骤/核查准则（禁含字面量）│  │
│  └─────────────────────────────────────────┬─────────────────────────────────────────┘  │
│                                            ▼                                            │
│  Step 4: 记忆固化 (Memory Consolidation) ──► 直接追加写入 JSONL 记忆池与向量缓存         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1. 三段式推理记忆模式（Memory Schema，`Sec 3.2`, `2509.25140.md:68`；`prompts/memory_instruction.py:15-61`）
每条从历史经验中提炼出的记忆条目（Memory Item）严格剥离具体网站域名、商品名或硬编码 DOM 元素 ID，由三个结构化字段组成：
1. **`Title`（标题）**：概括核心推理模式或操作策略的简短标识符（例如：`User-Specific Information Navigation`、`Category Filter Prioritization`）。
2. **`Description`（适用边界描述）**：一句话总结该记忆条目的触发条件与禁用边界（论文正文写“一句话摘要”，开源代码 `memory_instruction.py:34, 58, 87` 明确强化为：`<one sentence summary describing when or when NOT to use the memory item>`）。
3. **`Content`（可迁移推理内容）**：用 1~3 句话（并行扩展 `PARALLEL_SI` 为 1~5 句话）记录经验证的推理步骤、决策依据或失败预防护栏（Guardrails）。

### 2. 三阶段闭环集成流程（`Sec 3.2`, `2509.25140.md:70`；`Appendix A.1–A.2`, `appendix.tex:10-85`）
1. **记忆检索与显式推理门控（Memory Retrieval & Explicit Gating）**：
   - 面对新查询 $q_i$，使用 `gemini-embedding-001`（源码设置 `output_dimensionality=3072`，`memory_management.py:50, 78`）在历史任务查询池中按余弦相似度检索最相近的 Top-$k$ 个历史任务经验（**默认 $k=1$**，即只取最相似的 1 个历史任务所产出的 $\le 3$ 条记忆项；`Sec 5 / Appendix C.1` 消融证明 $k=1$ 显著优于 $k=2,3,4$）。
   - 将召回的记忆条目注入 Agent 的系统提示词（`WebArena/agents/legacy/agent.py:134-138`），并附加强制性每步反思指令（`appendix.tex:66-68`）：
     > *"Below are some memory items that I accumulated from past interaction from the environment that may be helpful to solve the task. You can use it when you feel it's relevant. **In each step, please first explicitly discuss if you want to use each memory item or not, and then take action.**"*
2. **无监督自评与双通道记忆抽取（Self-Judged Dual-Path Extraction）**：
   - **观察状态压缩近似（Footnote 1，`2509.25140.md:515`；`induce_memory.py:70-76`）**：由于原始网页无障碍树（Accessibility Tree）过长，在构造供记忆抽取的轨迹 $\tau$ 时，系统用 Agent 每步的思考与动作序列 `<think>\n{t}\n</think>\n<action>\n{a}\n</action>` 近似替代完整状态转移序列 $(o_{0:t}, a_{0:t})$。
   - **LLM-as-a-Judge 代理判分（`Fig. 6`, `llm-judge.pdf`）**：使用与 Agent 相同的骨干模型（温度设为 $0.0$），结合用户意图 `intent`、动作历史 `trajectory`、最终网页状态 `cap` 与回复，将任务归入信息检索（Information seeking）、页面导航（Site navigation）或内容修改（Content modification）三类之一，输出两行结果：`Thoughts: <reasoning>` 与 `Status: "success" or "failure"`。
   - **双分支条件蒸馏（`Fig. 5`, `reasoningbank_si.pdf`；温度设为 $1.0$，每次最多提取 3 条）**：
     - 当判定为 `Success` 时，调用 `SUCCESSFUL_SI`：要求模型“先思考轨迹为何成功，再总结可迁移的成功推理策略”；
     - 当判定为 `Failure` 时，调用 `FAILED_SI`：要求模型“先反思并定位轨迹失败的根本原因，再提炼未来避免同类错误的预防性教训或恢复策略”。
3. **极简记忆固化（Memory Consolidation）**：
   - 将新提取的记忆条目与当前任务查询 $q_i$、原始轨迹一并追加写入 JSONL 记忆库（`appendix.tex:72-85`），不做复杂的删除或图合并，从而纯粹隔离并验证“高质量推理记忆内容”本身带来的增益。

### 3. 记忆感知的测试时扩展（MaTTS: Memory-Aware Test-Time Scaling，`Sec 3.3`, `2509.25140.md:72-88`；`Fig. 3 & Fig. 7`）
作者指出了简单结合 TTS 与记忆（**Vanilla TTS**，`Fig. 3(a)`：对 $k$ 条采样轨迹分别独立调用单轨迹抽取器，塞入记忆库）的缺陷——忽略了同一任务下不同探索路径之间的对比信息。为此提出 **`MaTTS`** 的两种实例化方案（扩展因子记为 $k$）：
1. **并行扩展（Parallel Scaling，`Fig. 3(b)` & `Fig. 7 Left`）**：
   - 在已检索记忆项的引导下，对同一查询 $q_i$ 并行生成 $k$ 条探索轨迹 $\{\tau^{(1)}, \dots, \tau^{(k)}\}$（其中既有成功也有失败）。
   - **跨轨迹自对比聚合（Self-Contrast Reasoning，`PARALLEL_SI`）**：将全部 $k$ 条轨迹一次性输入抽取模型，无需依赖外部二元裁判，直接要求模型横向对比：“为什么部分轨迹成功而另一部分失败？找出跨轨迹一致导向成功的模式，并从失败轨迹中识别低效或错误动作以制定预防策略”，从全部 $k$ 条轨迹中汇总提炼至多 **5 条** 高可靠记忆项。
2. **串行扩展（Sequential Scaling，`Fig. 3(c)` & `Fig. 7 Right`）**：
   - 在单条轨迹首次完成后，不立即结束，而是依次注入 `First-time Check Instruction`（*“仔细重新检查之前的推理步骤和动作，特别注意是否使用了页面上的正确元素、回复是否完整回答了用户查询，若有不一致请修正，若无误请确认最终答案”*）和后续 $k-2$ 轮 `Follow-up Check Instruction`（*“Let's check again.”*）。
   - 将修正过程中的中间反思笔记与纠错动作一并纳入轨迹，从中提炼捕获了“试错–自我纠正”洞察的记忆条目。

---

## 4.3 实验设置与完整数据对账 (Experimental Setup & Complete Results)

作者在三大权威交互式 Agent 基准上进行了系统评测：**WebArena**（684 个任务，排除故障的 Map 子集，涵盖 Shopping 187、Admin 182、Gitlab 180、Reddit 106、Multi 跨站 29，最大步数限制 30 步）、**Mind2Web**（1,341 个任务，含 Cross-Task 252、Cross-Website 177、Cross-Domain 912）以及 **SWE-Bench-Verified**（500 个经人工验证的真实 GitHub 仓库 Issue 修复任务，采用 `mini-SWE-Agent` 纯 Bash 环境）。对比基线包括：**`No Memory`**、**`Synapse`**（原始成功轨迹作上下文）与 **`AWM`**（归纳成功动作工作流）（`Sec 4.1`, `04-experiments.tex:4-12`；`Appendix B`, `appendix.tex:103-141`）。

### 1. 主实验一：`WebArena` 五大子集与三大骨干模型完整对比（对应论文 `Table 1`，`04-experiments.tex:13-53`）
- **指标说明**：`SR`（Success Rate $\uparrow$，百分比成功率）衡量有效性；`Step`（Average Steps $\downarrow$，平均交互步数）衡量执行效率。`+MaTTS` 采用并行扩展（$k=5$，汇报单轨平均质量 `Pass@1`）。

| 骨干模型与记忆方法 (`Model / Method`) | Shopping (`187`) `SR` / `Step` | Admin (`182`) `SR` / `Step` | Gitlab (`180`) `SR` / `Step` | Reddit (`106`) `SR` / `Step` | Multi (`29`) `SR` / `Step` | **Overall (`684`) `SR` $\uparrow$ / `Step` $\downarrow$** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`Gemini-2.5-flash`** | | | | | | |
| No Memory | 39.0 / 8.2 | 44.5 / 9.5 | 33.9 / 13.3 | 55.7 / 6.7 | 10.3 / 10.0 | 40.5 / 9.7 |
| Synapse | 40.6 / 7.0 | 45.1 / 9.1 | 35.6 / 13.0 | 59.4 / 6.5 | 10.3 / 10.5 | 42.1 / 9.2 |
| AWM | 44.4 / 7.0 | 46.7 / 8.8 | 37.2 / 13.2 | 62.3 / 6.1 | 3.4 / **7.7** | 44.1 / 9.0 |
| **ReasoningBank** ($k=1$) | **49.7** / **6.1** | **51.1** / **8.2** | **40.6** / **12.3** | **67.0** / **5.6** | **13.8** / 8.8 | **48.8** (+8.3) / **8.3** (-1.4) |
| **ReasoningBank + MaTTS** ($k=5$, Pass@1) | **53.0** / 6.3 | **53.8** / **7.6** | **42.8** / **11.9** | **70.8** / **5.4** | **17.2** / **8.0** | **51.8** (+11.3) / **7.9** (-1.8) |
| **`Gemini-2.5-pro`** | | | | | | |
| No Memory | 45.5 / 7.6 | 51.1 / 8.7 | 35.0 / 11.6 | 71.7 / 6.0 | 6.9 / 8.8 | 46.7 / 8.8 |
| Synapse | 46.5 / 6.6 | 52.2 / 8.9 | 38.3 / 11.3 | 68.9 / 5.9 | 6.9 / 9.0 | 47.7 / 8.5 |
| AWM | 48.1 / 6.4 | 49.3 / 9.8 | 40.0 / 11.2 | 68.9 / 6.4 | 3.4 / 9.3 | 47.6 / 8.7 |
| **ReasoningBank** ($k=1$) | **51.9** / **6.0** | **56.6** / **7.7** | **44.4** / **9.8** | **80.2** / **5.1** | **13.8** / **8.2** | **53.9** (+7.2) / **7.4** (-1.4) |
| **ReasoningBank + MaTTS** ($k=5$, Pass@1) | **54.0** / **5.9** | **58.2** / **7.4** | **46.7** / **9.1** | **83.0** / 5.3 | **20.7** / **7.2** | **56.3** (+9.6) / **7.1** (-1.7) |
| **`Claude-3.7-sonnet`** | | | | | | |
| No Memory | 38.5 / 6.1 | 49.5 / 8.4 | 36.7 / 10.6 | 53.8 / 5.5 | 0.0 / 11.6 | 41.7 / 8.0 |
| Synapse | 39.6 / 5.8 | 50.5 / 8.5 | 38.0 / 10.0 | 53.8 / 6.1 | 0.0 / 11.8 | 42.6 / 7.9 |
| AWM | 39.6 / 7.2 | 47.8 / 9.3 | 34.6 / 10.9 | 52.8 / 7.0 | 0.0 / 12.4 | 40.8 / 8.9 |
| **ReasoningBank** ($k=1$) | **44.9** / **5.6** | **53.3** / **7.6** | **41.1** / **9.5** | **57.5** / **5.2** | **3.4** / **10.5** | **46.3** (+4.6) / **7.3** (-0.7) |
| **ReasoningBank + MaTTS** ($k=5$, Pass@1) | **47.1** / 5.8 | **55.5** / **7.4** | **43.3** / **9.4** | **60.4** / **5.0** | **10.3** / **9.1** | **48.8** (+7.1) / **7.2** (-0.8) |

> **关键发现**：在最具挑战性的跨网站迁移子集 **`Multi`** 上，死记硬背单站动作序列的 `AWM` 在三个模型上全面崩溃（在 `Gemini-2.5-flash/pro` 上从 `10.3%/6.9%` 腰斩至 `3.4%`），而提炼高层推理策略的 `ReasoningBank + MaTTS` 将 `Multi` 成功率大幅推升至 **`17.2%` / `20.7%` / `10.3%`**。

### 2. 主实验二：`Mind2Web` 三级泛化测试（对应论文 `Table 2`，`04-experiments.tex:91-118`）
- **指标说明**：`EA`（Element Accuracy $\uparrow$，元素选择准确率）、`AF1`（Action $F_1$ $\uparrow$，操作 $F_1$）、`SSR`（Step Success Rate $\uparrow$，单步成功率）、`SR`（Task Success Rate $\uparrow$，全步全对的任务成功率）。

| 骨干模型与方法 | Cross-Task (`252`) `EA` / `AF1` / `SSR` / `SR` | Cross-Website (`177`) `EA` / `AF1` / `SSR` / `SR` | Cross-Domain (`912`) `EA` / `AF1` / `SSR` / `SR` |
| :--- | :---: | :---: | :---: |
| **`Gemini-2.5-flash`** | | | |
| No Memory | 46.0 / 59.1 / 40.3 / 3.3 | 39.8 / 45.1 / 31.7 / 1.7 | 35.8 / 37.9 / 31.9 / 1.0 |
| Synapse | 47.0 / 59.5 / 41.2 / 3.5 | 40.3 / 46.0 / 32.1 / 1.9 | 36.3 / 38.5 / 32.4 / 1.1 |
| AWM | 46.3 / 56.1 / 41.0 / 3.5 | 39.1 / 42.2 / 31.7 / 2.1 | 33.3 / 36.5 / 30.1 / 0.7 |
| **ReasoningBank** | **52.1 / 60.4 / 44.9 / 4.8** | **44.3 / 52.6 / 33.9 / 2.3** | **40.6 / 41.3 / 36.6 / 1.6** |
| **`Gemini-2.5-pro`** | | | |
| No Memory | 49.3 / 60.2 / 44.4 / 3.5 | 41.2 / 49.8 / 34.8 / 3.4 | 37.9 / 37.7 / 35.0 / 1.4 |
| Synapse | 50.1 / 61.0 / 44.7 / 3.6 | 41.8 / 51.2 / 35.0 / 3.2 | 38.5 / 39.8 / 35.6 / 1.5 |
| AWM | 48.6 / 61.2 / 44.4 / 3.7 | 41.9 / 47.9 / 34.8 / 2.3 | 37.3 / 38.1 / 34.4 / 1.2 |
| **ReasoningBank** | **53.6 / 62.7 / 45.6 / 5.1** | **46.1 / 54.8 / 36.9 / 3.8** | **42.8 / 45.2 / 38.1 / 1.7** |

### 3. 主实验三：`SWE-Bench-Verified` 仓库级代码修复与 `Gemma-3-12B` 开源小模型验证（`Table 3/Wraptable` & `Table 6`，`04-experiments.tex:63-86`、`appendix.tex:211-225`）

| 评测基准与骨干模型 | 对比方法 (`Method`) | 解决率 / 成功率 (`Resolve Rate / SR %` $\uparrow$) | 平均交互步数 (`Average Steps` $\downarrow$) |
| :--- | :--- | :---: | :---: |
| **`SWE-Bench-Verified` (`500` 题, `Gemini-2.5-flash`)** | No Memory | 34.2% | 30.3 |
| | Synapse | 35.4% | 30.7 |
| | **ReasoningBank** | **38.8%** (+4.6%) | **27.5** (-2.8 步) |
| **`SWE-Bench-Verified` (`500` 题, `Gemini-2.5-pro`)** | No Memory | 54.0% | 21.1 |
| | Synapse | 53.4% | 21.0 |
| | **ReasoningBank** | **57.4%** (+3.4%) | **19.8** (-1.3 步) |
| **`WebArena-Shopping` (`187` 题, 开源 `Gemma-3-12B-Instruct`)** | No Memory | 17.1% | 13.7 |
| | Synapse | 16.0% | 14.0 |
| | AWM | 21.4% | 12.5 |
| | **ReasoningBank** | **24.1%** (+7.0%) | **11.8** (-1.9 步) |

### 4. 核心消融、效率拆解与 Token 开销账本（`Sec 4.3–5` & `Appendix C`）
1. **成功步数与失败步数拆解（`Table 3 in Sec 5`, `2509.25140.md:272-286`）**：
   - `ReasoningBank` 的步数下降并非因为“提早放弃失败任务”，恰恰相反，**在成功解决的实例上步数削减最为显著**：在 Shopping（`6.8 -> 4.7` 步，削减 `30.9%`）、Admin（`8.4 -> 7.0` 步）、Gitlab（`8.6 -> 7.6` 步）、Reddit（`6.1 -> 5.0` 步）上，Agent 借助历史推理策略直接走上正确路径，省去了盲目试探。
2. **失败轨迹的价值消融（`Sec 5 Fig. ablation_failure`, `2509.25140.md:254-259`）**：
   - 在 `WebArena-Shopping`（`Gemini-2.5-flash`）上，若**仅用成功轨迹（Success-only）**，Synapse / AWM / ReasoningBank 的成功率分别为 `40.6%` / `44.4%` / `46.5%`；
   - 当**同时纳入成功与失败轨迹（Success + Failure）**时，Synapse 仅微升至 `41.7%`，AWM 反而因把错误动作序列当成工作流而跌至 `42.2%`（`-2.2%`），唯有 `ReasoningBank` 跃升至 **`49.7%`**（`+3.2%`）。
3. **LLM-as-a-Judge 裁判噪声鲁棒性（`Sec 5 Fig. judge_accuracy`, `2509.25140.md:260-266`）**：
   - `Gemini-2.5-flash` 作为无监督裁判在 `WebArena-Shopping` 上的真实二元判别准确率为 **`72.7%`**；人为向 Ground-Truth 标签注入翻转噪声模拟 `50% ~ 100%` 的裁判准确率发现，在 `70% ~ 90%` 的合理准确率区间内，`ReasoningBank` 的最终任务成功率高度稳定，证明反思式策略蒸馏对裁判误判具备天然容错性。
4. **检索经验数量 $k$ 消融与单任务 Token 成本账本（`Appendix C.1–C.2`, `appendix.tex:155-196`）**：
   - **检索数量 Top-$k$ 消融**：在 `WebArena-Shopping` 上，无记忆为 `39.0%`，召回 **$k=1$ 个历史经验时达到峰值 `49.7%`**；继续增大 $k=2, 3, 4$ 时，成功率依次回落至 `46.0%`、`45.5%`、`44.4%`——证明**过多经验会引入冲突策略与上下文噪声，记忆的相关性与精炼度远比数量重要**。
   - **单任务全链路平均 Token 消耗对比（`Table 5 / table: inference_cost`）**：

| 方法 (`Method`) | 动作生成 (`Action Generation`) | 自评裁判 (`LLM-as-a-Judge`) | 记忆抽取 (`Memory Extraction`) | **单任务总 Token 消耗 (`Total`)** | 相对 No Memory 开销变化 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **No Memory** | 50,847.4 | — | — | **50,847.4** | 基准 |
| **Synapse** | 55,920.5 | 2,594.2 | — | **58,514.7** | +15.1% |
| **AWM** | 53,819.6 | 2,479.1 | 3,074.1 | **59,372.8** | +16.8% |
| **ReasoningBank** | **49,306.1** | 2,186.3 | 1,562.1 | **53,054.5** | **仅 +4.3%**（因交互步数减少，动作生成 Token 反而比无记忆更低） |

---

## 4.4 论文与开源代码实现 (`repos/reasoning-bank`) 深度对账表

通过对账论文 LaTeX 源码与 Google 官方仓库 `D:\coding\sharing\papers\repos\reasoning-bank` 的实现代码，发现 5 处关键工程细节与源码缺陷：

| 维度 | 论文描述 (`arXiv:2509.25140`) | 开源仓库实现 (`repos/reasoning-bank/WebArena/`) | 深度剖析与复现排坑指引 |
| :--- | :--- | :--- | :--- |
| **1. 记忆抽取输入是否包含裁判的诊断理由 (`autoeval_thoughts`)** | `Fig. 5` (`reasoningbank_si.pdf`) 展示输入给 `SUCCESSFUL_SI` / `FAILED_SI` 的 Prompt 仅包含 `Query: <user query>` 和 `Trajectory: <trajectory>` | 在 `WebArena/induce_memory.py:145-163` 中，代码会主动读取裁判输出的 `{model}_autoeval.json` 中的 `thoughts` 字段，并在轨迹末尾显式拼接：<br>`"\n\nThe task {succeeded\|failed} because: {autoeval_thoughts}"` | **这是源码中极其关键但论文未明说的提分细节**：记忆抽取模型并不是盲目从长轨迹里猜为什么失败，而是直接把 `LLM-as-a-Judge` 的归因分析（`thoughts`）作为先验诊断喂给了抽取器 |
| **2. `Description` 字段的触发/反触发边界定义与注入格式** | `Sec 3.2` 与 `Fig. 5` 将 `Description` 定义为 `<one sentence summary of the memory item>`；`Appendix A.2` (`appendix.tex:64`) 称检索后注入格式仅用 `title` 与 `content` | 1. `prompts/memory_instruction.py:34, 58, 87` 将 `Description` 升级为：<br>`<one sentence summary describing when or when NOT to use the memory item>`；<br>2. `run.py:188-193` 与 `agent.py:134-138` 将包含 `# Memory Item i`、`## Title`、`## Description`、`## Content` 的**完整 Markdown 块原样拼入 `sys_msg`** | 在 `Description` 中显式写出“**何时使用、何时严禁使用（when or when NOT to use）**”，配合 `sys_msg` 中强制要求每步 `<think>` 先讨论是否采用每条记忆，构成了完整的防负迁移护栏 |
| **3. 向量检索的非对称指令前缀（Asymmetric Instruction Embedding）** | `Appendix A.2` (`appendix.tex:60-63`) 仅描述用 `gemini-embedding-001` 计算任务查询嵌入并按余弦距离检索 | `memory_management.py:172-215` (`screening`) 实现为**非对称检索**：写入缓存库 `embeddings.jsonl` 时直接编码原始 `cur_query`（`3072` 维）；而检索打分时，为当前查询拼接了专用指令前缀：<br>`Instruct: Given the prior web navigation queries, your task is to analyze a current query's intent and select relevant prior queries that could help resolve it.\nQuery: {cur_query}`（且额外支持开源 `Qwen/Qwen3-Embedding-8B`，`L59-75`） | 指令微调嵌入（Instruction-tuned Embedding）能将“表面词汇不同但底层导航意图相通”的历史任务对齐；另外注意 `screening()` 在 `L190-197` 先把当前查询追加写入缓存文件，再读取此前缓存的 `cache_emb` 计算内积，避免自命中 |
| **4. 轨迹去噪与环境观察省略机制** | `Sec 3.1 Footnote 1` 简要提及用 $\pi_{\mathcal{L}}$ 的思考过程近似替代完整网页观察 $o_{0:t}$ | `induce_memory.py:47-76` 从每步 `step_*.pkl.gz` 中仅提取 `<think>` 与 `<action>`（跳过空动作步），完全丢弃冗长的 `axtree_txt` / `pruned_html`；`induce_scaling.py:45-64` 还提供了 `remove_invalid_steps` 过滤 `scroll()`、`noop()` 与非法参数动作 | 网页 DOM 动辄数万 Token，仅用 `<think> + <action>` 加上裁判对最终网页状态 `cap` 的诊断摘要（`autoeval_thoughts`），即可在 `1,562` Token 内完成高质量策略归纳 |
| **5. 开源仓库 `pipeline_scaling.py` 与 `induce_scaling.py` 的三处实现 Bug** | `Sec 3.3` 描述并行扩展采样 $k=5$ 条不同轨迹后送入 `PARALLEL_SI` 对比提取记忆 | 核查 `WebArena/pipeline_scaling.py:43-78` 与 `induce_scaling.py:168-196` 发现三处开源整理遗留 Bug：<br>① `pipeline_scaling.py:73` 在 `for i in range(args.num_trials):` 循环外传入 `f"{args.output_dir}/results_{i}"`，导致只传了最后一次试验目录；<br>② `induce_scaling.py:181` 把成功条件写反成了 `if reward == 0: status = "success"`（`induce_memory.py:131` 正确写为 `if reward == 1`）；<br>③ `induce_scaling.py:194-196` 未实例化 `CLIENT_DICT[args.model]` 就直接调用了 `client.one_step_chat` | 若直接运行开源脚本复现 `MaTTS` 并行扩展，必须先修复 `pipeline_scaling.py:73` 与 `induce_scaling.py:168-196` 的这三处 Bug |

---

## 4.5 批判性审视与对本项目的对齐启发 (Critical Analysis & Project Alignment)

### 1. ReasoningBank 的核心局限性
1. **缺乏记忆池去重、冲突消解与遗忘机制（Append-Only Bloat）**：
   作者在 `Appendix A.2` (`appendix.tex:72-78`) 与 `Sec 7 Limitations` 中坦言，当前采用最简单的“只追加不修剪（Append-Only）”策略，每跑完一个任务就往 JSONL 里塞入 1~3 条记忆。当连续运行上千个任务后，相似任务下会堆积大量冗余甚至相互矛盾的经验条目。
2. **仅按“任务查询 Query 相似度”检索，缺少细粒度模块化索引**：
   在 `memory_management.py` 中，多条记忆项被绑死在同一个历史任务 `task_id` 下，且仅对 `cur_query` 做向量编码（甚至没有对记忆项自身的 `Title + Description + Content` 建独立索引）。如果一个复杂任务在中途遇到了某个特定子问题（如“日期选择器格式报错”），但整体任务 Query 与历史任务不相似，就无法召回对应的排错经验。
3. **过多召回导致性能退化（$k>1$ 时不升反降）**：
   `Appendix C.1` 显示当召回经验数从 $k=1$ 增加到 $k=4$ 时，成功率从 `49.7%` 一路跌回 `44.4%`，说明未经结构化槽位约束的自然语言推理提示词一旦堆叠超过 3 条，极易引发 Agent 注意力分散或过度套用不匹配的策略。

### 2. 对联接 Agent 主报告（[storyline_and_evaluation_merged_technical_route_report.html](file:///d:/coding/sharing/.lavish/storyline_and_evaluation_merged_technical_route_report.html)）的直接启发
1. **直接支撑主报告“第三层：程序性经验与反思规则层（Procedural & Reflective Experience Memory）”**：
   - 在联接 Agent 处理“**正常顺畅单据 vs. 卡顿异常单据 / 中途取消的无效单据**”以及“**快路径执行 vs. 慢路径澄清交互**”时，完全对齐 `ReasoningBank` 的**正反双通道蒸馏范式**：
     - 从**正常顺畅单据与一次闭环对话**中，提取正向保障参数与映射策略（对应 `SUCCESSFUL_SI`）；
     - 从**卡顿异常记录、中途取消的无效单据或用户明确纠正的慢路径对话**中，结合网元实测回执诊断（对应 `autoeval_thoughts`），提取**预防性避坑规则与参数调整规则（Slot Revision Rule）**（对应 `FAILED_SI`），避免将无效废单或劣化配置当作正向习惯写入长期记忆。
2. **吸收源码级“适用/禁用边界（`when or when NOT to use`）+ 每步显式采用门控”设计**：
   - 借鉴 `prompts/memory_instruction.py:34` 对 `Description` 字段的改造，在我们经验规则条目的结构化 Schema 中强制设立 **`applicable_condition`（何时适用）** 与 **`exclusion_boundary`（何时严禁套用，例如：非周期性临时出差或短时测试单据严禁套用日常通勤保障模板）**。
   - 在 Agent 决策阶段，控制每次仅注入 **Top-1（至多 2~3 条）** 高置信度经验规则（遵循 $k=1$ 最优原则），并要求模型在推理链中先显式核验当前上下文是否满足 `applicable_condition` 且未触发 `exclusion_boundary`，杜绝盲目套用历史经验。
3. **利用 `MaTTS` 自对比思路提升合成数据与慢路径策略归纳质量**：
   - 在合成数据生成与离线策略沉淀阶段，可对同一模糊用户意图采样多条候选交互轨迹（含未澄清直接执行的失败轨迹与精准追问后闭环的成功轨迹），通过 `PARALLEL_SI` 的**跨轨迹自对比（Self-Contrast）**一次性提炼出高泛化性的消歧澄清准则。

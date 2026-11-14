# 15. REM (Reusable Experience Memory)：经验记忆控制论——存什么、何时召回、何时遗忘的运行态闭环治理

← 返回 [精读笔记索引](../reading_notes.md)　·　[论文主目录](../../README.md)

---

## 0. 论文基本信息与核心锚点

| 项目 | 内容 |
| :--- | :--- |
| **论文标题** | *REM: What to Store, When to Recall, What to Forget in Experience Memory for Coding Agents* |
| **作者与单位** | Xinyi Lisa Chen（Yale University / Amazon Intern）、Pedro Herrero-Vidal、Xiaohan Chen、Xiaojing Yu、Cris Liu、Bingqing Song、Bin Xu、Suleiman A. Khan、You-Lin Chen（Amazon） |
| **发表时间与出处** | `arXiv:2610.27377v1`（2026 年 10 月，**NeurIPS 2026 Workshop on Continual Learning for Enterprise AI Agents (CLEA) Camera-Ready**） |
| **本地文件锚点** | PDF：[`papers/procedural_memory/REM_2026.pdf`](../../procedural_memory/REM_2026.pdf)<br>LaTeX 源码（含 Camera-Ready 修订轨迹 `\rev{}` / `\del{}`）：[`papers/procedural_memory/2610.27377/source/main.tex`](../../procedural_memory/2610.27377/source/main.tex) |
| **算法与复现协议** | 基于 Amazon `Strands` 框架（6 工具：`bash / read / write / edit / grep / glob`）与 `Amazon Titan Text Embeddings v2`，完整伪代码见 `App A Alg. 1`，5 模型全量对账表见 `App E Tables 6–11` |
| **核心研究问题** | 为什么即便由完美先知（`Oracle`）把 100% 相关的历史轨迹或摘要塞给智能体，端到端任务解决率依然毫无提升？经验记忆的真正瓶颈究竟是“找不准（`Retrieval Fidelity`）”，还是“**进入长程推理循环后的运行态生命周期控制（`Lifecycle Control`：存什么形态、在智能体什么状态下注入、注入后停留多久）**”？ |
| **主报告支撑章节** | **3.3.3 节（四阶段诊断文档压缩与自动 Schema 发现）**、**3.3.4 节（基于受挫门控的按需召回 `Struggle-Gated Recall`、单次曝光即驱逐 `One-Shot Eviction` 与能力带宽边界）** |

---

<a id="c15-1"></a>

## 15.1 核心问题洞察：为什么把经验记忆当成“静态检索问题”会失效？（`Sec 1, Sec 3.1`）

### 1. 现有经验复用系统的三大失效实证（`Sec 1:81–86, Sec 3.1:116–122`）

在仓库级代码修复（`SWE-bench` / `SWE-ContextBench`）或 Text-to-SQL 等长视距探索任务中，单次运行往往跨越数十至上百个 `Think-Act` 回合，产生 `55K ~ 170K Tokens` 的庞大轨迹。现有记忆系统几乎把全部精力花在生命周期的中间环节——“如何检索出最相关的历史轨迹”，并在任务启动时一次性急切注入（`Eager Start-of-Run Injection`）。作者指出这一范式忽略了三个事实〔正文 `Sec 1:83–86`〕：

1. **智能体对注入上下文的实际吸收率（`Uptake / Coverage`）极低**：在本文的标识符探针测量中，智能体平均只引用了原始轨迹中 **`26.7% ~ 27.2%`** 的关键标识符，散文式摘要也仅引用了 **`45.7% ~ 52.5%`**〔正文 `Sec 1:85, Sec 5.3 Table 2`〕。
2. **存储粒度的两极分化陷阱（`Sec 2:100, Sec 3.1:119`）**：
   - 若存**原始长轨迹（`Raw Trajectory`，约 `105K Tokens`）**：在检索端，真正具有区分度的关键标识符被海量废弃探索分支稀释（`Match@1` 仅 `22.2%`）；在注入端，庞大的文本直接挤占并取代了当前智能体自身的探索推理（回合数从 `70` 骤降至 `50`，无法应用的坏补丁 `PatchNA` 从 `7` 恶化至 `11`）。
   - 若切碎为**原子事实切片（`Factoids / Chunks`，如 `Mem0` 约 `12 Tokens`、`Supermemory` 约 `30 Tokens`）**：虽然去除了噪声，却彻底打碎了“故障定位 $\rightarrow$ 根因理解 $\rightarrow$ 修复模式 $\rightarrow$ 验证方式”之间的逻辑连接结构（`Match@1` 仅 `23.2% ~ 25.3%`）。
3. **静态检索器看不见运行态智能体的实时内部状态（`Sec 3.1:121–122`）**：
   - 一个已经靠自身能力顺利定位到缺陷的智能体，强行塞入外部实现细节只会干扰其思路（尤其是高能力模型）；只有当智能体自身的假设耗尽、验证受挫（`Struggling`）时，重型实现记录才能发挥救援作用。
   - 一旦重型记录完成启发后若一直滞留在上下文前缀（`Pinned in Context`），就会在后续所有回合持续产生锚定偏置，把智能体往另一个历史任务的特定解法上拽。

### 2. 控制论视角下的经验记忆三决策模型（`Sec 1:87, Sec 3.2:126–135, Fig. 1`）

因此，作者将经验记忆从“检索查找问题（`Lookup Problem`）”重构为智能体 `Think-Act` 循环内部的“**三决策闭环控制问题（`Control Problem`）**”〔正文 `Sec 1:91–92, Sec 3.2, App A Alg. 1`〕：

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│             REM (Reusable Experience Memory): In-Loop Three-Decision Control Policy             │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                 │
│  [Decision 1: WHAT TO STORE (Offline Write Path — Alg. 1 Lines 1–6)]                            │
│   Raw Trajectory τ (55K–170K tok)                                                               │
│     ├─► 1a. Flatten(τ): Keep user/assistant text & tool inputs; drop tool results (~15× shrink) │
│     ├─► 1b. Extract & Render(τ): 1 LLM call extracts 8 discovered fields ──► Phase-Structured   │
│     │       Document d (~270–305 tok, >100× compression: Localize → Understand → Fix → Verify)  │
│     └─► 1c. Record(τ): Extract raw implementation edits & verifications r (capped at 12K chars) │
│                                      │                                                          │
│  [Read Path (At Task Start t = 0 — Alg. 1 Lines 7–8)]                                           │
│   New Task q ──► Titan Embed v2 Cosine Top-5 over {d_i} ──► 1-Call LLM Rerank ──► (d*, r*)      │
│   • Tier 1 Injection: Phased Document d* (~270 tok) placed in initial file & stays for full run │
│   • Tier 2 Withheld : Implementation Record r* (≤12K chars) withheld until struggle gate fires! │
│                                      │                                                          │
│  [Decisions 2 & 3: WHEN TO RECALL & WHAT TO FORGET (In-Loop Recall Node — Alg. 1 Lines 9–20)]   │
│   For turn t = 1 to N (100 turns max):                                                          │
│     ├─► Check Struggle Gate: Has gate fired before (g == True)?                                 │
│     │     • If g == False AND Struggle Signal S(o_{1:t-1}) fires (first genuinely failed        │
│     │       validation/test, excluding edits to test files):                                    │
│     │         ──► [Decision 2: WHEN TO RECALL]  ρ_t = r*, set g = True (Inject for 1 turn only) │
│     │     • Else (Not struggling yet, OR already exposed once in a prior turn):                 │
│     │         ──► [Decision 3: WHAT TO FORGET]  ρ_t = ∅ (One-Shot Eviction from active prefix!) │
│     └─► Execute Step: c_t = q ⊕ d* ⊕ h_{t-1} ⊕ ρ_t  ──►  (a_t, o_t) = π(c_t)                    │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

<a id="c15-2"></a>

## 15.2 REM 三阶段机制详解、自动 Schema 发现与吸收率探针（`Sec 3.2–3.3, App A–F`）

### 1. 决策一：存什么（`What to Store`）——四阶段结构化文档与双层读取介质（`Sec 3.2:128–135`）

针对每条已完成的探索轨迹 $\tau$（原始长度 `55K ~ 170K Tokens`），写入路径生成两个互补粒度的数据产物〔正文 `Sec 3.2:128–135`，附录 `App A Alg. 1 & App B:340`〕：
1. **第一层（`Tier 1`）：四阶段诊断文档（`Phase-Structured Document` $d$，平均仅 `270 ~ 305 Tokens`）**：
   - **无损扁平化预压缩（`Flatten`）**：保留用户输入、助手推理文本与工具调用入参（`tool-call inputs`），直接丢弃冗长的工具返回结果（`tool results`，如大段文件内容转储），在不做截断的前提下实现约 **`15 倍`** 体积缩减；
   - **单次 LLM 结构化抽取与确定性渲染（`Extract & Render`）**：通过 1 次 LLM 调用抽取领域字段，并由确定性模板渲染为严格对齐诊断工作流四阶段——**定位（`Localize`）$\rightarrow$ 理解根因（`Understand`）$\rightarrow$ 修复模式（`Fix Pattern`）$\rightarrow$ 验证方式（`Verify`）**——的紧凑文档 $d$（实现超过 **`100 倍`** 的总压缩率）。
   - **检用合一设计**：文档 $d$ **既是向量检索与重排的唯一索引单元，又是任务启动时注入智能体上下文的导航单元**（以初始必读文件形式挂载并全程保留在历史中，`App B:340`）。
2. **第二层（`Tier 2`）：原始实现记录（`Implementation Record` $r$，上限 `12,000 字符` $\approx 3,000\text{ Tokens}$）**：
   - 提取同一轨迹 $\tau$ 中实际执行的代码编辑（`raw edits`）与验证命令记录，在任务启动时**严格扣留不注入**，仅在循环内受挫门控触发时按需调出。

### 2. 决策二与三：何时召回（`When to Recall`）与何时遗忘（`What to Forget`）（`Sec 3.2:134–135, App A Alg. 1`）

在智能体的第 $t = 1, \dots, N$ 步循环中，内置召回节点（`In-Loop Recall Node`）实时监控观测序列 $o_{1:t-1}$〔附录 `App A Alg. 1 Lines 9–20` & `App B:340`〕：
- **受挫触发器（`Struggle Gate` $S(o_{1:t-1})$）**：当且仅当智能体在运行中遭遇**首次真正的验证失败（`First Genuinely Failed Validation`）**——即运行测试或检查命令返回失败结果（**显式过滤掉智能体对测试文件本身的编辑**，避免智能体自己编写复现测试时的预期报错被误判为受挫）——且此前尚未触发过（$\lnot g$）时，门控激活，在下一回合将实现记录 $\rho_t \leftarrow r^\star$ 注入上下文，并将布尔锁置为 $g \leftarrow \textsc{true}$。
- **单次曝光即驱逐（`One-Shot Eviction`）**：在紧接着的下一个回合（以及此后的所有回合），由于 $g$ 已为 $\textsc{true}$，召回节点立即执行 $\rho_t \leftarrow \emptyset$，将 12K 字符的实现记录 $r^\star$ 从上下文前缀中彻底移除（不再滞留于 KV-Cache 前缀中），仅保留轻量级的四阶段文档 $d^\star$。

### 3. 零人工提示工程的自动 Schema 发现闭环（`Automated Schema Discovery`，`Sec 3.3, App F`）

为消除手工设计抽取字段的领域壁垒，`REM` 设计了一个仅需少量无标注示例轨迹（在代码中仅取经验池里的 **9 条轨迹**，且严格排除评测集任务）的元循环（`Meta-Loop`）〔正文 `Sec 3.3:140`，附录 `App F:582–608`〕：
1. **四步自迭代协议**：① 生成器 LLM（`Claude Sonnet 4`）编写或修订包含 `6 ~ 10` 个命名字段及 JSON 模板的抽取提示词；② 在验证集轨迹（截断至 15K 字符）上执行抽取；③ 评判器 LLM（`LLM Judge`）从 **覆盖度（`Coverage`）、特异性（`Specificity`）、可区分度（`Discriminability`）、简洁性（`Conciseness`）、结构一致性（`Structural Consistency`）** 五个维度按 `1 ~ 5` 分打分；④ 针对薄弱维度定向修订，当所有五维均分 $\ge 4.0$ 或满 5 轮时停止。
2. **首轮即收敛与手工 مقابل自动字段对账（`App F Table 14`）**：
   在代码修复域与 Text-to-SQL 域上，该元循环均在**第 1 轮迭代即达成收敛**（代码域五维得分：覆盖度 `4.12`、特异性 `4.00`、**可区分度 `4.75`**、简洁性 `4.38`、结构一致性 `4.50`；SQL 域前四维满分 `5.0`、简洁性 `4.8`）。对比手工 Schema 与自动发现 Schema 的字段差异〔附录 `App F Table 14`〕：

   | 手工设计的 Schema 字段（`Hand-written`，9 字段） | 自动发现的 Schema 字段（`Discovered`，8 字段） | 结构演进逻辑（为什么自动 Schema 检索更准？） |
   | :--- | :--- | :--- |
   | `files_modified`、`root_cause`、`fix_approach` | `files_modified`、`root_cause`、`fix_approach` | 三项核心定位与修复字段完全一致 |
   | `functions_changed` + `classes_involved`（拆为两项） | `related_functions`（合并为一项） | 精简代码结构层级冗余 |
   | `test_names` + `test_commands`（拆为两项） | `test_cases`（合并为一项） | 合并测试描述 |
   | `files_read`、`key_identifiers`（大量混杂探索噪声） | *（直接剔除！）* | **剔除仅读取未修改的文件与大杂烩标识符，防止稀释检索向量** |
   | *（无）* | **`bug_description`、`repository_info`、`error_messages`** | **新增三项问题表征字段：少花篇幅罗列浏览痕迹，多花篇幅刻画报错现象，直接对准新任务 Problem Statement！** |

### 4. 上下文实际吸收率探针（`Identifier Utilization Probe`，`Sec 3.3:144, App G`）

为了定量回答“智能体到底读没读注入的记忆”，作者构建了离线标识符探针：从注入文本中提取所有文件路径及长度 $\ge 4$ 字符的 `CamelCase / snake_case` 标识符（剔除停用词与配对的无记忆基线自己本就会搜到的标识符），统计它们在智能体后续自主输出的推理文本或工具调用入参（不含工具返回结果）中出现的比例，定义为**覆盖率（`Coverage / Uptake`）**，并同步测量首次引用回合（`First Influence`）、引用跨度窗口（`Window`）与最后一次引用后的无效滞留回合占比（`Dead Weight`）〔正文 `Sec 3.3:144`，附录 `App G Table 12`〕。

---

<a id="c15-3"></a>

## 15.3 SWE-ContextBench Lite 全量实验与五维深度剖析（`Sec 5, Tables 1–13`）

实验在 **SWE-ContextBench Lite**（99 个仓库级真实 Bug 修复任务 + 300 条已解决历史轨迹池，每题带 Ground-Truth 相关轨迹标签）上进行〔正文 `Sec 4:150`〕。

### 1. 检索精度对比：为什么 270 Token 的四阶段文档远超全部 SOTA 记忆系统？（`Sec 5.2, Table 1 & App D Table 5`）

在完全相同的 99 个任务与 300 条轨迹池上，对比四大主流开源/商业记忆系统（`Mem0`、`LangMem`、`OpenViking`、`Supermemory`）及智能体自主搜索基线的 Top-1 准确率（`Match@1`）〔图表 `Table 1` & 附录 `App D Table 5`〕：

| 记忆系统 / 检索方法 | 存储单元形态与平均大小 | 候选集预算 (`Candidates`) | 第一阶段 `Cosine Top-1` | 第一阶段 `Gold in Top-5` | 最终重排后 **`Match@1`** | 重排转化率 (`Conversion`) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `Free trajectory`（智能体自搜原始轨迹） | 原始轨迹（$\sim 105\text{K tok}$） | 自主搜索 | — | — | 22.2% | — |
| `Supermemory` | 托管文本块（$\sim 30\text{ tok}$） | 15 | — | — | 23.2% | — |
| `Mem0` | 抽取原子事实（$\sim 12\text{ tok}$） | 3 | — | — | 25.3% | — |
| `Free summary`（智能体自搜轨迹摘要） | 轨迹散文摘要（$\sim 373\text{ tok}$） | 自主搜索 | — | — | 35.4% | — |
| `OpenViking` | 索引文件块（$\sim 246\text{ tok}$） | 3 | — | — | 38.4% | — |
| `LangMem`（最强外部基线） | 抽取记忆条目（$\sim 48\text{ tok}$） | 10（`Recall@10 = 73.3%`） | — | — | 55.6% | — |
| **`REM`（手工 Schema）** | 四阶段结构化文档（$\sim 270\text{ tok}$） | **5** | **65.7%** | **83.8%** | **66.7%** | 79.6%（5 次解析失败回退） |
| **`REM`（自动发现 Schema）** | 四阶段结构化文档（$\sim 305\text{ tok}$） | **5** | 62.6% | 78.8% | **`68.7%`（`+13.1 pp`）** | **`87.2%`（0 解析失败）** |

*注：自动发现 Schema 池中因 API 限流有 33/300 条轨迹未完成抽取（含 8 个评测任务的真值轨迹，直接计为未命中），在此严苛条件下仍取得 `68.7%` 的最高分〔附录 `App D:369`〕。*

**核心归因（`Sec 5.2:224`）**：`REM` 第一阶段仅使用最普通的 `Titan Text Embeddings v2` 余弦相似度，在未做任何 LLM 重排前（`Cosine Top-1 = 62.6% ~ 65.7%`）就已经超越了 `LangMem` 10 候选重排后的 `55.6%`；且与体积几乎相同的 `OpenViking`（`246 tok`，`38.4%`）相比高出 **`+30.3 pp`**。这证明**决定检索上限的不是检索器算法或文本长度，而是写入时按诊断四阶段（定位/根因/修复/验证）组织的结构化信噪比**。

### 2. 端到端解决率、成本与上下文吸收率对账（`Sec 5.1, Sec 5.3, Table 2 & App C Table 4`）

在 `Claude Sonnet 4.5` 上，对比无记忆、五种任务启动时注入（含 `Oracle` 先知真值）以及 `REM` 的端到端解决率（`ITT Resolved %`）、加权 Token 成本（`Cost tok/task`）、回合数、耗时、坏补丁数（`PatchNA`）与标识符吸收覆盖率（`Coverage`）〔图表 `Table 2`、附录 `App C Table 4` & `App G Table 12`〕：

| 实验条件 | 存储/注入单元大小 | 注入标识符数 (`Injected`) | 实际引用数 (`Referenced`) | **吸收覆盖率 (`Coverage`)** | 无效滞留比 (`Dead Weight`) | **解决数 / 99 (`ITT %`)** | 加权成本 (`Cost tok`) | 平均耗时 (`Min`) | 坏补丁 (`PatchNA`) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `No memory`（3 次重复均值） | n/a | — | — | — | — | `23, 26, 25` (**`24.9%`**) | 452K | 11.9m | 7.0 |
| `Wrong summary`（注入无关摘要） | $\sim 380\text{ tok}$ | 8.9 | 0.3 | `3.4%` | 96.3% | `23` (`23.2%`) | 431K | 14.4m | 7 |
| `Free trajectory`（自搜原始轨迹） | $\sim 105\text{K tok}$ | 67.7 | 17.9 | `26.7%` | 23.0% | `22` (`22.2%`) | 637K | 13.1m | 11 |
| `Oracle trajectory`（**先知真值原始轨迹**） | $\sim 111\text{K tok}$ | 67.7 | 18.1 | `27.2%` | 19.3% | `24` (`24.2%`) | 768K（`+70%`） | 9.5m | 11 |
| `Oracle summary`（**先知真值散文摘要**） | $\sim 390\text{ tok}$ | 9.3 | 4.3 | `45.7%` | 51.9% | `23` (`23.2%`) | 378K | 13.7m | 6 |
| `Free summary`（自搜散文摘要） | $\sim 373\text{ tok}$ | 9.3 | 4.8 | `52.5%` | 52.8% | `24` (`24.2%`) | 484K | 13.8m | 10 |
| `Oracle phased document`（先知四阶段文档） | $\sim 540\text{ tok}$ | 12.4 | 7.8 | `64.7%` | 35.7% | `26` (`26.3%`) | 463K | 10.1m | 0 |
| **`REM`（检索四阶段文档 + 受挫门控 + 驱逐）** | $\sim 270\text{ tok}$ | 11.0 | 7.5 | **`69.1%`** | 27.2% | **`27, 29, 26` (`27.6%`)** | **`374K`（`-17%`）** | **`8.8m`（`-26%`）** | **`4.0`（`-43%`）** |

**核心实证结论（`Sec 5.1 & Sec 5.3`）**：
1. **即便给 100% 正确的 `Oracle Trajectory` 或 `Oracle Summary`，端到端解决率依然停留在 `23.2% ~ 24.2%`（不高于无记忆的 `24.9%`）**；唯独将同一条先知轨迹渲染为**四阶段文档（`Oracle Phased Document`）**或通过 `REM` 注入，解决率立即跃升至 `26.3% ~ 27.6%`（且在全部 3 次独立重复实验中 `27 vs 23`、`29 vs 26`、`26 vs 25` 100% 稳定胜出），同时将单任务 Token 成本降低 **`17%`**（`452K → 374K`）、耗时缩短 **`26%`**（`11.9m → 8.8m`）。
2. **吸收覆盖率（`Coverage`）直接揭开了背后的因果机制**：`REM` 的四阶段文档虽然比 `Oracle Summary` 更短（`270` 对比 `390 Tokens`），但被智能体读取和引用的完整度却高出 **`1.5 倍`**（**`69.1%` 对比 `45.7%`**）；在四个启动注入条件（$n=91$ 成功，$284$ 失败）中，成功解决任务的运行对注入标识符的引用覆盖率显著高于失败运行（Cohen's $d = +0.20, p = 0.03$，`App G Table 13`）。

### 3. 决策级消融实验：受挫门控（`Struggle Gate`）与单次曝光驱逐（`Eviction`）各自贡献多少？（`Sec 5.4, Table 3 & App E Table 11`）

固定注入相同的 `REM` 四阶段文档，仅改变第二层 `12K 字符实现记录（Implementation Record）` 的召回与留存策略（3 次重复均值，共 297 次任务运行）〔图表 `Table 3` & 附录 `App E Table 11`〕：

| 实现记录（`Implementation Record`）控制策略 | 触发注入的任务占比 | 第 1/2/3 次重复解决数 | **3 次均值解决率 (`ITT %`)** | 相对完整 `REM` 差值 $\Delta$ | 加权成本 (`Cost tok/task`) | 吸收覆盖率 (`Coverage`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `Never, document only`（永不注入记录，仅靠 270 tok 文档） | `0%` | `27, 28, 25` | `26.9%` | `-0.7 pp` ($p=0.82$) | 374K | **69.1%** |
| `Eager, at first source edit`（首次改代码时无条件急切注入） | `100%` | `23, 26, 26` | `25.3%` | **`-2.3 pp`** ($p=0.17$) | 423K（`+13%`） | 38.8% |
| `On struggle, then pinned`（受挫时注入，但常驻上下文不驱逐） | `56%` | `25, 26, 23` | `24.9%` | **`-2.7 pp`** ($p=0.08$) | **353K** | 50.5% |
| **`On struggle, then evicted (Full REM)`（受挫时注入 + 1 回合后驱逐）** | **`58%`** | **`27, 29, 26`** | **`27.6%`** | **基准 (`---`)** | 374K | 50.3% |

**核心机制解耦（`Sec 5.4:260`）**：
1. **受挫门控（`Gating`）击败急切注入（`Eager`）**：无脑在首次改代码时注入实现记录不仅使成本从 `374K` 涨至 `423K`，还将解决率从 `27.6%` 拉低至 `25.3%`（在双方存在分歧的 19 个任务运行中，受挫门控赢下 **13 个**）。
2. **用完即驱逐（`Eviction`）击败常驻（`Pinned`）**：常驻不驱逐（`Pinned`）与单次驱逐（`Evicted`）对记录标识符的引用覆盖率几乎完全相同（`50.5%` 对比 `50.3%`），但常驻策略在全部 3 次重复实验中均输给驱逐策略（均值低 **`-2.7 pp`**，退回无记忆水平 `24.9%`）——这证明**驱逐改变的不是智能体从记录中读到了多少信息，而是消除了外部历史补丁在后续几十个回合中对智能体自身推理的持续偏置干扰**！

### 4. 核心发现：经验记忆存在严格的“能力收益带宽（`Capability Band`）”（`Sec 5.5, Fig. 3, App E Tables 6–10`）

作者将完全相同的记忆与控制策略横跨 **5 个不同能力层级的模型**（裸跑解决率从 `20.2%` 到 `52.5%`）进行扫描，发现了极具警示意义的符号反转规律〔正文 `Sec 5.5:266`，图表 `Fig. 3`，附录 `App E Tables 6–10`〕：

| 智能体基座模型 | `No Memory` 裸跑解决率 | `Oracle Phased Doc`（先知文档） | `REM (Document Only)`（仅 270 tok 文档） | `REM (Gate w/o Eviction)`（常驻记录） | `Full REM`（门控 + 驱逐） | 记忆干预的净效应符号与幅度 |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Claude Haiku 4.5**（弱模型） | `20.2%` (20/99) | `23.2%` (`+3.0`) | **`24.2%` (`+4.0`)** | **`24.2%` (`+4.0`)** | `21.2%` (`+1.0`) | **正向增益（`+4.0 pp`）**；但弱模型难以消化 12K 原始代码记录（容易机械照抄），仅给 270 tok 文档效果最佳 |
| **Claude Sonnet 4.5**（中模型，Rep 1 / 3-Rep Mean） | `23.2%` / `24.9%` | `26.3%` (`+3.1`) | **`27.3%` (`+4.1`)** / `26.9%` | `25.3%` / `24.9%` | **`27.3%` (`+4.1`)** / **`27.6%` (`+2.7`)** | **正向增益（`+2.7 ~ +4.1 pp`）**，且成本下降 **`17%`**（`452K → 374K`） |
| **Claude Opus 4.6**（中强模型） | `31.3%` (31/99) | `32.3%` (`+1.0`) | **`32.3%` (`+1.0`)** | `29.3%` (`-2.0`) | `31.3%` (`0.0`) | **临界平衡点（`+1.0 pp`）**，同时 Token 成本从 `280K` 大幅降至 **`231K`（`-17.6%`）** |
| **Claude Opus 4.8**（强模型） | **`47.5%` (47/99)** | `42.4%` (`-5.1`) | `39.4%` (`-8.1`) | `40.4%` (`-7.1`) | `40.4%` (`-7.1`) | **显著负向干扰（`-5.1 ~ -8.1 pp`）**！即便给 100% 正确的 `Oracle Doc` 也下跌 `-5.1 pp` |
| **Claude Sonnet 5**（最强模型） | **`52.5%` (52/99)** | `50.5%` (`-2.0`) | `50.5%` (`-2.0`) | `43.4%` (`-9.1`) | `47.5%` (`-5.0`) | **显著负向干扰（`-2.0 ~ -9.1 pp`）**！常驻记录更造成 `-9.1 pp` 的雪崩下跌 |

**为什么强模型连 100% 正确的 `Oracle Phased Document` 都会掉点？（`Sec 5.5:266`）**
因为当基座模型自身的无辅助解决率已经高达 `47.5% ~ 52.5%` 时，它在绝大多数任务上依靠直接阅读当前代码库就能独立且精准地定位缺陷；此时在开局强行塞入来自“相似但并非同一个 Bug”的历史修复文档，反而会**喧宾夺主地挤占并带偏强模型原本正确的自主推理轨迹**。

---

<a id="c15-4"></a>

## 15.4 对联接 Agent 主报告（3.3.3 节与 3.3.4 节）的落地启发

`REM` 是 `P1` 梯队收官的关键拼图，它从运行态控制论视角为我们主报告 [`storyline_and_evaluation_merged_technical_route_report.html`](../../../../.lavish/storyline_and_evaluation_merged_technical_route_report.html) 的**第 3.3.3 节（经验压缩形态）**与**第 3.3.4 节（按需召回、即时驱逐与能力门控）**提供了四条硬核设计准则：

1. **经验卡片必须遵循“四阶段约 300 Token 检用合一形态”，严禁直接注入原始长会话日志（支撑 3.3.3 节）**：
   - `Table 1 & Table 2` 证明，将万字轨迹先剥离冗余工具返回（`Flatten`），再按 **`症状定位（Localize）→ 根因理解（Understand）→ 调参修复模式（Fix Pattern）→ 核验指标（Verify）`** 渲染为约 `270 ~ 300 Tokens` 的紧凑结构化卡片，不仅使检索 `Match@1` 领先 `Mem0` / `LangMem` 达 **`13.1 ~ 43.4 pp`**，更使智能体对卡片关键参数的实际吸收率高达 **`69.1%`**（是原始日志 `27.2%` 的 **2.5 倍**）。
2. **用“5 维 LLM Judge 自动 Schema 发现”替代手写抽取字段（支撑 3.3.3 节）**：
   - 借鉴 `REM Sec 3.3 & App F`：只需抽样約 10 条历史排障轨迹，按“覆盖度、特异性、可区分度、简洁性、结构一致性”五维自动演进抽取 Schema，重点保留**故障现象与告警特征字段**（对应 `bug_description / error_messages`），剔除中间无关查询记录（对应剔除 `files_read`），即可实现零人工提示工程的跨业务域迁移。
3. **两级按需注入与“单次曝光即驱逐（`One-Shot Eviction`）”机制（支撑 3.3.4 节）**：
   - **第一级（轻量导航卡，常驻）**：约 270 Tokens 的四阶段排障概要在会话开始时注入；
   - **第二级（重型历史单据明细/完整排障对话，受挫门控 + 瞬时驱逐）**：平素严格扣留，**仅当智能体首轮快路径执行失败或收到网元异常/用户负向反馈（`Struggle Signal`）时才调入当前回合**；且在该回合生成修正动作后，**立即从下一回合的活跃上下文前缀中驱逐该重型记录（`One-Shot Eviction`）**，防止历史旧单据的参数细节在后续多轮对话中产生持续锚定污染（`Pinned` 策略会导致解决率下跌 `2.7 pp`）。
4. **根据任务复杂度与模型能力动态决定是否挂载开局经验（支撑 3.3.4 节 `Recipient-Conditioned Gating`）**：
   - `REM Sec 5.5` 揭示的“能力带宽效应”提醒我们：对于智能体仅凭当前实时网元状态与用户明确指令就能 100% 确定性闭环的简单快路径任务（类似强模型已能独立解决的任务），开局强行塞入相似历史案例反而可能引发负迁移；对此类高置信度场景，连第一级经验卡也应延迟到出现歧义或受挫信号时再介入。

---

← 返回 [精读笔记索引](../reading_notes.md)　·　[论文主目录](../../README.md)

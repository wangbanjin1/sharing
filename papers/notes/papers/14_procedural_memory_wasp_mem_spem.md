# 14. WASP-Mem 与 SPEM：面向复杂企业流程与大规模技能库的程序记忆自组织、诊断反馈与结构感知检索

← 返回 [精读笔记索引](../reading_notes.md)　·　[论文主目录](../../README.md)

---

## 0. 双篇论文基本信息与核心锚点

本篇笔记精读 **P1-8** 组合的两篇 2026 年末前沿程序记忆（`Procedural Memory`）工作——它们从两个互补视角解决了程序记忆的工程落地难题：**`WASP-Mem`（`arXiv:2611.04003`）**回答了“**在复杂专有企业环境中，程序记忆应当由人为预设 Schema 还是交由智能体自组织成互链 Wiki？人类精力应当花在事前定 Schema 还是事后故障诊断？**”；**`SPEM`（`arXiv:2610.26995`）**回答了“**当技能库扩展至数百至数千个工具/技能时，如何结合原子技能记忆、反向切片提取的 `Skill-DAG` 模板与状态感知 `Skill-GNN` 实现低开销结构化检索？**”。

| 维度 | 论文 A：**WASP-Mem**（`2611.04003`） | 论文 B：**SPEM**（`2610.26995`） |
| :--- | :--- | :--- |
| **论文标题** | *WASP-Mem: Let Agent Organize Procedural Memory. Human Spend Effort on Diagnosis* | *SPEM: Structure-Aware Procedural Memory for Efficient Skill Use in LLM Agents* |
| **作者与单位** | Peizhi Niu, Ge Shi, Vaibhav Gorde, Sarthak Ghosh, Christos Faloutsos（CMU）, Min Cheng, Kevin Chen | Ran Zhou, Zehui Kong, Fanyu Lin, Jiaheng Liu, Zhen Zhang, Yuxiang Ren（南京大学智能科学与技术学院） |
| **发表时间与编号** | `arXiv:2611.04003v1`（2026 年 11 月，ICLR 2027 投稿版式） | `arXiv:2610.26995v1`（2026 年 10 月，AAAI 2027 Preprint） |
| **本地文件锚点** | PDF：[`papers/procedural_memory/WASPMem_2026.pdf`](../../procedural_memory/WASPMem_2026.pdf)<br>LaTeX MD：[`papers/procedural_memory/2611.04003/2611.04003.md`](../../procedural_memory/2611.04003/2611.04003.md)<br>LaTeX 源码：[`papers/procedural_memory/2611.04003/source/sections/`](../../procedural_memory/2611.04003/source/sections/) | PDF：[`papers/procedural_memory/SPEM_2026.pdf`](../../procedural_memory/SPEM_2026.pdf)<br>LaTeX MD：[`papers/procedural_memory/2610.26995/2610.26995.md`](../../procedural_memory/2610.26995/2610.26995.md)<br>LaTeX 源码：[`AnonymousSubmission2027.tex`](../../procedural_memory/2610.26995/source/AnonymousSubmission2027.tex) 与 [`appendix.tex`](../../procedural_memory/2610.26995/source/appendix.tex) |
| **代码与复现状态** | 基于 `pi-agent v0.75.3`（`--no-session`）与 `Cohere Embed v4`（1024 维），完整协议见 `App B & App E` | 基于 `Harbor` 执行器与 `Hetero-GNN`（2 层，128 维），完整推理伪代码见 `App A.1 Alg. 1` 与 `Table 4` |
| **主报告支撑章节** | **3.3.3 节（成败双源巩固与人类诊断价值）**、**3.3.4 节（隐式去重对比机械 Schema 强合并的防误合教训）** | **3.3.3 节（轨迹反向切片提纯 `Trajectory-DAG`）**、**3.4 节（原子技能 + `Skill-DAG` 双层检索与异常恢复）** |

---

<a id="c14-1"></a>

## 14.1 Part I — WASP-Mem：基于自组织互链 Wiki 的程序记忆巩固与“苦涩教训”（`2611.04003`）

### 1. 企业级程序自动化中的“残差程序知识缺口”（`Sec 1, Sec 3, App A`）

在企业生产环境中，智能体的静态脚手架（`Static Harness` $H$，含系统提示词、工具接口与预置上下文）无法预知所有专有策略、未文档化的 API 行为（如特殊分页参数、权限校验）、严苛的输出规范以及依赖服务状态的异常恢复路径〔正文 `Sec 1:25`，附录 `App A:240–243`〕。作者将这类“未编码在静态脚手架 $H$ 中、仅在真实执行时暴露、但一旦掌握即可跨任务复用的条件—动作—恢复规律”形式化定义为**残差程序知识（`Residual Procedural Knowledge`）**〔附录 `App A:240–243`〕。

作者在 `App A Table 2` 中明确划定了**程序记忆（`Procedural Memory`）**与情景记忆（`Episodic`）、语义记忆（`Semantic`）在重复试验与失败处理上的本质边界〔附录 `App A Table 2`〕：

| 对比维度 | 情景记忆（`Episodic`） | 语义记忆（`Semantic`） | 程序记忆（`Procedural`） |
| :--- | :--- | :--- | :--- |
| **存储核心内容** | 具体历史事件及其发生上下文 | 通用客观事实或概念 | **条件—动作—异常恢复规程（`Condition-Action Procedure`）** |
| **多次重复试验的处理** | 保持为彼此独立的历史事件 | 重复事实直接合并去重 | **融合并精炼同一条可复用执行规程** |
| **失败轨迹的价值** | 仅作为另一条失败事件记录 | 错误事实直接丢弃 | **暴露缺失的前置条件（`Preconditions`）或故障恢复分支** |
| **泛化目标与主评测指标** | 事件级回忆准确率（`Recall`） | 概念级回忆准确率（`Recall`） | **跨任务实例的端到端执行成功率（`Execution Success`）** |

一个满足**程序充分性（`Procedural Sufficiency`）**的巩固条目必须同时具备四要素〔附录 `App A:249–252`〕：**(i) 规程目标（`Purpose`）**、**(ii) 触发与适用条件（`Applicable Conditions`）**、**(iii) 可执行动作与实现细节（`Executable Actions & Details`）**、**(iv) 动作失败时的恢复路径（`Recovery Behavior`）**。

### 2. WASP-Mem 核心架构与三类变体设计（`Sec 3.1–3.2, App B`）

设第 $r$ 轮持久化记忆库为 $M_r$，在 $n=127$ 个基准任务上执行产生的轨迹批次为 $B_r = \{\tau_i^r\}_{i=1}^n$，对应的环境或人工反馈为 $F_r = \{f_i^r\}_{i=1}^n$，准入范围（`Ingestion Scope`）为 $S \in \{\text{Success-only}, \text{Both}\}$。记忆巩固算子 $C$ 按轮次迭代更新记忆库〔正文 `Sec 3 Eq. 1:66`，附录 `App A:246`〕：
$$M_{r+1} = C\!\left(M_r, B_r, F_r; S\right)$$

**WASP-Mem（Wiki-based Agent-Synthesized Procedural Memory）**受 Karpathy（2026）“LLM 维护个人知识库 Wiki”思想启发，将持久化记忆组织为一个以 `index.md` 为总路由入口、通过 Obsidian 风格双向链接 `[[wikilinks]]` 互连的 Markdown Wiki 文件系统〔正文 `Sec 3.1:72–79`，附录 `App B:298–300`〕：

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    WASP-Mem Multi-Round Execution & Wiki Consolidation Loop                     │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                 │
│  [Execution Phase (Round r, Frozen Store M_r)]                                                  │
│   Task q_i ──► Retrieval-Only Subagent (Read-only M_r)                                          │
│                 ├─ 1. Inspect index.md router + Cohere Embed v4 (1024-d) semantic search (Top-5)│
│                 ├─ 2. Follow [[wikilinks]] across related conditions / actions / lessons         │
│                 └─ 3. If task-level misses OR step fails ──► Trigger Subgoal Search (Top-3)      │
│                                      │                                                          │
│                                      ▼                                                          │
│                Executor (pi-agent bash-only) ──► Raw Rollout Trace τ_i^r (.jsonl)               │
│                                      │                                                          │
│                                      ▼                                                          │
│                Feedback E(τ_i^r): Self-Judge | Task-binary | Checkpoint-binary | + Human Diag   │
│                                      │                                                          │
│  [Consolidation Phase (Mutable Copy of M_r ──► M_{r+1})]                                        │
│   Eligible Rollouts (S: Success-only vs. Both) processed sequentially in lexicographic order:   │
│   ├─ 1. Ingestion : Spawn subagent to review τ_i^r + f_i^r; read existing wiki pages first;     │
│   │                 implicitly merge/revise existing page or create new page + [[wikilinks]]    │
│   ├─ 2. Lint      : Check generalizability, ambiguity, page length, link integrity & conflicts; │
│   │                 split, merge, or relink pages                                               │
│   └─ 3. Re-index  : Rebuild 1024-d semantic search index over updated wiki ──► M_{r+1}          │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

为严格检验“**应当由人类预先规定知识结构，还是让智能体自主组织结构**”，作者在 `WASP-Mem` 内部构造了三个受控递进变体，并与四类外部基线正交对比〔正文 `Sec 3.1:80–83, Sec 3.2:88–91`，附录 `App B Table 3 & Table 4`〕：

| 方法类别 | 方法名称 | 持久表示形态 | 是否在写入前读取现有库 | 组织约束与去重方式 | 检索适配器规则（`App B Table 4`） |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **无记忆基线** | `No Memory` | 无 | 否 | 无 | 不检索 |
| **原始轨迹基线** | `No Consolidation` | 原始会话 `.jsonl` 轨迹 | 否 | 仅保存原始轨迹，不抽象不合并 | 检索最相似的 1 条原始轨迹全文 |
| **扁平洞察基线** | `Insights` | 抽象策略原则文件 | 否（各轨迹独立提取） | 扁平集合，跨会话零去重 | 任务级检索 Top-5 文件，子目标检索 Top-3 文件 |
| **三层技能树基线** | `SkillX` | `Planning / Functional / Atomic` 三层技能 | 否（各轨迹独立提取） | 预设三层固定层级，跨规划树零去重 | 路由/语义检索任务级 Top-5、子目标 Top-3，展开关联层 |
| **WASP-Mem 变体 1** | **`Free Form`（核心推荐）** | **无约束 Markdown Wiki 页面**（仅含标题、简述、修改时间轻量头） | **是（按序读写同一可变副本）** | **智能体自主组织结构 + 隐式去重（`Implicit Dedup`）** + 任意 `[[wikilinks]]` | 任务级检索 `index.md` + Top-5 页面；子目标检索 Top-3 页面 |
| **WASP-Mem 变体 2** | `Schema Form` | **强类型 Wiki 页面**（强制分为 `Procedures`、`Actions`、`Lessons` 三类，固定字段与枚举项） | **是（按序读写同一可变副本）** | **人类预设 Schema + 隐式去重**；固定链接语法（`Action` 间禁止互链） | 任务级从 Top-3 候选选 1 个 `Procedure`；子目标检索 Top-5 `Actions` 并展开关联页 |
| **WASP-Mem 变体 3** | `Schema Form-ED` | 同上（`Procedures / Actions / Lessons` 强类型页面） | **否（先盲提增量页，后脚本强合并）** | **人类预设 Schema + 显式规则去重（`Explicit Dedup`）**：先用确定性脚本归一化页面 ID（如将所有调用 Python 的动作映射为 `action-bash-run-python`），再强制 LLM 合并同 ID 页面 | 同 `Schema Form` |

### 3. 四维受控实验全量结果与“过滤假说（Filter Hypothesis）”（`Sec 4, App C Tables 7–12`）

作者在两个包含专有规程缺口的企业级基准上展开评测〔正文 `Sec 4.1:108–123`〕：
- **TheAgentCompany**：涵盖 GitLab、RocketChat、OwnCloud、Plane 四个自托管 Docker 服务的 **127 个职场任务、542 个基于环境状态检验的二进制检查点（`Checkpoints`）**；
- **$\tau^2$-Bench Retail（In-Domain 跨任务泛化）**：编写一套对智能体脚手架完全隐藏的自定义零售标准操作规程（SOP），划分为严格不相交的 **74 个训练任务（391 个检查点）**与 **40 个测试任务（192 个检查点）**，在训练集上巩固后冻结记忆库并在测试集上评测。

#### 实验一：七种巩固方法跨三模型与双基准全量对比（`Sec 4.2 Table 1, App C Table 7`）
固定 `Checkpoint-binary` 反馈、同时摄取成败轨迹（`Both`）、单轮巩固（`R1`），全量结果如下〔图表 `Table 1` & 附录 `App C Table 7`〕：

| 模型底座 | 巩固方法 | TheAgentCompany<br>`Checkpoint Pass` (`542`) | TheAgentCompany<br>`Fully Passed` (`127`) | TheAgentCompany<br>`Store (KB)` | TheAgentCompany<br>`Consol. Cost` | $\tau^2$-Bench Retail<br>`Checkpoint Pass` (`192`) | $\tau^2$-Bench Retail<br>`Fully Passed` (`40`) | $\tau^2$-Bench<br>`Store (KB)` |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Claude Opus 4.6** | `No Memory` | 317/542 (`58.5%`) | 46/127 (`36.2%`) | n/a | n/a | 66.7% | 40.0% | n/a |
| | `No Consolidation` | 332/542 (`61.3%`, `+2.8`) | 51/127 (`40.2%`) | 7,979 | n/a | 69.3% (`+2.6`) | 42.5% | 1,428 |
| | `SkillX` | 354/542 (`65.3%`, `+6.8`) | 58/127 (`45.7%`) | 1,125 | \$173 | **81.2%** (`+14.5`) | 50.0% | 336 |
| | `Insights` | 356/542 (`65.7%`, `+7.2`) | 58/127 (`45.7%`) | 396 | **\$148** | 78.1% (`+11.4`) | **55.0%** | 96 |
| | `WASP-Mem: Schema Form-ED` | 356/542 (`65.7%`, `+7.2`) | 57/127 (`44.9%`) | 789 | \$380 | 79.7% (`+13.0`) | 52.5% | 656 |
| | `WASP-Mem: Schema Form` | 359/542 (`66.2%`, `+7.7`) | **62/127 (`48.8%`)** | 565 | \$230 | 77.6% (`+10.9`) | 42.5% | 252 |
| | **`WASP-Mem: Free Form`** | **392/542 (`72.3%`, `+13.8`)** | 61/127 (`48.0%`) | **234** | \$198 | **81.2%** (`+14.5`) | **55.0%** | **92** |
| **GPT-5.4** | `No Memory` | 325/542 (`60.0%`) | 51/127 (`40.2%`) | n/a | n/a | 65.1% | 35.0% | n/a |
| | `No Consolidation` | 339/542 (`62.5%`, `+2.5`) | 54/127 (`42.5%`) | 8,208 | n/a | 62.0% (`-3.1`) | 42.5% | 1,953 |
| | `SkillX` | 364/542 (`67.2%`, `+7.2`) | 64/127 (`50.4%`) | 1,161 | \$171 | 69.3% (`+4.2`) | 45.0% | 425 |
| | `Insights` | 359/542 (`66.2%`, `+6.2`) | 62/127 (`48.8%`) | 399 | **\$146** | 67.7% (`+2.6`) | 52.5% | **112** |
| | `WASP-Mem: Schema Form-ED` | 363/542 (`67.0%`, `+7.0`) | 63/127 (`49.6%`) | 808 | \$370 | 71.9% (`+6.8`) | 52.5% | 880 |
| | `WASP-Mem: Schema Form` | 368/542 (`67.9%`, `+7.9`) | 64/127 (`50.4%`) | 592 | \$229 | 71.4% (`+6.3`) | 47.5% | 303 |
| | **`WASP-Mem: Free Form`** | **393/542 (`72.5%`, `+12.5`)** | **66/127 (`52.0%`)** | **233** | \$202 | **76.6%** (`+11.5`) | **60.0%** (`+25.0`) | 123 |
| **GLM-5** | `No Memory` | 319/542 (`58.9%`) | 49/127 (`38.6%`) | n/a | n/a | 47.4% | 25.0% | n/a |
| | `No Consolidation` | 335/542 (`61.8%`, `+2.9`) | 52/127 (`40.9%`) | 8,480 | n/a | 46.4% (`-1.0`) | 30.0% | 1,461 |
| | `SkillX` | 356/542 (`65.7%`, `+6.8`) | 59/127 (`46.5%`) | 1,187 | **\$79** | 53.1% (`+5.7`) | 32.5% | 315 |
| | `Insights` | 357/542 (`65.9%`, `+7.0`) | 60/127 (`47.2%`) | 441 | \$87 | 51.6% (`+4.2`) | 37.5% | **82** |
| | `WASP-Mem: Schema Form-ED` | 356/542 (`65.7%`, `+6.8`) | 59/127 (`46.5%`) | 838 | \$197 | 53.1% (`+5.7`) | 27.5% | 557 |
| | `WASP-Mem: Schema Form` | 361/542 (`66.6%`, `+7.7`) | 64/127 (`50.4%`) | 599 | \$117 | 56.2% (`+8.8`) | 37.5% | 323 |
| | **`WASP-Mem: Free Form`** | **393/542 (`72.5%`, `+13.6`)** | **66/127 (`52.0%`)** | **255** | \$118 | **58.3%** (`+10.9`) | **42.5%** (`+17.5`) | 92 |

**核心机理——巩固作为信息过滤器（`The Filter Hypothesis`）与四类典型行为（`Sec 4.2:136–146, App D.6 Table 13`）**：
为什么 `Free Form` 相比人为规定 `Schema Form` 与确定性规则去重 `Schema Form-ED`，不仅存储体积缩小了 **$57\% \sim 71\%$**（`233–255 KB` 对比 `565–838 KB`），检查点通过率反而高出 **`4.6 ~ 6.8` 个百分点**？作者通过定性审计生成库（`App D.6 Table 13`）指出了“**过滤不足（`Under-filtering`）**”与“**过度过滤（`Over-filtering`）**”的并发退化：
1. **隐式增量合并（`Implicit Merge` —— `Free Form` 优势）**：`Free Form` 在写入前先读取现有 Wiki，当后续任务遇到新的 GitLab API 分页与异常处理证据时，直接修订同一个 GitLab 认证页面，使多次试验沉淀为一篇完备规程。
2. **独立提取导致的碎片冗余（`Independent Duplication` —— `SkillX / Insights` 缺陷）**：由于按轨迹独立提取且无跨会话去重，`SkillX` 为实质相同的 GitLab API 认证流程创建了 **15 个互相独立的页面**，导致检索器被冗余碎片淹没（`Under-filtering`）。
3. **预设 Schema 截断关键实现细节（`Schema Omission` —— `Schema Form` 缺陷）**：在任务 `ds-stock-analysis-slides` 中，`Schema Form` 的固定字段只记录了抽象步骤名称，却丢弃了 `Free Form` 保留的具体代码片段与格式规范，导致智能体“知道步骤名却写不出可执行命令”（`Over-filtering`）。
4. **确定性规则归一化引发的错误强合并（`Explicit False Merge` —— `Schema Form-ED` 缺陷）**：`Schema Form-ED` 的确定性脚本将“用 Python 批改机器学习试卷”与“用 Python 抽取视频帧”统统归一化映射到同一个动作标识符 `action-bash-run-python` 下并强制 LLM 合并，导致风马牛不相及的操作指令被绑定检索。

#### 实验二与实验三：反馈丰富度阶梯 × 成败轨迹准入范围的正交交互（`Sec 4.3, App C Table 8 & Table 9`）

作者在 `Free Form (R1)` 下交叉对比了四级反馈（`Self-Judge` $\rightarrow$ `Task-binary` $\rightarrow$ `Checkpoint-binary` $\rightarrow$ `Checkpoint-binary + Human` 自然语言故障诊断）与两类准入范围（仅成功 `Success-only` 对比 成败双收 `Both`）〔附录 `App C Table 8 & Table 9`〕：

| 模型底座 | 反馈类型（`Feedback Type`） | `Success-only`（仅摄取成功）<br>`Checkpoint Pass` \| `Full Pass` \| `Store` | `Both`（同时摄取成功与失败）<br>`Checkpoint Pass` \| `Full Pass` \| `Store` | 引入失败轨迹的净增益<br>$\Delta_{\text{Both - Success}}$ (`CP` / `Full`) |
| :--- | :--- | :---: | :---: | :---: |
| **Claude Opus 4.6** | `Self-Judge`（纯模型自评） | 351/542 (`64.8%`) \| `42.5%` \| 193 KB | 352/542 (`64.9%`) \| `46.5%` \| 212 KB | `+0.1 pp` / `+4.0 pp`（几乎无增益） |
| | `Task-binary`（任务级二值成败） | — | 391/542 (`72.1%`) \| `50.4%` \| 237 KB | — |
| | `Checkpoint-binary`（检查点级二值） | — | 392/542 (`72.3%`) \| `48.0%` \| 234 KB | `+6.1 pp`（相对 `Success-only`） |
| | **`CP-binary + Human`（含人工诊断）** | 359/542 (`66.2%`) \| `41.7%` \| 119 KB | **411/542 (`75.8%`)** \| **`55.9%`** \| 328 KB | **`+9.6 pp` / `+14.2 pp`** |
| **GPT-5.4** | `Self-Judge`（纯模型自评） | 356/542 (`65.7%`) \| `45.7%` \| 211 KB | 352/542 (`64.9%`) \| `44.1%` \| 200 KB | **`-0.8 pp` / `-1.6 pp`（负迁移！）** |
| | `Task-binary`（任务级二值成败） | — | 384/542 (`70.8%`) \| `52.0%` \| 224 KB | — |
| | `Checkpoint-binary`（检查点级二值） | — | 393/542 (`72.5%`) \| `52.0%` \| 233 KB | `+5.9 pp`（相对 `Success-only`） |
| | **`CP-binary + Human`（含人工诊断）** | 361/542 (`66.6%`) \| `47.2%` \| 135 KB | **418/542 (`77.1%`)** \| **`61.4%`** \| 335 KB | **`+10.5 pp` / `+14.2 pp`** |
| **GLM-5** | `Self-Judge`（纯模型自评） | 351/542 (`64.8%`) \| `44.1%` \| 212 KB | 349/542 (`64.4%`) \| `44.1%` \| 235 KB | **`-0.4 pp` / `0.0 pp`（负迁移！）** |
| | `Task-binary`（任务级二值成败） | — | 388/542 (`71.6%`) \| `50.4%` \| 256 KB | — |
| | `Checkpoint-binary`（检查点级二值） | — | 393/542 (`72.5%`) \| `52.0%` \| 255 KB | `+5.7 pp`（相对 `Success-only`） |
| | **`CP-binary + Human`（含人工诊断）** | 362/542 (`66.8%`) \| `43.3%` \| 140 KB | **414/542 (`76.4%`)** \| **`56.7%`** \| 343 KB | **`+9.6 pp` / `+13.4 pp`** |

**核心实证结论（`Sec 4.3:164–172`）**：
1. **“失败轨迹并非天然有用，是诊断性反馈让失败变得可学习（Feedback Makes Failure Learnable）”**：
   - 在缺乏外部真值的 `Self-Judge` 下，引入失败轨迹（`Both`）不仅没有任何帮助，反而在 `GPT-5.4` 与 `GLM-5` 上引起 `-0.8 pp` 与 `-0.4 pp` 的倒退——因为模型自评无法区分“偶然的错误尝试”与“可复用的避坑教训”，盲目摄取失败只会向记忆库注入噪声。
   - 反之，当配备 `Checkpoint-binary + Human` 故障诊断时，引入失败轨迹使检查点通过率暴涨 **`+9.6 ~ +10.5 pp`**，完整任务通关率暴涨 **`+13.4 ~ +14.2 pp`**！
2. **人工诊断的价值几乎 100% 集中在“把失败轨迹转化为修正规则”上**：如果只摄取成功轨迹（`Success-only`），无论把反馈从 `Self-Judge` 升级到多么昂贵的 `CP-binary + Human`，检查点通过率仅微弱变化 `+0.9 ~ +2.0 pp`（`64.8% → 66.2%`）。只有把人工诊断用在失败轨迹上，才能释放出 `+10.9 ~ +12.2 pp` 的跃升。

#### 实验四：多轮迭代精炼（`R0 → R4`）与轨迹数量控制实验（`Sec 4.4, App C Tables 10–12`）

| 模型底座 | 反馈条件 | `R0`（无记忆） | `R1`（第 1 轮巩固） | `R2`（第 2 轮巩固） | `R3`（第 3 轮巩固） | `R4`（第 4 轮巩固） | `Pooled Insights`（一次性合并 R0–R4 共 635 条轨迹） |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Claude Opus 4.6** | `CP-binary + Human` | `58.5%` (46/127) | `75.8%` (71/127) | `79.3%` (79/127) | `82.3%` (86/127) | **`85.6%` (92/127)** | `79.5%` (78/127，仅相当于 `Free Form R2`) |
| | `Self-Judge` | `58.5%` (46/127) | `64.9%` (59/127) | `64.4%` (52/127) | `66.8%` (56/127) | `68.8%` (60/127) | — |
| **GPT-5.4** | `CP-binary + Human` | `60.0%` (51/127) | `77.1%` (78/127) | `80.8%` (86/127) | `82.8%` (91/127) | **`86.7%` (99/127)** | `79.9%` (84/127，比 `Free Form R4` 低 `-6.8 pp`) |
| | `Self-Judge` | `60.0%` (51/127) | `64.9%` (56/127) | `66.1%` (58/127) | **`67.2%` (62/127)** | `67.0%` (62/127) | — |
| **GLM-5** | `CP-binary + Human` | `58.9%` (49/127) | `76.4%` (72/127) | `79.9%` (82/127) | `83.2%` (87/127) | **`86.3%` (94/127)** | `79.2%` (81/127，比 `Free Form R4` 低 `-7.1 pp`) |
| | `Self-Judge` | `58.9%` (49/127) | `64.4%` (56/127) | `64.0%` (55/127) | `63.7%` (55/127) | `65.5%` (57/127) | — |

**核心实证结论（`Sec 4.4:190–198, App D.2:371–374`）**：
1. **1 轮人工故障诊断远胜 4 轮模型自评（`1 Round Human Diagnosis > 4 Rounds Self-Judge`）**：仅经过 **1 轮**人工诊断巩固（`R1`：检查点通过率 `75.8% ~ 77.1%`，耗时约 6 小时标注，见 `App E:422`），就全面碾压了跑满 **4 轮** `Self-Judge` 的最终结果（`65.5% ~ 68.8%`），领先幅度高达 **`+7.0 ~ +10.9 pp`**。
2. **多轮诊断将局部检查点修复转化为端到端通关率倍增**：在 `Claude Opus 4.6` 上，随着前序步骤被固化、深层卡点依次暴露并被诊断修复，127 个任务中的满分通关数从 `R0` 的 **46 个（`36.2%`）**单调攀升至 `R1` **71 个** $\rightarrow$ `R2` **79 个** $\rightarrow$ `R3` **86 个** $\rightarrow$ `R4` **92 个（`72.4%`）**（`GPT-5.4` 更是达到 **99/127 = `78.0%`**）。
3. **存储与执行成本双降（`App E Table 14`）**：引入 `Free Form WASP-Mem` 后，单批次 127 个任务的平均执行 API 成本从无记忆的 `\$106.6`（Claude）/ `\$108.5`（GPT-5.4）下降至 `\$88.9` / `\$87.1`（因为避免了盲目试错重试）。

---

<a id="c14-2"></a>

## 14.2 Part II — SPEM：双层结构感知程序记忆、反向切片 DAG 提纯与 Skill-GNN 选技（`2610.26995`）

### 1. 大规模技能库下的四大瓶颈与 SPEM 双层架构（`Sec 1–3, Fig. 1`）

当智能体面临包含数百至数千个可复用技能（`Skills`）的技能库时，现有方案陷入两难：① 全量加载（`Vanilla Skills`）导致上下文膨胀、Token 与延迟暴增且引发 `Lost-in-the-Middle`；② 扁平向量检索（`Vector Skills`）只看表面语义相似，忽略了技能间的**前置条件、执行顺序、状态转移与数据流依赖**；③ 即使在单次执行中规划出了正确的技能组合，执行结束后即被丢弃，下次遇到同类任务仍需从头推导〔正文 `Sec 1:144–153`〕。

为此，**SPEM（Structure-Aware Procedural Memory）**构建了由**原子技能记忆（`Atomic Skill Memory` $\mathcal{M}_a$）**与**技能有向无环图记忆（`Skill-DAG Memory` $\mathcal{M}_d$）**组成的双层程序记忆框架〔正文 `Sec 3.1:251–297`，附录 `App A.1 Alg. 1 & App A.2 Table 1`〕：

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                  SPEM: Dual-Layer Procedural Memory & Skill-GNN Architecture                    │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                 │
│   ┌──────────────────────────────────────────┐   ┌───────────────────────────────────────────┐  │
│   │ 1. Atomic Skill Memory M_a = {s_i}_{i=1}^N│   │ 2. Skill-DAG Memory M_d = {G_j}_{j=1}^M   │  │
│   │  s_i = (d_i, e_i, σ_i):                  │   │  G_j = (V_j, E_j, e_j, m_j):              │  │
│   │  • Core: skill_id, name, 1-line summary  │   │  • V_j: phase/skill nodes & arg bindings  │  │
│   │  • Interface: I/O schema, tooling, device│   │  • E_j: temporal / data-flow / control    │  │
│   │  • Stats σ_i: EMA success_rate, exec_cost│   │  • m_j: structural_signature, reliability │  │
│   └────────────────────┬─────────────────────┘   └─────────────────────┬─────────────────────┘  │
│                        │                                               │                        │
│                        └───────────────────────┬───────────────────────┘                        │
│                                                ▼                                                │
│   Incoming Task q (Embedding e_q) ──► [Step 1: Template Match C_d(q) = {G_j | sim(e_q,e_j) ≥ τ}]│
│                                        (Threshold τ = 0.80)                                     │
│                                                │                                                │
│                   ┌────────────────────────────┴────────────────────────────┐                   │
│                   ▼ (If C_d(q) ≠ ∅: High-Confidence Hit)                    ▼ (If C_d(q) = ∅ OR │
│       [Direct Template Reuse]                                    Replanning / Failure Triggered)│
│       Inject compact Skill-DAG backbone                         [Step 2: Atomic Top-K C_a(q)]   │
│       (Prunes 54.9% steps, cuts tokens by 49.8%!)                           │                   │
│                   │                                                         ▼                   │
│                   │                                      [Step 3: Task-Conditioned Graph G_q]   │
│                   │                                      Nodes: Task, State, History, Skills    │
│                   │                                      Skill-GNN (2-layer Hetero-GNN, 1.5~2ms)│
│                   │                                      Scores next-skill utility p_i = f(h_i) │
│                   └────────────────────────────┬────────────────────────────┘                   │
│                                                ▼                                                │
│                                   [LLM Executor Action Loop]                                    │
│                                                │                                                │
│                   ┌────────────────────────────┴────────────────────────────┐                   │
│                   ▼ (If Episode Succeeds)                                   ▼ (If Episode Fails)│
│       [Trajectory-DAG Extraction (Fig. 2)]                      [Negative Feedback Protection]  │
│       • Build execution graph G_τ = (V_τ, E_τ)                  • Do NOT create new Skill-DAG!  │
│       • Backward slicing: V*_τ = {v | v ──►* v_succ}            • Only decay EMA reliability    │
│       • Prune failed branches/no-ops via u_t score                stats σ_i / m_j of used items │
│       • Merge contiguous steps & repair edges ──► Write G*_τ                                    │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2. 三大核心技术模块与数学形式化（`Sec 3.1–3.3, App A.1–A.5`）

#### (1) 双层记忆 Schema 与两级优先级检索（`Sec 3.1 Eq. 1–6, App A.2 Table 1`）
1. **原子技能记忆 $\mathcal{M}_a = \{s_i\}_{i=1}^N$**：每个技能表示为三元组 $s_i = (d_i, e_i, \sigma_i)$〔正文 `Eq. 1–2`〕：
   - $d_i$（静态身份与接口元数据）：包含 `skill_id`、`name`、`one_line_capability`、`input_schema`、`output_schema`、`tooling` 与 `device_requirements`；其中**检索嵌入 $e_i$ 仅由 `name + one_line_capability` 编码生成**，以聚焦面向任务的功能匹配，而完整技能文档 `raw_content` 仅在命中后才注入提示词〔附录 `App A.2:108–112`〕；
   - $\sigma_i$（在线动态反馈统计）：记录 `usage_count`、`success_rate`、`exec_cost`、`last_used_at` 与 `preference_score`，在每次执行后通过**指数移动平均（`EMA`）**保守更新〔附录 `App A.2:117–123`〕。
2. **技能 DAG 记忆 $\mathcal{M}_d = \{G_j\}_{j=1}^M$**：每个模板表示为四元组 $G_j = (V_j, E_j, e_j, m_j)$，其中 $V_j$ 为绑定了原子技能与参数槽位的阶段节点，$E_j$ 为有向依赖边（含时序 `temporal`、数据流 `data-flow`、控制流 `control-flow` 与参数依赖），$e_j$ 为源任务嵌入，$m_j$ 包含用于去重合并的**结构签名（`structural_signature`）**、父模板血缘 `parent_dag_ids` 与在线成功率〔正文 `Eq. 3–4`，附录 `App A.2:125–131, Table 1`〕。
3. **模板优先、原子兜底的两级检索（`Eq. 5–6`）**：给定新任务 $q$（嵌入 $e_q$），首先在 $\mathcal{M}_d$ 中检索相似度超过阈值 $\tau = 0.80$（`App B Table 4`）的高置信度模板：
   $$\mathcal{C}_d(q) = \left\{G_j \in \mathcal{M}_d \;\middle|\; \operatorname{sim}(e_q, e_j) \ge \tau\right\}$$
   若 $\mathcal{C}_d(q) \neq \emptyset$，直接注入最高分 `Skill-DAG` 骨架；若未命中（或执行中途触发重规划/动作失败），则从 $\mathcal{M}_a$ 召回 Top-$K$ 原子候选集 $\mathcal{C}_a(q) = \operatorname{TopK}_{s_i \in \mathcal{M}_a} \operatorname{sim}(e_q, e_i)$ 并交由 `Skill-GNN` 做状态感知重排。

#### (2) 动态候选图构建、Skill-GNN 状态感知打分与零样本冷启动（`Sec 3.2 Eq. 7–11, App A.4–A.5`）
不同于绑定在固定全局静态图上的转导式（Transductive）图模型，`Skill-GNN` 采用**归纳式（Inductive）动态子图推理**〔正文 `Sec 3.2:303–338`，附录 `App A.4:227`〕：
1. **任务条件化候选图 $\mathcal{G}_q = (\mathcal{V}_q, \mathcal{E}_q, \mathcal{R})$**：节点集 $\mathcal{V}_q$ 包含当前任务节点、当前环境状态节点、已执行历史节点以及 Top-$K$ 候选技能节点（节点特征拼接语义嵌入 $e_i$ 与动态统计特征 $\sigma_i$）；有向边集 $\mathcal{E}_q$ 涵盖任务—技能、状态—技能、技能—技能等多类关系 $r \in \mathcal{R}$。
2. **异构关系消息传递与三头预测（`Eq. 8–9, App A.5`）**：经过 $L=2$ 层异构图神经网络（`Hetero-GNN`，隐藏层维度 `128`，单次推理仅需 **`2.42 ms`**，若用 `GIN` 仅需 **`1.47 ms`**，见 `App C Table 2`）：
   $$h_i^{(\ell+1)} = \phi_\ell\!\left(h_i^{(\ell)},\; \sum_{r \in \mathcal{R}} \sum_{j \in \mathcal{N}_r(i)} \alpha_{ij}^r W_r^{(\ell)} h_j^{(\ell)}\right), \qquad p_i = f_\theta\!\left(h_i^{(L)}\right)$$
   训练时联合优化三个轻量级预测头〔附录 `App A.5:271–307`〕：
   $$\mathcal{L} = \lambda_{\mathrm{next}} \mathcal{L}_{\mathrm{next}} + \lambda_{\mathrm{value}} \mathcal{L}_{\mathrm{value}} + \lambda_{\mathrm{edge}} \mathcal{L}_{\mathrm{edge}}$$
   其中 $\mathcal{L}_{\mathrm{next}}$ 为基于成功轨迹前缀 $P_k = (v_1, \dots, v_{k-1})$ 预测下一步技能 $v_k$ 的交叉熵损失，$\mathcal{L}_{\mathrm{value}}$ 为预测候选图整体成功效用的 Smooth-$L_1$ 损失，$\mathcal{L}_{\mathrm{edge}}$ 为预测两技能间是否存在依赖边的二元交叉熵损失。
3. **无轨迹场景下的技能库级冷启动（`Library-Level Cold Start`，`Eq. 10–11, App A.4–A.5, Fig. 4`）**：当部署初期完全没有目标域执行轨迹（如 `SkillsBench`）时，仅利用技能库元数据从每个技能的名称、一句话能力描述、I/O Schema 生成伪查询 $\widetilde{\mathcal{D}}_0 = \{(\tilde{q}_i, s_i)\}_{s_i \in \mathcal{M}_a}$，并基于共享工具、标签与接口兼容性诱导弱技能关系边 $\widetilde{\mathcal{E}}_0 = \{(s_i, r, s_j) \mid \kappa_r(s_i, s_j) \ge \eta_r\}$ 预热 `Skill-GNN`，随着线上成功轨迹积累再平滑过渡到轨迹前缀监督。

#### (3) 基于反向切片与效用评分的轨迹 DAG 提纯（`Trajectory-DAG Extraction`，`Sec 3.3 Eq. 12–14, App A.3, Fig. 2`）
智能体成功完成任务后的原始轨迹 $\tau = \{(a_t, o_t, r_t, y_t, b_t)\}_{t=1}^T$ 往往混杂着大量试错弯路、空操作（`no-op`）与冗余探索（在 `ALFWorld` 上平均长达 `13.4` 步）。若直接原样存入记忆库（对应 `w/o DAG Extraction`），不仅浪费 Token 还会误导后续执行。`SPEM` 提出四步提纯流水线〔正文 `Sec 3.3:370–385`，附录 `App A.3:161–210`〕：
1. **构建初始执行图 $G_\tau = (V_\tau, E_\tau)$**：解析每步动作动词、参数跨度与关联实体，连接时序边、共享实体/参数依赖边与终态可达边；
2. **从成功终态节点 $v_{\mathrm{succ}}$ 反向切片（`Backward Slicing`）**：仅保留通过时序或实体依赖路径对最终成功有因果贡献的前置节点集合：
   $$V^*_\tau = \left\{v \in V_\tau \;\middle|\; v \to^* v_{\mathrm{succ}}\right\}$$
3. **步骤有用性评分剪枝（`Step Usefulness Pruning`）**：为每步计算可解释效用分以剪除失敗分支、空操作与重复探测〔附录 `App A.3:188–196`〕：
   $$u_t = \operatorname{clip}_{[0, 1]}\!\left(\mathbf{w}^+ \cdot \phi^+(t) - \mathbf{w}^- \cdot \phi^-(t)\right)$$
   其中正向特征 $\phi^+(t)$ 衡量任务推进、成功信号、新颖度与依赖支撑度，负向特征 $\phi^-(t)$ 惩罚显式报错、无状态变化的 `no-op` 与重复探索；
4. **同意图连续步骤归并与依赖边修复**：将具有相同程序意图的连续步骤折叠为阶段级（Phase-level）节点，形成紧凑骨架 $G^*_\tau = (V^*_\tau, E^*_\tau)$ 写回 $\mathcal{M}_d$（将平均步数从 `13.4` 步压缩至 **`6.0` 步，剪除 `54.9%` 的冗余动作**，见 `Sec 4.3:494–496 & Fig. 3(a)`）。**失败的执行绝不生成正样本 DAG 模板，仅下调所调用技能或模板的可靠性统计分**〔附录 `App A.3:208–210`〕。

### 3. 全量实验结果、模板复用分析与消融实验（`Sec 4, Tables 1–3, App C`）

#### (1) SkillsBench（200 技能库）与 ALFWorld（37 技能库）主实验对比（`Table 1`）

| 模型底座 | 方法名称 | SkillsBench<br>Reward $R \uparrow$ (%) | SkillsBench<br>Input Tokens $T \downarrow$ | SkillsBench<br>Runtime $S \downarrow$ (s) | ALFWorld<br>Success $\uparrow$ (%) | ALFWorld<br>Steps $\downarrow$ | ALFWorld<br>Tokens $\downarrow$ | ALFWorld<br>Runtime $\downarrow$ (s) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **MiniMax-M2.7** | `Vanilla Skills`（全量加载） | 21.61 | 798,323 | 469.3 | 59.3 | 21.24 | 152,242.1 | 55.95s |
| | `Vector Skills`（扁平向量 Top-$K$） | 13.07 | 722,765 | 439.5 | 63.9 | 18.36 | 55,816.6 | 55.71s |
| | `GoS`（静态技能依赖图检索） | 23.50 | 735,113 | 399.4 | 68.6 | 20.26 | 62,033.9 | 54.22s |
| | `SkillDAG`（动态类型演化图） | **27.09** | 979,781 | 476.1 | 63.3 | **16.37** | 296,512.4 | 137.38s |
| | **`SPEM (Ours)`** | **25.14**（次优） | **721,926**（`-26.3%` 对比 SkillDAG） | **360.5**（`-24.3%`） | **70.7** | 18.29 | **45,785.7**（`-84.6%` 对比 SkillDAG） | **51.56s** |
| **GPT-5.2-Codex** | `Vanilla Skills`（全量加载） | 28.87 | 2,785,485 | 686.8 | 84.9 | 14.65 | 99,023.9 | 84.57s |
| | `Vector Skills`（扁平向量 Top-$K$） | 23.44 | 1,047,698 | 763.4 | 83.7 | 16.18 | **47,357.3** | 80.43s |
| | `GoS`（静态技能依赖图检索） | 37.50 | 1,162,375 | 705.2 | 85.3 | 16.46 | 48,805.6 | 71.23s |
| | `SkillDAG`（动态类型演化图） | 34.38 | 1,370,270 | 861.1 | 85.7 | **11.73** | 105,449.9 | 169.10s |
| | **`SPEM (Ours)`** | **38.38** | **980,029**（`-15.7%` 对比 GoS） | **618.7**（`-12.3%`） | **87.1** | 15.07 | 47,409.1（`-55.0%` 对比 SkillDAG） | **66.01s** |

#### (2) Skill-DAG 模板命中率与组件消融实验（`Table 2 & Table 3`）
1. **ALFWorld 模板命中与复用统计（`Table 2`）**：
   - 在 `MiniMax-M2.7` 下，模板命中率（`Hit`）达 **`56.43%`**（未命中回退原子检索 `Fallback = 43.57%`），命中模板的任务成功率达 **`74.68%`**；
   - 在 `GPT-5.2-Codex` 下，模板命中率达 **`60.71%`**（`Fallback = 39.29%`），命中模板的任务成功率高达 **`85.88%`**（无效模板率仅 `14.12%`）。
   - 在精确模板重放对照实验（`Fig. 3(b)`）中，注入提纯后的 `Skill-DAG` 骨架在保持 100% 复现成功的同时，将平均执行步数从 `11.42` 降至 **`6.26`（减少 `45.2%`）**，Token 消耗从 `23.77K` 降至 **`11.93K`（减少 `49.8%`）**，耗时从 `28.01s` 降至 **`20.88s`（减少 `25.5%`）**。
2. **ALFWorld 核心模块消融（`Table 3`，基于 `MiniMax-M2.7`）**：

   | 消融变体 | 成功率 `Succ. (%)` $\uparrow$ | 平均步数 `Steps` $\downarrow$ | 平均耗时 `Time (s)` $\downarrow$ | 平均消耗 `Tokens` $\downarrow$ | 缺失模块导致的性能退化归因 |
   | :--- | :---: | :---: | :---: | :---: | :--- |
   | `w/o Skill-DAG`（移除 DAG 模板记忆） | 56.8%（`-13.9%`） | 23.0 | 55.4s | 67.5K | 失去高层子目标顺序引导，智能体被迫在长视距任务中反复试错探索 |
   | `w/o Skill-GNN`（仅靠向量检索程序记忆） | 58.3%（`-12.4%`） | 20.3 | 54.7s | 53.6K | 当执行状态变化或前置动作失败时，静态语义检索无法根据实时状态调整技能排序 |
   | `w/o DAG Extraction`（存完整轨迹而非提纯骨架） | 63.0%（`-7.7%`） | 18.9 | 57.8s | 56.2K | 原始轨迹中的冗余探索与环境特定噪声污染了提示词，拉低成功率并推高开销 |
   | **`Full SPEM`（完整双层记忆 + GNN + 反向切片）** | **`70.7%`** | **`18.3`** | **`51.6s`** | **`45.8K`** | 三组件协同实现最高成功率与最低 Token/时间开销 |

3. **扩展至 2,000 个技能库时的检索退化对比（`Sec 4.4:533–535, Fig. 3(c)–(d)`）**：
   当技能库规模从数十个扩展至 **2,000 个技能**时，纯向量检索（`Retrieval-only`）因语义拥挤导致 `Hit@1` 跌至 **`0.0`**、`MRR` 仅 `0.112`；而叠加 `Skill-GNN` 结构化上下文重排后，在 2,000 个技能下仍保持 **`Hit@1 = 0.51`**、**`MRR = 0.573`**（提升超 **5 倍**）。

---

<a id="c14-3"></a>

## 14.3 双篇横向协同与对联接 Agent 主报告（3.3.3 / 3.3.4 / 3.4 节）的工程启发

将 `WASP-Mem` 与 `SPEM` 结合对读，恰好补齐了我们主报告 [`storyline_and_evaluation_merged_technical_route_report.html`](../../../../.lavish/storyline_and_evaluation_merged_technical_route_report.html) 中**程序记忆（`Procedural Memory`）从“轨迹提纯 $\rightarrow$ 跨会话去重整合 $\rightarrow$ 诊断驱动修正 $\rightarrow$ 运行时状态感知召回”**的全链路设计：

1. **轨迹入库前必须做“反向切片骨架提纯（`Backward Slicing`）”而非原样塞入（来自 `SPEM Sec 3.3`）**：
   - 在多轮排障对话与网元调参过程中，智能体往往经历了多轮参数试探、查询空操作甚至中途改口才最终达成顺畅运行。若像 `w/o DAG Extraction` 那样将整段含噪轨迹原样存入经验库，成功率会下跌 `7.7%` 且 Token 开销激增。
   - **落地动作**：在我们的慢路径经验沉淀模块中，以最终网元顺畅回执 $v_{\mathrm{succ}}$ 为终点做反向因果切片（$V^*_\tau = \{v \mid v \to^* v_{\mathrm{succ}}\}$），剔除中途被用户否决的废单分支与冗余查询，仅将“触发症状 $\rightarrow$ 关键消歧槽位 $\rightarrow$ 最终生效参数组合”提纯为紧凑的 `Skill-DAG` 骨架。
2. **避免死板枚举 Schema 与粗暴脚本同义归并，采用“先读后写”的隐式上下文去重（来自 `WASP-Mem Sec 4.2 & Table 13`）**：
   - `WASP-Mem` 的消融实验给我们敲响了警钟：① 过于死板的固定字段模板（`Schema Form`）会削足适履，把关键的网元特殊参数细节过滤掉（`Over-filtering`）；② 基于表层工具名或命令名的确定性脚本强合并（`Schema Form-ED`）会把“同调一个接口但业务目的完全不同”的规程错误揉成一团（`Explicit False Merge`）。
   - **落地动作**：保留核心路由索引（对应 `index.md` + 业务应用分类锚点），但在沉淀具体排障规程正文时采用“**先检索读取现有规程页 $\rightarrow$ 由巩固智能体结合完整上下文判断是追加异常恢复分支（`Implicit Merge`）还是新建独立规程**”，并允许保留轻量级自由文本注解以承载特殊基站/时段的边角料约束。
3. **区分“成功轨迹自固化”与“失败轨迹的诊断转化”（来自 `WASP-Mem Sec 4.3` 与 `SPEM App A.3`）**：
   - 两篇论文在对待失败轨迹上达成高度一致：**没有任何诊断定位信号的失败轨迹绝不能作为正向模板入库**（`SPEM` 仅用其衰减可靠性分；`WASP-Mem` 证明在 `Self-Judge` 下引入失败轨迹会产生负迁移）。
   - 但当拥有**检查点级定位回执（如网元底层具体哪个指标超标/哪一步 API 报错）或慢路径用户明确指出卡顿原因（对应 `CP-binary + Human Diagnosis`）**时，失败轨迹就成为填补“残差程序知识缺口”的最宝贵资产，1 轮诊断修正即可带来 `+10.9 ~ +12.2 pp` 的跃升。
4. **“高频模板直通（Fast Template Hit）”与“异常状态图重排（State-Conditioned Recovery）”双轨协同（来自 `SPEM Sec 3.1–3.2 & App D Case Studies`）**：
   - 正常高频场景直接命中高置信度 `Skill-DAG` 模板（$\operatorname{sim} \ge 0.80$），一步到位输出完整参数配置（节省近 `50%` Token 与步数）；
   - 当模板未命中，或按默认模板下发单据后收到网元异常回执（如 `ALFWorld` 中未开冰箱直接冷却失败）时，立即将“当前目标 + 失败动作 + 最新环境观测”组成状态节点，触发状态感知的子目标/恢复技能重检索。

---

← 返回 [精读笔记索引](../reading_notes.md)　·　[论文主目录](../../README.md)

# [10] Memory in the Age of AI Agents: A Survey — Forms, Functions and Dynamics (Dec 2025 / Jan 2026) — 深度精读与三维正交分类体系对齐

- **标题**：*Memory in the Age of AI Agents: A Survey — Forms, Functions and Dynamics*
- **作者与机构**：Yuyang Hu, Shichun Liu, Yanwei Yue, Guibin Zhang, Boyang Liu, Fangyi Zhu, Jiahang Lin, Honglin Guo, Shihan Dou, Zhiheng Xi, Senjie Jin, Jiejun Tan, Yanbin Yin, Jiongnan Liu, Zeyu Zhang, Zhongxiang Sun, Yutao Zhu, Hao Sun, Boci Peng, Zhenrong Cheng, Xuanbo Fan, Jiaxin Guo, Xinlei Yu, Zhenhong Zhou, Zewen Hu, Jiahao Huo, Junhao Wang,肆, Yu-Gang Jiang, Xuanjing Huang, Ji-Rong Wen, Zhicheng Dou, Philip Torr, Shuicheng Yan 等 47 位作者（新加坡国立大学 NUS、中国人民大学高瓴人工智能学院 RUC、复旦大学、北京大学、南洋理工大学 NTU、同济大学、UCSD、HKUST-GZ、牛津大学、OPPO 等）
- **发表时间与状态**：`arXiv:2512.13564v2`（v1: 2025 年 12 月 15 日，v2: 2026 年 1 月，全长 107 页、涵盖 800+ 篇前沿文献）
- **本地 PDF 与转换稿路径**：
  - [Memory_Age_of_AI_Agents_2025.pdf](file:///D:/coding/sharing/papers/memory/Memory_Age_of_AI_Agents_2025.pdf)
  - [2512.13564.pdf](file:///D:/coding/sharing/papers/memory/2512.13564/pdf/2512.13564.pdf)
  - [2512.13564.md](file:///D:/coding/sharing/papers/memory/2512.13564/2512.13564.md)
- **开源列表仓库**：[Shichun-Liu/Agent-Memory-Paper-List](https://github.com/Shichun-Liu/Agent-Memory-Paper-List)（本地同步索引：[README.md](file:///D:/coding/sharing/papers/repos/Agent-Memory-Paper-List/README.md)）

---

## 一、论文核心定位与解决的分类学痛点 (`Sec 1–2`)

### 1.1 现有智能体记忆研究的三大痛点 (`Sec 1, Page 2–3`)
1. **概念边界混用（Conceptual Ambiguity）**：学术界与工业界经常将 **Agent Memory（智能体记忆）** 与 **LLM Memory（大模型长上下文注意力/KV Cache 机制）**、**RAG（检索增强生成）**、**Context Engineering（单轮/跨轮上下文预算编排）** 混为一谈（`Sec 2.3, Fig. 2`）。
2. **传统粗粒度二分法失效（Inadequacy of Coarse Dichotomies）**：早期综述（如 Zhang et al., 2024m）普遍沿用认知心理学的“短期记忆对比长期记忆（Short-term vs. Long-term Memory）”或“陈述性对比程序性记忆”二分法，无法刻画现代智能体中动态演化的记忆拓扑（如三维多层时序图 `Zep`、Zettelkasten 卡片网络 `A-MEM`、软/硬混合工作记忆折叠 `AgentFold`、隐空间记忆编织 `MemGen`）。
3. **静态存储视角忽略生命周期动力学（Static View Overlooking Operational Dynamics）**：多数工作只讨论“存什么格式”，却忽略了记忆从原始交互轨迹中**形成（Formation）**、与存量知识库**演化（Evolution：整合/更新/遗忘）**、再到按需**检索利用（Retrieval：时机/改写/多路召回/后处理）**的闭环动力学。

### 1.2 数学形式化与四大相近概念严格划界 (`Sec 2.1–2.3, Fig. 2`)
1. **智能体与记忆生命周期三算子形式化 (`Sec 2.1–2.2, Page 4–6`)**：
   - 设多轮交互环境中的轨迹为 $\tau = (s_0, o_0, a_0, \dots, s_T)$，智能体策略为 $a_t = \pi_i(o_t^i, m_t^i, Q)$。
   - 统一记忆状态空间 $\mathcal{M}_t \in \mathcal{M}$（不预设短/长期物理隔离，短/长期区别仅体现为以下三个生命周期算子的**时间调用频率与作用范围**）：
     $$\mathcal{M}_{t+1}^{\text{form}} = \mathcal{F}(\mathcal{M}_t, \phi_t), \quad \mathcal{M}_{t+1} = \mathcal{E}(\mathcal{M}_{t+1}^{\text{form}}), \quad m_t^i = \mathcal{R}(\mathcal{M}_t, o_t^i, Q)$$
     其中：
     - $\phi_t$：当前步或当前会话产生的交互制品（对话轮次、工具调用返回、环境反馈、推理链）；
     - **形成算子 $\mathcal{F}$（Formation）**：从原始轨迹流 $\phi_t$ 中筛选、蒸馏、结构化构建或编码候选记忆单元；
     - **演化算子 $\mathcal{E}$（Evolution）**：将新形成记忆 $\mathcal{M}_{t+1}^{\text{form}}$ 融入存量库（执行跨簇整合、冲突消解更新、低价值遗忘）；
     - **检索算子 $\mathcal{R}$（Retrieval）**：基于当前观测 $o_t^i$ 与任务目标 $Q$ 构造查询并返回精炼后的工作上下文 $m_t^i$。
2. **Agent Memory 与 LLM Memory / RAG / Context Engineering 的严格边界 (`Sec 2.3, Fig. 2, Page 6–9`)**：

| 对比维度 | Agent Memory（智能体记忆） | LLM Memory（大模型内生记忆） | RAG（检索增强生成） | Context Engineering（上下文工程） |
| :--- | :--- | :--- | :--- | :--- |
| **核心定义** | 跨任务/跨会话持续演化的**自组织认知状态**（融合用户/环境事实与执行经验） | 模型架构层面的**长序列注意力、KV Cache 压缩与参数存储机制** | 面向**静态外部领域知识库**的查询-检索-生成管线（含 Modular / Graph / Agentic RAG） | 有限窗口内的**信息布局、Prompt 压缩、工具 schema 挂载与预算分配** |
| **写操作与演化性** | **高频主动读写与自演化**（`ADD / UPDATE / DELETE / CONSOLIDATE`） | 预训练/微调期写入，或推理期被动维护 KV 状态 | 知识库通常**静态只读**（即使 Agentic RAG 主动规划检索，也不修改底层语料库） | 仅在当前会话窗口内做瞬态裁剪/折叠，无跨会话持久演化 |
| **与 Agent Memory 的交集** | 核心本体 | 为 Agent Memory 提供底层 Parametric 与 Latent 载体 | Retrieval 算子 $\mathcal{R}$ 复用 RAG 检索技术，但服务于动态自演化记忆库 | Working Memory（`Sec 4.3`）是 Context Engineering 在单轮/多轮动态控制上的具象化 |

---

## 二、三维正交分类体系全景（Forms × Functions × Dynamics，`Fig. 1, Sec 3–5`）

本综述提出了涵盖 **形式（Forms：What carries memory?）**、**功能（Functions：Why agents need memory?）** 与 **动力学（Dynamics：How memory operates and evolves?）** 的三维正交分类架构：

```
+=========================================================================================================+
|                   Memory in the Age of AI Agents: 3D Orthogonal Taxonomy (arXiv:2512.13564)             |
+=========================================================================================================+
|                                                                                                         |
|  [Dimension 1: FORMS — What Carries Memory? (Sec 3, Fig. 3-5, Tables 1-3)]                              |
|  +---------------------------------+---------------------------------+-------------------------------+  |
|  | 3.1 Token-level Memory          | 3.2 Parametric Memory           | 3.3 Latent Memory             |  |
|  | (Explicit, discrete, editable)  | (Weight-space storage)          | (Continuous hidden/KV states) |  |
|  |  - 1D Flat (Chunk/Profile/Log)  |  - Internal (Pre/Mid/Post-train |  - Generate (Gist/MemGen/M+)  |  |
|  |    Mem0, MemGPT, AWM, Voyager   |    ROME, MEMIT, AlphaEdit)      |  - Reuse (LONGMEM, Memory3)   |  |
|  |  - 2D Planar (Tree/KG/Table)    |  - External (LoRA/Adapters:     |  - Transform (SnapKV, H2O,    |  |
|  |    A-MEM, MemTree, D-SMART      |    WISE, ELDER, Memory Decoder) |    PyramidKV, R3Mem)          |  |
|  |  - 3D Hierarchical (Multi-layer |                                 |                               |  |
|  |    Graph/Pyramid: Zep, HippoRAG,|                                 |                               |  |
|  |    G-Memory, CAM, EverMemOS)    |                                 |                               |  |
|  +---------------------------------+---------------------------------+-------------------------------+  |
|                                                    |                                                    |
|                                                    v                                                    |
|  [Dimension 2: FUNCTIONS — Why Agents Need Memory? (Sec 4, Fig. 6-7, Tables 4-6)]                       |
|  +---------------------------------+---------------------------------+-------------------------------+  |
|  | 4.1 Factual Memory              | 4.2 Experiential Memory         | 4.3 Working Memory            |  |
|  | ("What does the agent know?")   | ("How does the agent improve?") | ("What is it thinking now?")  |  |
|  |  - User Factual Memory:         |  - Case-based (Raw trajectories |  - Single-turn Working Mem:   |  |
|  |    Dialogue Coherence & Goal    |    & solutions: ExpeL, Memento) |    Input Condensation (Hard/  |  |
|  |    Consistency (Mem0, RMM)      |  - Strategy-based (Insights,    |    Soft/Hybrid) & Observation |  |
|  |  - Environment Factual Memory:  |    Workflows, Patterns: AWM,    |    Abstraction (Synapse)      |  |
|  |    Knowledge Persistence &      |    ReasoningBank, H2R, AgentKB) |  - Multi-turn Working Mem:    |  |
|  |    Multi-Agent Shared Access    |  - Skill-based (Code/Scripts/   |    State Consolidation (MEM1, |  |
|  |    (Zep, AriGraph, MetaGPT)     |    APIs/MCPs: Voyager, LEGOMem) |    ReSum), Hierarchical       |  |
|  |                                 |  - Hybrid (G-Memory, Memp)      |    Folding (AgentFold), Plan  |  |
|  +---------------------------------+---------------------------------+-------------------------------+  |
|                                                    |                                                    |
|                                                    v                                                    |
|  [Dimension 3: DYNAMICS — How Memory Operates and Evolves? (Sec 5, Fig. 8-10, Table 7)]                 |
|  +---------------------------------+---------------------------------+-------------------------------+  |
|  | 5.1 Memory Formation  F(M, phi) | 5.2 Memory Evolution  E(M_form) | 5.3 Memory Retrieval R(M,o,Q) |  |
|  |  1. Semantic Summarization      |  1. Consolidation:              |  1. Timing & Intent (When &   |  |
|  |     (Incremental / Partitioned) |     Local / Cluster / Global    |     Where: ComoRAG, MemOS)    |  |
|  |  2. Knowledge Distillation      |  2. Updating:                   |  2. Query Construction        |  |
|  |     (Factual / Experiential)    |     External Conflict Resolution|     (Decomposition / Rewriting|  |
|  |  3. Structured Construction     |     (Hard overwrite vs. Zep     |      HyDE, MemoRAG, MemGuide) |  |
|  |     (Entity-level / Chunk-level)|     bi-temporal soft invalid) & |  3. Retrieval Strategies      |  |
|  |  4. Latent Representation       |     Internal Model Editing      |     (Lexical / Semantic /     |  |
|  |  5. Parametric Internalization  |  3. Forgetting:                 |      Graph / Generative /     |  |
|  |     (Knowledge / Capability)    |     Time / Frequency / Value    |      Hybrid)                  |  |
|  |                                 |                                 |  4. Post-Retrieval (Rerank,   |  |
|  |                                 |                                 |     Filter, Aggregate)        |  |
|  +---------------------------------+---------------------------------+-------------------------------+  |
+=========================================================================================================+
```

---

## 三、维度一：记忆的物理与拓扑载体（Forms，`Sec 3, Fig. 3–5, Tables 1–3`）

### 3.1 Token-level Memory：按拓扑维度划分为 1D / 2D / 3D (`Sec 3.1, Fig. 3, Table 1`)
Token 级记忆以离散、可读、可外部审计的符号单元（自然语言文本、JSON 槽位、代码、三元组、多模态帧描述）存储，作者创造性地按**单元间的拓扑连接维度（Topological Dimensionality）**将其分为三代：

| 拓扑维度 | 拓扑特征与组织方式 (`Sec 3.1.1–3.1.3`) | 典型代表系统（源自 `Table 1, Page 12–16`） | 优势与局限对比 |
| :--- | :--- | :--- | :--- |
| **1D Flat Memory（一维扁平记忆）** | 单元之间无显式拓扑边，按时间序列、分块列表或键值袋（Bag-of-Units）线性排列（如对话块、用户画像槽位、经验轨迹条、工具代码库） | `MemGPT` (2023), `MemoryBank` (2024), `Mem0` (vector branch, 2025), `MemoryOS` (2025), `AWM` (2024), `ReasoningBank` (2025), `Voyager` (2024), `MIRIX-1.0` (2025), `LightMem` (2025) | **优势**：写入开销极低，易于增删改与向量检索；<br/>**局限**：缺乏跨片段显式关联，多跳推理与全局模式归纳能力弱 |
| **2D Planar Memory（二维平面结构记忆）** | 在单一抽象层级内引入显式结构连接（单层树、平面知识图谱、关系表），分为**在线构建（Online）**与**离线构建（Offline）** | **Tree**：`MemTree` (2025), `HAT` (2024), `RAPTOR` (2024)；<br/>**Graph**：`A-MEM` (2025, Zettelkasten 卡片网), `Mem0g` (2025), `M3-Agent` (2025), `D-SMART` (2025), `Optimus-1` (2024) | **优势**：支持单层邻域游走与显式语义关联；<br/>**局限**：所有节点处于同一抽象平面，缺乏跨粒度的垂直抽象层 |
| **3D Hierarchical Memory（三维层级拓扑记忆）** | 同时具备**层内水平连接（Intra-layer links）**与**跨层垂直抽象（Inter-layer vertical abstraction）**，分为**金字塔结构（Pyramids）**与**多层异构图（Multi-layer Graphs）** | **Pyramid**：`GraphRAG` (2025), `Zep` (2025, Episodic $\rightarrow$ Semantic $\rightarrow$ Community 三层图), `HiAgent` (2025), `G-Memory` (2025)；<br/>**Multi-layer Graph**：`HippoRAG / HippoRAG 2` (2024/2025), `AriGraph` (2024), `SGMem` (2025), `CAM` (2025), `MAGMA` (2026), `EverMemOS` (2026) | **优势**：兼顾底层原始证据溯源与高层社区/规律归纳，支持粗到细（Coarse-to-Fine）多粒度检索；<br/>**局限**：图构建与跨层同步维护的 LLM/I/O 成本高 |

### 3.2 Parametric Memory 與 Latent Memory (`Sec 3.2–3.3, Fig. 4–5, Tables 2–3`)
1. **Parametric Memory（参数级记忆，`Sec 3.2, Table 2`）**：
   - **Internal Parametric（内部权重存储）**：通过 Pre-training（`LMLM`, `HierMemLM`）、Mid-training（`Agent-Founder`, `Early Experience` 将无奖励探索轨迹内化进权重）或 Post-training（SFT/RL 如 `SELF-PARAM`, `CharacterGLM`；模型编辑如 `ROME`, `MEMIT`, `AlphaEdit`）写入主模型权重。
   - **External Parametric（外部参数模块）**：冻结主干，将记忆写入轻量级可插拔参数模块，包括 Adapter/LoRA（`MLP-Memory`, `WISE`, `ELDER`, `Memory Decoder`, `MemLoRA`）或辅助小模型（`MAC`, `Retroformer`）。
2. **Latent Memory（隐空间记忆，`Sec 3.3, Fig. 4, Table 3`）**：
   - **Generate（生成式隐状态）**：通过压缩编码器或织入模块生成紧凑隐向量/软 Token（如 `Gist`, `ICAE`, `AutoCompressors`, `MemoRAG`, `MemoryLLM`, `M+`, `Titans`, `MemGen`, `CoMEM`）。
   - **Reuse（直接复用 KV Cache）**：跨轮次持久保存并检索原始 KV 状态（如 `Memorizing Transformers`, `LONGMEM`, `Memory³`）。
   - **Transform（变换裁剪 KV Cache）**：基于注意力分数动态裁剪、合并或降维历史 KV 缓存（如 `H2O`, `Scissorhands`, `SnapKV`, `PyramidKV`, `RazorAttention`, `R3Mem`）。

---

## 四、维度二：记忆的三大认知功能（Functions，`Sec 4, Fig. 6–7, Tables 4–6`）

作者摒弃了“仅按时间长短划分功能”的旧做法，按记忆在智能体认知闭环中回答的**三个核心问题**划分为三大功能支柱（`Fig. 6, Page 29`）：

### 4.1 Factual Memory（事实记忆）—— *"What does the agent know?"* (`Sec 4.1, Table 4`)
1. **User Factual Memory（用户事实记忆，`Sec 4.1.1`）**：
   - **支撑对话连贯性（Dialogue Coherence）**：跨长周期会话记住用户的静态属性、动态偏好、社交关系与个人经历（如 `Mem0`, `MemoryBank`, `RMM`, `COMEDY`, `LD-Agent`, `SeCom`）。
   - **支撑目标一致性（Goal Consistency）**：在多轮复杂任务中追踪用户已确认的约束槽位与未决意图，防止目标漂移（如 `MemGuide` 分离已确认槽位与未决意图，`A-MEM`, `SGMem`）。
2. **Environment Factual Memory（环境事实记忆，`Sec 4.1.2`）**：
   - **支撑知识持久化（Knowledge Persistence）**：维护外部文档事实、工具状态或物理/游戏世界状态的一致性映射（如 `HippoRAG`, `Zep`, `AriGraph`, `CAM`, `M3-Agent`, `Mem-α`）。
   - **支撑多智能体共享访问（Multi-Agent Shared Access）**：在多 Agent 协作中充当去中心化或中心化的黑板/共享环境状态库（如 `MetaGPT` 的共享消息池、`G-Memory` 的三层角色定制图、`Memory Sharing`、`OASIS`）。

### 4.2 Experiential Memory（经验记忆）—— *"How does the agent improve?"* (`Sec 4.2, Fig. 7, Table 5`)
这是本综述对程序性/经验性记忆最核心的贡献之一：按**抽象粒度与可执行性（Abstraction Level & Executability）**将经验记忆严格划分为三级演进阶梯（加混合型）：

| 经验记忆子类型 | 存储粒度与核心形态 (`Sec 4.2.1–4.2.4`) | 是否直接可执行 | 典型代表系统（源自 `Table 5, Page 38–40`） | 核心作用与局限 |
| :--- | :--- | :---: | :--- | :--- |
| **1. Case-based Memory（案例级记忆，`Sec 4.2.1`）** | 最小化加工的原始交互轨迹（**Trajectories**）或成功求解实例（**Solutions**），保留完整的“情境-动作-结果”对齐 | 否（作为 In-Context Exemplar 重放） | `ExpeL` (2024), `Synapse` (2024), `MapCoder` (2024), `FinCon` (2024), `Memento` (2025, 用 Soft Q-learning 学习案例检索概率), `MemRL` (2026), `JARVIS-1` (2025) | **优势**：信息保真度最高、证据可验证；<br/>**局限**：占据大量上下文预算，跨任务泛化能力受表面特征限制 |
| **2. Strategy-based Memory（策略级记忆，`Sec 4.2.2`）** | 从成败轨迹中蒸馏出的可迁移非代码高层知识，细分为三层粒度：<br/>① **Insights（原子级启发/纠错规则）**<br/>② **Workflows（序列级工作流模板）**<br/>③ **Patterns（图式级推理骨架）** | 否（作为规划与推理的高层脚手架 Scaffold） | **Insights**：`H2R` (2025, 解耦规划级与执行级启发), `R2D2` (2025), `Reflexion` (2023), `ACE` (2025)；<br/>**Workflows**：`AWM` (2024), `Agent KB` (2025)；<br/>**Patterns**：`Buffer of Thoughts` (2024), `ReasoningBank` (2025), `Dynamic Cheatsheet` (2025), `PRINCIPLES` (2025) | **优势**：高度紧凑、可审计、可组合，大幅压缩搜索空间并支持跨领域迁移；<br/>**局限**：仅提供规划指导，不直接与环境底层接口交互 |
| **3. Skill-based Memory（技能级记忆，`Sec 4.2.3`）** | 智能体**可直接调用、结果可验证、可组合（Callable, Verifiable, Composable）**的程序化能力，细分为四类接口：<br/>① **Code Snippets**<br/>② **Functions & Scripts**<br/>③ **APIs**<br/>④ **MCPs（Model Context Protocol）** | **是**（直接执行代码/脚本/API/MCP 工具） | **Code**：`Voyager` (2024), `Darwin Gödel Machine` (2025)；<br/>**Functions/Scripts**：`LEGOMem` (2025), `Memp` (2025), `SkillWeaver` (2025), `LearnAct` (2025), `ASI` (2025)；<br/>**APIs**：`ToolLLM` (2024), `ToolGen` (2025), `ToolRet` (2025), `DRAFT` (2025)；<br/>**MCPs**：`Alita` / `Alita-G` (2025), `MemTool` (2025) | **优势**：将抽象策略落地为确定性执行动作，支持按需加载以节省上下文；<br/>**局限**：面临工具库膨胀后的语义检索瓶颈与环境变更后的脚本失效问题 |
| **4. Hybrid Experiential Memory（混合经验记忆，`Sec 4.2.4`）** | 协同维护案例、策略与可执行技能，或实现**从高频成功案例向高效技能的动态编译（Case $\rightarrow$ Strategy $\rightarrow$ Skill Compilation）** | 混合 | `ExpeL` (Case + Insight), `Agent KB` (Workflow + Solution path), `ChemAgent` (2025), `G-Memory` (2025), `Memp` (2025), `MemVerse` (2025, 融合参数记忆与 Token 级程序记忆) | 兼顾底层实例证据、高层策略泛化与快速确定性执行 |

### 4.3 Working Memory（工作记忆）—— *"What is the agent thinking about now?"* (`Sec 4.3, Table 6`)
作者明确指出：LLM 默认的 Context Window 只是一个**被动只读缓冲区（Passive Read-only Buffer）**，不具备人类工作记忆（Baddeley, 2012; Cowan, 2014）的**主动选择、抗干扰维护与动态改写能力**。因此，智能体工作记忆被严格定义为**单次任务/会话内对上下文工作区的主动管理与操纵机制（Active Management and Manipulation within a Single Episode）**：
1. **Single-turn Working Memory（单轮工作记忆，`Sec 4.3.1, Table 6-I`）**：处理海量即时输入（长文档、高维视频流、复杂 DOM 树），最大化单位 Token 的有效载荷：
   - **Input Condensation（输入浓缩）**：Hard Token 筛选（`LLMLingua`, `LongLLMLingua`, `CompAct`）、Soft 隐向量压缩（`Gist`, `ICAE`, `AutoCompressors`, `R3Mem`）与 Hybrid 软硬结合（`HyCo2`, `MELODI`）。
   - **Observation Abstraction（观测抽象）**：将非结构化高维观测重写为任务相关的紧凑状态描述（如 `Synapse` 将冗余 HTML DOM 树抽象为简洁状态摘要；`VideoAgent`, `Context as Memory` 提取视频关键帧语义事件）。
2. **Multi-turn Working Memory（多轮工作记忆，`Sec 4.3.2, Table 6-II`）**：在长程多步交互中维护任务状态与历史相关性，防止注意力饱和与目标漂移（Goal Drift）：
   - **State Consolidation（状态归并）**：将不断增长的轨迹流循环映射为固定预算的演化状态（如 `MEM1`, `MemAgent`, `ReSum`, `MemSearcher`, `IterResearch`, `SUPO` 用 RL 训练模型周期性重写固定大小的工作记忆状态；`ACON`, `AgentDiet` 优化历史压缩准则）。
   - **Hierarchical Folding（层级折叠）**：按子目标（Subgoal）分解轨迹，仅在子任务活跃期保留细粒度动作-观测对，子任务一旦完成即将其**折叠（Fold）**为简明摘要写回主干（如 `HiAgent`, `Context-Folding`, `AgentFold`, `DeepAgent`）。
   - **Cognitive Planning（认知规划工作区）**：以可读写的外部化层级计划或世界模型（如 `SayPlan` 的 3D 场景图、`PRIME`、`Agent-S`、`KARMA`）作为工作记忆核心锚点。

---

## 五、维度三：记忆生命周期动力学（Dynamics，`Sec 5, Fig. 8–10, Table 7`）

### 5.1 Memory Formation（记忆形成：*"How to extract the memory?"*，`Sec 5.1, Table 7`）
从原始交互流中提取高价值记忆的五类操作范式：
1. **Semantic Summarization（语义摘要，`Sec 5.1.1`）**：
   - *Incremental（增量融合）*：新块与旧摘要滚动融合（如 `MemGPT`, `Mem0`, 以及基于 PPO/GRPO 强化学习的 `MEM1`, `MemAgent`）；
   - *Partitioned（分区聚类摘要）*：按天/会话切分（`MemoryBank`, `COMEDY`）、按主题/语义聚类后摘要（`ReadAgent`, `LightMem`）或光学二维映射压缩（`DeepSeek-OCR`）。
2. **Knowledge Distillation（知识蒸馏，`Sec 5.1.2`）**：
   - *Distilling Factual Memory*：提取用户意图与客观事实（`TiM`, `RMM`, `MemGuide`, `M3-Agent`）；
   - *Distilling Experiential Memory*：从成功轨迹提取规划（`AWM`, `Memp`）、从失败轨迹对比反思（`R2D2`, `SAGE`）、正反对比蒸馏（`ExpeL`, `ReMe`）、两级规划+执行蒸馏（`H2R`），以及基于 RL 训练提取策略（`Memory-R1`, `Mem-α`）。
3. **Structured Construction（结构化构建，`Sec 5.1.3`）**：
   - *Entity-Level Construction（实体级建图）*：提取三元组构建平面图（`KGT`, `Mem0g`）、OWL 本体神经符号图（`D-SMART`）、社区层级图（`GraphRAG`）、语义+情景双层图（`AriGraph`, `HippoRAG`）或双时态三层图（`Zep`）；
   - *Chunk-Level Construction（片段级建树/建网）*：静态树（`HAT`, `RAPTOR`）、动态自底向上/自顶向下树（`MemTree`, `H-MEM`）、卡片链接网（`A-MEM`, `PREMem`）与增量多智能体三层图（`CAM`, `G-Memory`）。
4. **Latent Representation（隐空间表征编码，`Sec 5.1.4`）**：直接编码为连续向量或触发式隐 Token（`MemoryLLM`, `M+`, `MemGen`, `CoMEM`）。
5. **Parametric Internalization（参数内化，`Sec 5.1.5`）**：知识编辑（`MEND`, `ROME`, `MEMIT`, `CoLoR`）与能力内化（SFT/DPO/GRPO 及免检索插拔式 `Memory Decoder`）。

### 5.2 Memory Evolution（记忆演化：*"How to refine the memory?"*，`Sec 5.2, Fig. 9`）
1. **Consolidation（记忆整合，`Sec 5.2.1`）**：
   - *Local Consolidation（局部细粒度合并）*：Top-$K$ 相似条目由 LLM 判断合并（`RMM`, `VLN`）；
   - *Cluster-level Fusion（簇级融合）*：跨簇泛化归纳或簇内哈希桶去重（`PREMem`, `EverMemOS` 的 `MemCell` $\rightarrow$ `MemScene` 质心归并, `TiM`, `CAM`）；
   - *Global Integration（全局整合）*：临时快照与长期档案合成（`MOOM`, `Matrix`, `AgentFold`）。
2. **Updating（记忆更新与冲突消解，`Sec 5.2.2`）**：
   - **外部记忆更新的四代演进路线**：
     1. *硬覆盖/硬删除（Destructive Replacement）*：`MemGPT`, `D-SMART`, `Mem0g` 直接用新事实替换/删除冲突旧事实，破坏了历史时间连续性；
     2. *双时态软失效（Bi-temporal Soft Invalidation）*：`Zep` 通过标记 `t_invalid` 失效时间戳保留历史演变轨迹；
     3. *在线软写入 + 离线反射合并（Dual-phase Eventual Consistency）*：`MOOM`, `LightMem` 在线低延迟追加，离线批量合并消歧；
     4. *RL 学习更新策略（Learned Update Policy）*：`Mem-α`, `Memory-R1` 通过强化学习训练模型自主决策何时更新、如何平衡稳定性与可塑性（Stability–Plasticity Dilemma）。
   - **内部模型编辑（Model Editing）**：`ROME`, `MemoryLLM`, `M+`, `ChemAgent`。
3. **Forgetting（记忆遗忘，`Sec 5.2.3`）**：
   - *Time-based（基于时间衰减）*：FIFO 淘汰（`MemGPT`）、随机比例替换或指数权重衰减（`MAICC`）；
   - *Frequency-based（基于访问频率）*：LFU（`XMem`）、计数布隆过滤器（`KARMA`）、LRU 淘汰与归档（`MemOS`）；
   - *Importance-driven（基于综合价值与语义判别）*：结合艾宾浩斯时间衰减+频率+语义/情感显著性或 LLM 主动裁剪（`MemoryBank`, `Livia`, `TiM`, `MemTool`）。

### 5.3 Memory Retrieval（记忆检索：*"How to utilize the memory?"*，`Sec 5.3, Fig. 10`）
将检索拆解为四阶段标准流水线：
1. **Retrieval Timing & Intent（何时检索与查哪个库，`Sec 5.3.1`）**：
   - *Automated Timing（自主时机）*：从工具主动触发（`MemGPT`, `MemTool`）演进到**快慢思考触发**（`ComoRAG`, `PRIME` 先快思考生成初稿，评估不足再触发慢速深度检索）与隐状态触发器（`MemGen`）；
   - *Automated Intent（自主路由）*：根据反馈切换抽象层级（`AgentRR`）、跨存储介质调度（`MemOS` 的 `MemScheduler`）或自顶向下粗到细层级路由（`H-MEM`）。
2. **Query Construction（查询构造，`Sec 5.3.2`）**：
   - *Query Decomposition（复杂查询分解）*：子问题拆解（`Visconde`, `ChemAgent`）、全局规划器拆解（`PRIME`, `MA-RAG`）、师生失败驱动拆解（`Agent KB`）；
   - *Query Rewriting（查询改写）*：零样本假设文档 `HyDE`、基于全局压缩记忆生成草稿查询的 `MemoRAG`、提取命令式高层意图短语的 `MemGuide`、澄清树 `ToC`。
3. **Retrieval Strategies（检索执行策略，`Sec 5.3.3`）**：Lexical（BM25/TF-IDF）、Semantic（Dense Embedding）、Graph（$K$-hop 自我中心图 `Mem0g`/`SGMem`、个性化 PageRank `HippoRAG`、LLM 引导束搜索 `CAM`/`D-SMART`、时序图约束检索 `Zep`/`MemoTime`）、Generative（直接生成文档 ID）与 Hybrid（词法+向量+图+多因子打分如 `Generative Agents`, `MIRIX`, `Agent KB`, `Semantic Anchoring`）。
4. **Post-Retrieval Processing（检索后处理，`Sec 5.3.4`）**：
   - *Re-ranking & Filtering（重排与过滤）*：多信号融合重排（`RCR-Router`）、RL 权重学习（`Learn-to-Memorize`）、时间窗口过滤（`Zep`, `MemoTime`）、LLM 驗證器过滤（`Memory-R1`）、Q-learning 效用预测（`Memento`）与槽位补全边际增益重排（`MemGuide`）；
   - *Aggregation & Compression（聚合与角色定制压缩）*：全局摘要整合（`ComoRAG`）、子查询证据抽取（`MA-RAG`）、多 Agent 角色定制化提示生成（`G-Memory`）。

---

## 六、主流评测基准与开源框架横向总表（`Sec 6, Tables 8–9`）

### 6.1 评测基准全景分类 (`Sec 6.1, Table 8, Page 65–67`)
作者梳理了 40 个相关评测基准，按测试目标分为两大类：
1. **显式面向记忆/终身学习/自演化智能体的基准（26 个）**：
   - *长程对话与用户画像追踪*：`LoCoMo` (300 s., 真实多模态对话), `PersonaMem` (15 t./180 s., 动态用户画像), `LongMemEval` (5 t./500 s., 交互式长程记忆), `PerLTQA` (8,593 s.), `MemoryBank` (194 s.), `MPR` (108,000 s.), `PrefEval` (3,000 s., 隐式偏好遵循), `LOCCO` (3,080 s.), `DialSim` (~1,300 s.), `Madial-Bench` (331 s.)。
   - *记忆幻觉与综合能力诊断*：`HaluMem` (3,467 s., 记忆幻觉评测), `MemBench` (53,000 s., 涵盖事实与经验记忆), `MemoryAgentBench` (4 t., 多轮交互四大能力), `MemoryBench` (4 t./~20,000 s., 持续学习)。
   - *测试时自演化与流式终身学习*：`Evo-Memory` (10 t./~3,700 s., 测试时自演化流式评测), `LifelongAgentBench` (1,396 s.), `StreamBench` (9,702 s.), `WebChoreArena` (532 s.), `MT-Mind2Web` (720 s.)。
   - *长上下文基础探针*：`LongBench` / `LongBench v2`, `RULER`, `BABILong`, `MM-Needle`。
2. **隐式考验长程记忆与经验复用的通用智能体基准（14 个）**：
   - 具身与文本交互（`ALFWorld`, `ScienceWorld`, `BabyAI`, `AgentGym`, `AgentBoard`, `PDDL`）、Web 与工具调用（`WebShop`, `WebArena`, `MMInA`, `ToolBench`）、真实代码与深度研究（`SWE-Bench Verified`, `GAIA`, `xBench-DS`）。

### 6.2 25 个主流开源记忆框架对比 (`Sec 6.2, Table 9, Page 68`)
`Table 9` 对比了 `MemGPT`, `Mem0`, `Memobase`, `MIRIX`, `MemoryOS`, `MemOS`, `Zep`, `LangMem`, `SuperMemory`, `Cognee`, `Memary`, `Second Me`, `MemU`, `MemEngine`, `ReMe`, `Acontext`, `HindSight` 等 25 个开源框架，指出当前开源生态正从“单一向量库封装”快速演进为**同时支持事实记忆（Factual）与经验/技能记忆（Experiential）、兼具图+向量混合结构与多模态能力**的综合记忆底座。

---

## 七、八大前沿趋势研判（Positions and Frontiers，`Sec 7, Page 69–78`）

| 前沿方向 (`Sec 7.1–7.8`) | 范式演进核心命题（From $\rightarrow$ To） | 关键代表工作与未来技术路径 |
| :--- | :--- | :--- |
| **7.1 记忆检索对比记忆生成（Memory Retrieval vs. Memory Generation）** | 从**静态槽位/片段检索拼接（Retrieval-centric）**演进为**按需动态合成与重构（Memory Generation）** | ① *Retrieve-then-Generate*（`ComoRAG`, `G-Memory`, `CoMEM` 将召回素材重构为任务定制表示）；<br/>② *Direct Memory Generation*（`MemGen`, `VisMem` 直接从当前上下文与隐状态生成任务定制化隐记忆 Token） |
| **7.2 自动化记忆管理（Automated Memory Management）** | 从**人工设计 Prompt/阈值/管线（Hand-crafted Rules）**演进为**架构与内容联合自演化（Meta-Evolving Architecture）** | `CAM`（自动聚类）、`Memory-R1`（专用记忆管理 Agent）、**`MemEvolve`**（同时演化智能体的经验知识内容与底层记忆系统架构拓扑） |
| **7.3 强化学习驱动的记忆控制（RL Meets Agent Memory）** | 从**启发式无梯度操作（PE / SFT）**演进为**端到端 RL 策略控制全生命周期（RL-driven Memory Control）** | 覆盖形成与浓缩（`MEM1`, `MemAgent`, `IterResearch`, `SUPO`）、更新与提取（`Mem-α`, `Memory-R1`）、折叠（`Context-Folding`）、检索打分（`Memento`, `Learn-to-Memorize`），未来向**Token 级精细信用分配（Fine-grained Credit Assignment）**演进 |
| **7.4 多模态记忆（Multimodal Memory）** | 从**纯文本日志（Text-only）**演进为**跨模态统一表征与时序对齐（Omni-modal Unified Memory）** | 解决连续高维视频/音频/GUI 流的语义抽象与跨模态对齐（`M3-Agent`, `JARVIS-1`, `CoMEM`, `VideoAgent`, `DeepSeek-OCR`） |
| **7.5 多智能体共享记忆（Shared Memory in Multi-Agent Systems）** | 从**单智能体孤立私有库（Isolated Silos）**演进为**权限受控的共享黑板与角色定制视图（Role-customized Shared Memory）** | 解决多 Agent 间的记忆同步、认知冲突消解与角色定制化分发（`G-Memory`, `Memory Sharing`, `MetaGPT`, `OASIS`） |
| **7.6 面向世界模型的记忆（Memory for World Models）** | 从**被动历史记录（Passive Past Log）**演进为**支撑反事实推演与前瞻规划的动态世界状态预测器（Predictive World Model）** | 记忆不仅记录“发生过什么”，还编码环境转移规律 $P(s_{t+1}|s_t, a_t)$ 以支持前瞻模拟（`SayPlan`, `DreamGym`, `KARMA`） |
| **7.7 可信记忆（Trustworthy Memory: Privacy, Safety & Hallucination）** | 从**盲目信任存储内容**演进为**防投毒、防幻觉、支持精确机器遗忘（Unlearning）与隐私隔离的可信体系** | 应对记忆注入攻击（Memory Poisoning）、记忆幻觉级联放大（`HaluMem`）与敏感隐私合规擦除 |
| **7.8 人类认知与神经科学连接（Human-Cognitive Connections）** | 借鉴海马体-新皮层互补学习系统（CLS）、睡眠慢波重放整合（Sleep Consolidation）、主动重构式回忆（Constructive Recall）与情绪显著性调制 | 如 `HippoRAG`（海马体索引）、`LightMem`（离线睡眠期反射合并）、`Livia`（情绪显著性遗忘） |

---

## 八、对我们项目的核心启发与主报告对齐

1. **直接支撑主报告的三层认知记忆功能定位（对齐 `Sec 4`）**：
   - 本综述将智能体记忆功能严格划分为 **Factual Memory（事实记忆，`Sec 4.1`）**、**Experiential Memory（经验记忆：Case / Strategy / Skill 三级阶梯，`Sec 4.2`）** 与 **Working Memory（工作记忆：单轮输入浓缩/观测抽象 + 多轮状态归并/层级折叠/认知规划，`Sec 4.3`）**。这为我们主报告中的“**用户与网元事实记忆（Factual）+ 慢路径澄清与排障策略/技能沉淀（Experiential: Strategy & Skill）+ 会话内槽位状态机工作区（Working Memory）**”提供了2026年最具权威性的综述分类学背书。
2. **经验记忆的“案例 $\rightarrow$ 策略 $\rightarrow$ 技能（Case $\rightarrow$ Strategy $\rightarrow$ Skill）”三级演进闭环（对齐 `Sec 4.2.1–4.2.4`）**：
   - 综述指出了混合经验记忆（`Sec 4.2.4`，如 `G-Memory`, `Memp`）的核心演进方向：**将初始阶段保存的原始成功/失败排障单据与对话轨迹（Case-based），在累积足够证据后蒸馏为可迁移的消歧/参数调整规则（Strategy-based Insights/Workflows），最终将高频确定性子流程固化为可直接调用的标准脚本或 API/MCP 技能（Skill-based）**。这与我们提出的“慢路径交互归纳与经验规则沉淀 $\rightarrow$ 快路径直接命中执行”完全同构。
3. **快慢思考驱动的检索时机与意图路由（对齐 `Sec 5.3.1–5.3.2`）**：
   - 在检索动力学（`Sec 5.3.1`）中，综述重点总结了以 `ComoRAG`、`PRIME` 为代表的**快慢思考检索触发机制（Fast–Slow Thinking Retrieval Timing）**以及以 `MemGuide`、`ToC` 为代表的**意图分离与澄清树查询构造（Query Construction）**——先尝试快路径推理并评估槽位充分性，若发现信息缺失或指代模糊（`Underspecified`），再触发深度多路关联检索或慢路径主动澄清，同时像 `MemGuide` 一样在工作记忆中严格分离“已确认约束槽位（Confirmed Constraints）”与“待澄清意图（Unresolved Intents）”。
4. **外部记忆更新的双阶段最终一致性与双时态软失效（对齐 `Sec 5.2.2`）**：
   - 综述在 `Sec 5.2.2` 梳理了外部记忆更新从“硬覆盖（`Mem0g`）”到“双时态软失效（`Zep`）”再到“**在线软写入 + 离线反射合并（`LightMem`, `MOOM`）**”的演进脉络。我们在处理高频网元单据流与实时用户对话时，同样应采用“**会话内在线低延迟软追加 + 跨会话离线聚类整合与双时态版本归档**”的双阶段机制，兼顾实时响应速度与长程画像一致性。

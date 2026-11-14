# [09] MIRIX & MIRIX-2.0: Multi-Agent Memory System — 论文与源码精读笔记

- **论文标题**：
  - **MIRIX-1.0**：*MIRIX: Multi-Agent Memory System for LLM-Based Agents*（Yu Wang, Xi Chen；UC San Diego & NYU Stern / MIRIX AI；`arXiv:2507.07957v1`，2025 年 7 月 10 日）
  - **MIRIX-2.0**：*MIRIX-2.0: Multi-Agent Memory System*（Wei-Chieh Huang, Weizhi Zhang, Jiayan Nan, Peng Xia, Yu Wang；UIC, 同济大学, UNC Chapel Hill, UC San Diego / MIRIX AI；`arXiv:2611.12068v1`，2026 年 11 月 9 日）
- **本地文件与源码映射**：
  - 论文 PDF：[MIRIX_2025.pdf](file:///D:/coding/sharing/papers/memory/MIRIX_2025.pdf)（v1.0）、[MIRIX_2_0_2026.pdf](file:///D:/coding/sharing/papers/memory/MIRIX_2_0_2026.pdf)（v2.0）
  - 转换后 Markdown：[2507.07957.md](file:///D:/coding/sharing/papers/memory/2507.07957/2507.07957.md)、[2611.12068.md](file:///D:/coding/sharing/papers/memory/2611.12068/2611.12068.md)
  - LaTeX 源码包：`D:\coding\sharing\papers\memory\2507.07957\source\`、`D:\coding\sharing\papers\memory\2611.12068\source\`
  - 官方开源仓库：`D:\coding\sharing\papers\repos\MIRIX\`（`https://github.com/Mirix-AI/MIRIX`）

---

## 一、核心定位与从 MIRIX-1.0 到 MIRIX-2.0 的演进脉络

### 1.1 现有记忆系统的不可能三角与两代架构分工 (`2507.07957 Sec 1`, `2611.12068 Sec 1`)
论文指出，生产级 Agent 记忆系统必须同时满足三项核心指标（`2611.12068 Sec 1 & Sec 2.1`）：
1. **源证据保真度（Source Fidelity / Accuracy）**：人名、日期、数量、价格及相似事件之间的细微区分在写入与巩固（Consolidation）后仍能无损恢复，且每条推理结论均可追溯至原始存储记录。
2. **有界检索开销（Bounded Access / Efficiency）**：单次查询检查的图邻域与引用的数据库记录行数必须受显式预算（Explicit Budgets）严格上界约束，不随历史总长度线性膨胀。
3. **跨事件时序独立性（Temporal Identity）**：同一事件在不同会话中的重复提及应共享证据，但措辞相似的不同次无日期事件（如不同日期的两次跑步或两次网络卡顿）绝不能因文本近似而坍缩为同一节点。

围绕这一目标，MIRIX 经历了两代核心演进：
- **MIRIX-1.0 (`arXiv:2507.07957`)**：首创 **“六类专业化记忆分库（Six Memory Components）+ 多智能体协同路由（1 个 `Meta Memory Manager` + 6 个专用 `Memory Managers` + 1 个 `Chat Agent`）+ 主动话题检索（Active Retrieval）”**，并构建了面向高分辨率屏幕流的多模态基准 **ScreenshotVQA**。
- **MIRIX-2.0 (`arXiv:2611.12068`)**：在保留 MIRIX-1.0 六类分库作为底层**类型化证据平面（Typed Evidence Plane $P_u$，System of Record）**的基础上，新增了**保血缘 $n$ 元超图索引层（Provenance Hypergraph $G_u$）**与**脱离写路径的异步巩固机制（AutoDream）**，实现了**用户侧记忆（User-Centric Memory：语义实体对齐而不改写原文）**与**智能体侧记忆（Agent-Centric Memory：从任务轨迹原话引文中提炼正反经验并编修程序技能 `Skills`）**的大一统。

---

## 二、六类记忆分库与多智能体路由底座 (`MIRIX-1.0 Sec 3` & `MIRIX-2.0 Sec 2.2`)

### 2.1 六类记忆组件的数据结构与职责边界 (`2507.07957 Sec 3.1`, `2611.12068 Table 2`)
MIRIX 将智能体记忆严格解耦为六个拥有独立 PostgreSQL Schema（`mirix/orm/`）与独立管理智能体（`mirix/agent/`）的存储组件：

| 记忆组件 | 核心认知角色 | 核心 Schema 字段 (`2507.07957 Sec 3.1` & `mirix/orm/`) | 超图索引 (`MIRIX-2.0`) | 开源仓对应 Manager (`mirix/services/`) |
| :--- | :--- | :--- | :---: | :--- |
| **1. Core Memory**<br>（核心常驻记忆） | 始终驻留 System Prompt 的高优先级画像与人设 | 分 `persona`（Agent 身份与风格）与 `human`（用户姓名、核心长期偏好）两块；容量达 **90%** 时触发受控重写压缩 | **否**（直接常驻注入） | `block_manager.py` |
| **2. Episodic Memory**<br>（情景事件记忆） | 带时间戳的具体事件、交互与状态变更日历 | `event_type` (`user_message` / `inferred_result` / `system_notification`)、`summary`、`details`、`actor` (`user` / `assistant`)、`timestamp` ($\tau_e$ 事件发生时间 vs. $\tau_m$ 提及时间) | **是**（索引至 $G_u$） | `episodic_memory_manager.py` |
| **3. Semantic Memory**<br>（语义概念记忆） | 跨时间稳定的抽象事实、概念与人物社会关系 | `name`（实体/概念标识）、`summary`（关系或定义简述）、`details`（详细背景）、`source`（来源说明） | **是**（索引至 $G_u$） | `semantic_memory_manager.py` |
| **4. Procedural Memory**<br>（程序技能记忆） | 目标导向的操作规程、工作流与可执行脚本 | v1.0：`entry_type` (`workflow`/`guide`/`script`)、`description`、`steps`；<br>v2.0 升级为带引文溯源的 **`Skill` 库**（由 `AutoDream` 蒸馏与编修） | **否**（独立技能检索） | `procedural_memory_manager.py` & `skill_experience_curator.py` |
| **5. Resource Memory**<br>（多模态资源记忆） | 用户正在处理的完整/分块文档、语音转录或截图摘要 | `title`、`summary`、`resource_type` (`doc`/`markdown`/`pdf_text`/`image`/`voice_transcript`)、`content` | **否**（专用检索通道） | `resource_memory_manager.py` |
| **6. Knowledge Vault**<br>（敏感凭证保险箱） | 需逐字精确保存的敏感隐私与鉴权信息（防泛化篡改） | `entry_type` (`credential`/`bookmark`/`contact_info`/`api_key`)、`source`、`sensitivity` (`low`/`medium`/`high`)、`secret_value`（高敏条目排除在常规检索外） | **否**（权限隔离访问） | `knowledge_vault_manager.py` |

### 2.2 多智能体协同写入与 Active Retrieval 工作流 (`2507.07957 Sec 3.2–3.3, Fig. 5–8`)
1. **写路径（Memory Update Workflow）**：
   - 新输入 $x_t$（对话轮次或每积满 20 张去重屏幕截图，视觉相近度 $>0.99$ 自动丢弃）到达时，系统先在现有记忆库中执行一次快速预检索，将检索摘要与 $x_t$ 一并交给 **`Meta Memory Manager`**。
   - `Meta Memory Manager` 判定需要更新的目标记忆子集 $\mathcal{K}_t = R_\theta^\star(x_t) \subseteq \{1..6\}$，并行唤醒对应的 **`Memory Managers`**。
   - 各子 Agent 调用专属工具写入/更新各自表项，直至调用终止工具 `finish_memory_update()` 返回确认（`docs/ARCHITECTURE.md:111-115`）。
2. **读路径（Active Retrieval 主动话题检索）**：
   - 针对传统记忆系统“不显式指令就不查记忆、直接依赖预训练过时知识作答”的痛点，MIRIX 强制 `Chat Agent` 在生成回复前先根据上下文生成当前查询话题（`current topic`），自动从六大组件检索 Top-$k$ 相关摘要并包裹在 `<episodic_memory>...</episodic_memory>` 等 XML 标签内注入 System Prompt，随后按需发起细粒度工具检索（支持 `embedding_match`、`bm25_match`、`string_match`）。

---

## 三、MIRIX-2.0 核心算法突破：保血缘 $n$ 元超图与 AutoDream (`2611.12068 Sec 2, Alg. 1`)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                          MIRIX-2.0 双层存储-索引分离与三路径架构 (Sec 2, Fig. 1 & Alg. 1)        │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 【1. 写路径 Write(x_t)】                                                                        │
│   输入 x_t ──► Meta Memory Manager R_θ*(x_t) ──► 6 个 Typed Writers W_k*(x_t, P_u)              │
│     ├─► 先提交持久化至【类型化证据平面 P_u (PostgreSQL + pgvector, System of Record)】(Fail-Soft)│
│     └─► 若 k ∈ {episodic, semantic}：                                                           │
│           ├─► n-ary Frame 抽取与缺失细节修复: Φ ← Extract*(m) ∪ Repair*(m)  (Eq. 5)             │
│           ├─► 锚点规范化与准入门控: A_m ← Admit(Canon*(Φ)) (剔除通用词/角色词，上限 16/18 个)    │
│           └─► 写入【Neo4j 保血缘超图 G_u = (A_u, F_u, E_u)】：                                  │
│                 • 语义帧 ID: id_S(f) = H(u, p, σ(f))                (Eq. 6, 跨会话累积引文 C_f)  │
│                 • 情景帧 ID: id_E(f) = H(u, p, σ(f), χ(f))          (Eq. 7-8, 防无日期事件坍缩)  │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 【2. 读路径 Read(q) & Answer(q)】 (全流程受算子预算 B_q^B, B_q^R 严格上界约束)                  │
│   查询 q ──► 确定性规划器 Plan(q) 识别 5 类算子 o_q ∈ {single, temporal, intersection,          │
│              list-union, count} 并分配双通道行数预算 (B_q^B, B_q^R) (Eq. 9, Table 3)            │
│     ├─► 锚点入口打分 s_A(a,q) (Eq. 10)：向量召回 15 个 + 精确匹配 16 个 ──► 截断保留 Top K_A=15 │
│     ├─► 双通道有界扩展：                                                                        │
│     │     • Base-Recall Lane: 关联行 + 同 Chunk/相邻时间片血缘重算 (上限 B_q^B)                 │
│     │     • Relation-Citation Lane: 谓词过滤(≤240 帧) + 9 项加性打分 s_F(f,q) (Eq. 11, 上限 B_q^R)│
│     └─► 引用平衡融合 Fuse ──► 返回【超图事实 F_q + 支撑源记录行】──► AnswerCheck 触发至多 1 次重搜│
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 【3. 离线巩固路径 AutoDream (脱离写路径运行)】                                                  │
│   ├─► SemanticDream(Δ_u) (Eq. 12-13)：仅针对新增语义前沿 Δ_u 中稳定实体类型 T_safe，            │
│   │     在 Top-4 近邻 (cos ≥ 0.86) 中由 LLM 判定同指并合并锚点边，【绝不改写 P_u 原始证据行】   │
│   └─► ProceduralDream(S_u)：Distill*(S_u) 从真实会话原话引文中判定成败并提炼正/反经验 e_{1:m}   │
│         ──► Curate*(P_u^P, e_{1:m}) 创建/修订可执行 Skill（强制校验原文 Quote 真实存在）        │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 证据平面与超图索引的严格物理解耦 (`Sec 2.2–2.3, Eq. 1–4`)
在 MIRIX-2.0 中，用户的持久状态定义为 $\mathcal{S}_u^t = (P_u^t, G_u^t)$（`Eq. 1`）：
- **证据平面 $P_u$（PostgreSQL + `pgvector`）是唯一权威数据源（System of Record）**：每条情景或语义记录表示为：
  $$m = (i, k, y, \tau_e, \tau_m, \rho, \mathbf{z}) \quad (\text{Eq. 2})$$
  其中 $i$ 为不可变行 ID，$k \in \{\text{episodic}, \text{semantic}\}$，$\tau_e$ 为事件发生时间，$\tau_m$ 为提及/写入时间，$\rho$ 为源文档与分块血缘（Provenance），$\mathbf{z}$ 为检索向量。**写操作必须先在数据库提交（`Commit(P_u, m)`），超图构建仅作为 Fail-Soft 索引钩子——即使图写入失败也绝不回滚已落库的记忆记录**（`Sec 2.2, Invariant 4`）。
- **保血缘 $n$ 元超图 $G_u = (\mathcal{A}_u, \mathcal{F}_u, \mathcal{E}_u)$（Neo4j）**：
  - **锚点（Anchor, `Eq. 4`）**：$a = (i_a, n_a, t_a, \mathbf{e}_a, I_a^E, I_a^S)$。通过确定性规范化键 $\kappa(n)$（转小写、去标点、剔除 11 个冠词/虚词、长度 $\ge 4$ 词尾复数还原、词序排序，但**严格保留数字**以区分 `10 Gallons` 与 `20 Gallons`，见 `graph_memory_manager_v7.py:89-114`）及准入门控（`Admit`：拦截 `advice / details / plan` 等 52 个泛化词及 `user / assistant` 角色伪实体，单条 Episodic 上限 **16** 个锚点、Semantic 上限 **18** 个锚点，见 `lines 54-125`）。
  - **注册表引导的实体对齐（Registry-Guided Canonicalization, `Sec 2.3 & App. 6.2`）**：对每个新抽取实体，检索同用户下余弦相似度 $\cos \ge 0.72$（向量索引得分 $(1+\cos)/2 \ge 0.86$）的 Top-4 已有锚点，每条记录仅发起 **1 次** LLM 调用判定是否同指；LLM 只能从候选集中选择已有名称，严禁凭空捏造合并目标。

### 3.2 $n$ 元事实帧（N-ary Frames）与双轨身份哈希 (`Sec 2.3, Eq. 5–8`)
针对传统三元组知识图谱（如 Graphiti/Zep）将多参与方事件拆碎导致上下文丢失的问题（例如“Caroline 于 5 月 6 日乘达美航空从波士顿飞往迈阿密”若拆为多个二元边，查询时无法区分哪次航班对应哪个航司），MIRIX-2.0 提取 $n$ 元框架（`frame_extractor.py:1-158`）：
$$f = \left(p,\; \{(r_j, a_j)\}_{j=1}^{d_f},\; \ell_f,\; \tau_e, \tau_m,\; C_f\right) \quad (\text{Eq. 5})$$
- **实体作角色臂（Role-Typed Arms），数值作字面量属性（Literals $\ell_f$）**：日期、价格、数量、时长（如 `"17"`, `"$420"`, `"500 Mbps"`）强制存储在帧属性字典 $\ell_f$ 中，严禁作为独立实体锚点污染图空间（`frame_extractor.py:19-24, 97-98`）。只有至少绑定 2 个不同锚点（$|A_f| \ge 2$）的帧才会被物化。
- **角色词表折叠（`_ROLE_CANON`, `frame_extractor.py:59-91`）**：源码中实测发现开放角色提取会产生 71 种角色名，导致同一事实因角色标签不同（如 `attendee` 与 `agent`、`patient` 与 `theme`）占总事实 `7.2%` 的重复率；因此代码通过 `_ROLE_CANON` 将长尾同义角色确定性映射至核心角色（保留 `agent / origin / destination / recipient / instrument / location` 等关键方向区分）。
- **缺失高信号细节的确定性审计与单次修复（`Repair*`, `Alg. 1 line 5 & App. 6.2`）**：提取后用确定性规则检查源文本中的引号短语、数字或视觉内容覆盖率（$<45\%$ 内容词未覆盖时触发），最多将 12 项缺失细节送入 1 次补充提取调用（只增不删）。
- **语义帧与情景帧的差异化身份哈希（Occurrence Identity, `Eq. 6–8` & `graph_memory_manager_v7.py:131-180`）**：
  令 $\sigma(f)$ 为排序后的角色-锚点键集合 $\{r_j : \kappa(n_{a_j})\}$：
  - **语义帧 ID（跨会话合并累积引文）**：
    $$\operatorname{id}_S(f) = H(u, p, \sigma(f)) \quad (\text{Eq. 6})$$
  - **情景帧 ID（带发生键 $\chi(f)$，防无日期事件坍缩）**：
    $$\operatorname{id}_E(f) = H(u, p, \sigma(f), \chi(f)), \quad \chi(f) = \begin{cases} \text{explicit event time}, & \text{if extracted}, \\ \text{immutable memory id } i_m, & \text{otherwise}. \end{cases} \quad (\text{Eq. 7–8})$$
    因此，对同一带日期事件的多次提及会汇聚到同一帧并累加引文集合 $C_f$；而发生在不同天但未标明具体日期的两次同类事件（因 $i_m$ 不同）严格保持为两个独立帧。

---

### 3.3 图主导的有界证据检索 (`Graph-Owned Retrieval`, `Sec 2.4 & App. 6.3, Eq. 9–11`)
1. **五类查询算子与显式双通道预算（`Eq. 9 & App. Table 3`）**：
   确定性规划器 `Plan(q)` 将问题映射为 $\Pi(q) = (o_q, \mathcal{P}_q, \mathcal{C}_q, \mathcal{Y}_q, \mathcal{T}_q, B_q^B, B_q^R)$，按算子类型严格限制**基础召回通道行数 $B_q^B$** 与**关系引用通道行数/事实帧数 $B_q^R$**：

   | 查询算子 $o_q$ | 适用问题类型 | 基础通道预算 $B_q^B$ (Base Rows) | 关系通道预算 $B_q^R$ (Cited Rows / Facts) |
   | :--- | :--- | :---: | :---: |
   | **`Single`** | 单值属性或单一事实查询 | 6 | 4 |
   | **`Temporal`** | 时间先后、日期定位或跨期变化 | 6 | 6 |
   | **`Intersection`** | 多实体交集或共同特征查询 | 7 | 7 |
   | **`List-union`** | 枚举列表或多事件汇总 | 7 | 9 |
   | **`Count`** | 计数统计类问题（需覆盖完整集合） | 8 | 12 |

2. **锚点入口评分（`Eq. 10`）**：
   先由向量检索召回 15 个锚点，关系型查询额外补充最多 16 个问题中精确提及的锚点，按以下公式取 Top $K_A = 15$：
   $$s_A(a, q) = s_{\text{vec}} + s_{\text{exact}} + s_{\text{lex}} + s_{\text{pred}} + s_{\text{spec}} - s_{\text{hub}} \quad (\text{Eq. 10})$$
   其中 $-s_{\text{hub}}$ 为节点度数的对数惩罚项，用于抑制高频泛化中心节点（如对话主角）淹没局部具体锚点。
3. **关系通道 9 项加性帧评分（`Eq. 11`）**：
   在 Neo4j 内部先按谓词过滤并截断至最多 $K_F = 240$ 个候选帧（`graph_retriever_v7.py:34`），随后按 9 项指标打分选出 Top $B_q^R$：
   $$s_F(f, q) = s_{\text{rel}} + s_{\text{entity}} + s_{\text{constraint}} + s_{\text{type}} + s_{\text{time}} + s_{\text{intersection}} + s_{\text{specificity}} + s_{\text{role}} + s_{\text{state}} \quad (\text{Eq. 11})$$
   - 关键设计：**状态项 $s_{\text{state}}$** 会读取事件状态字面量（区分 `planned` 计划中与 `completed` 已发生），在 `Count`、`List-union` 与 `Temporal` 问题中自动对“仅计划但未发生（planned）”的事件降权惩罚（直接解决了 MIRIX-1.0 在 LoCoMo 上把计划露营日与实际露营日混淆的痛点！）。
4. **作答期规则校验（`Answer-Time Verification`, `Sec 2.4 & App. 6.4`）**：
   作答 Agent 最多调用 5 次 `Read`。生成初稿 $\hat{y}$ 后，由无参考答案的规则校验器 `Check` 检查是否存在显式不确定表述、计数题缺少数字或与证据账本矛盾、回答中出现的月份/数字既不在证据账本也不在问题中等情况（以及所有 `Intersection` 问题），触发时仅追加 **1 次**重检索与 **1 次**重写（`Alg. 1 line 15`）。

---

### 3.4 AutoDream：语义锚点无损合并与程序技能引文蒸馏 (`Sec 2.5 & App. 6.5, Eq. 12–13`)
AutoDream 完全脱离前台写路径运行，并对语义记忆与程序记忆采取截然相反的治理策略：

1. **语义记忆巩固（`SemanticDream`: 只合锚点索引，绝不改写证据表 $P_u$）**：
   $$\operatorname{Dream}(P_u, G_u; \Delta_u) = (P_u, \widetilde{G}_u) \quad (\text{Eq. 12})$$
   - **触发条件与前沿边界 $\Delta_u$**：每摄入 5 个分块（Chunks）及最后一个分块后触发，仅检查本次新写入语义行背后的锚点 $\mathcal{A}_\Delta$，且仅限身份稳定类型 $\mathcal{T}_{\text{safe}} = \{\text{person, organization, location, object, concept}\}$（刻意排除 `event, date, content, method`，防事件坍缩）。
   - **候选对生成与负例缓存 $\mathcal{N}$（`Eq. 13`）**：
     $$\mathcal{C}_\Delta = \left\{(a, b) : a \in \mathcal{A}_\Delta,\; b \in \operatorname{NN}_4(a) \setminus \{a\},\; \cos(\mathbf{e}_a, \mathbf{e}_b) \ge 0.86,\; t_a = t_b \in \mathcal{T}_{\text{safe}}\right\} \quad (\text{Eq. 13})$$
     每个中间轮次最多验证 **80 对**未见候选对，最终轮最多验证 **120 对**（若有合并再追加 1 轮最多 **60 对**的修复轮）。被 LLM 否决的锚点对哈希写入负例缓存 $\mathcal{N}$，后续周期永不重复调用。
   - **交换律与结合律合并代数**：确认 $a \to b$ 同指后，取 $I_a^E \cup I_b^E$、$I_a^S \cup I_b^S$、累加提及计数、取最大准入分，并将所有帧角色边重连至 $b$，使合并结果与执行顺序完全无关。
2. **程序记忆蒸馏与编修（`ProceduralDream`: `session_experience_distiller.py` & `skill_experience_curator.py`）**：
   - 当后台累积满 5 个已完成任务会话（Task Sessions）时自动触发。
   - **第一步：原话引文强校验的会话成败与正反经验蒸馏（`Distill*`, `session_experience_distiller.py:1-68`）**：
     - 蒸馏器仅读取外部真实对话表 `Conversation Message Store`（物理屏蔽 Meta Agent 自身的内部记忆调度消息，`lines 61-67`）。
     - 在无外部 Ground-Truth 标签的情况下，蒸馏器必须先从会话记录中提取原话引文（`outcome_evidence`）判定任务结局 `outcome` $\in \{\text{succeeded}, \text{failed}, \text{unclear}\}$，再同时提炼**正向复用经验（`worth_learning`）**与**反向避坑教训（`worth_avoiding`）**。
     - **防模型幻觉自夸的确定性引文核验（`check_reply_outcome`, `lines 20-41`）**：代码强制对 LLM 给出的每条证据引文进行去空格/标点/大小写归一化子串匹配（`OUTCOME_QUOTE_MIN_CHARS`）。若引文在原对话中不存在，直接强制降级为 `unclear`；若成功结局仅出现在 Agent 自己的回复中而无工具或用户确认（`outcome_source == "agent_only"`），经验可信度上限被强制封顶为 `MEDIUM`；若失败结局仅有 Agent 自述而无外部报错，同样降级为 `unclear`。
   - **第二步：带闭环反馈与引文溯源的技能编修（`Curate*`, `skill_experience_curator.py`）**：
     - 蒸馏器还会对本轮会话中已挂载的每项旧技能给出执行反馈 `skill_feedback`（`followed`: `yes/partly/no/unclear`；`effect`: `helped/no_effect/hurt/unclear`，同样强制校验原文 Quote，`lines 43-59`）。
     - 编修器（Curator）据此在程序记忆库 $P_u^P$ 中创建、修改或删除 `Skill`，且修改的步骤必须附上所依据经验的原文 Quote 校验，形成从 `Skill 步骤 -> Experience 教训 -> 原始 Session 对话行` 的三级可验证溯源链。

---

## 四、实验设计与全量结果精读

### 4.1 MIRIX-1.0 实验结果：ScreenshotVQA 与 LoCoMo (`2507.07957 Sec 4, Tables 1–3`)

#### （1）ScreenshotVQA 多模态长程屏幕流基准（`2507.07957 Table 1 / source/4_experiments.tex:47-62`）
采集 3 名博士生 1 天至 1 个月的高分辨率（2K–4K）电脑屏幕截图（每秒抓拍，帧间相似度 $>0.99$ 自动跳过，共 `5,886`、`18,178`、`5,349` 张图像，合计 87 道人工精标问答），主干模型统一为 `gemini-2.5-flash-preview-04-17`，`GPT-4.1` 担任 Judge：

| 方法 | Student 1 Acc $\uparrow$ | Student 1 存储 $\downarrow$ | Student 2 Acc $\uparrow$ | Student 2 存储 $\downarrow$ | Student 3 Acc $\uparrow$ | Student 3 存储 $\downarrow$ | **Overall Acc $\uparrow$** | **Overall 存储 $\downarrow$** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Gemini` (Long-Context, 缩放至 256×256 取最近 3,600 张) | 0.0000 | 142.10 MB | 0.0952 | 438.86 MB | 0.2545 | 129.14 MB | 0.1166 | 236.70 MB |
| `SigLIP@50` (RAG, Top-50 原图检索) | 0.3636 | 22.55 GB | 0.4138 | 19.88 GB | 0.5455 | 2.82 GB | 0.4410 | 15.07 GB |
| **`MIRIX-1.0`** (流式批处理写入 SQLite 六类分库) | **0.5455** | **20.57 MB** | **0.5667** | **19.83 MB** | **0.6727** | **7.28 MB** | **0.5950** (`+35%` 对比 RAG) | **15.89 MB** (`-99.9%` 对比 RAG) |

#### （2）MIRIX-1.0 在 LoCoMo 上的表现（`2507.07957 Table 2 & Appendix Table 3`）
在 `gpt-4.1-mini` 主干下（3 次独立运行均值），`MIRIX-1.0` 取得 Single-Hop **`85.11%`**、Multi-Hop **`83.70%`**（超最强基线 Zep `69.16%` 达 `+14.54` 个百分点，甚至反超 `Full-Context` 的 `77.70%`）、Open-Domain `65.62%`、Temporal **`88.39%`**、Overall **`85.38%`**（三次运行分别为 `83.98% / 87.34% / 84.82%`），逼近 `Full-Context` 上界（`87.52%`）。

---

### 4.2 MIRIX-2.0 全量实验结果：用户记忆与智能体程序记忆 (`2611.12068 Sec 3 & App. 7`)

MIRIX-2.0 对三个递进配置进行了严格消融：
- **`M0` (`MIRIX-1.0` Flat Memory)**：仅使用六类分库扁平向量/BM25 检索，关闭超图与 AutoDream；
- **`M1` (`MIRIX-2.0` Graph Only)**：开启 PostgreSQL 证据平面 + Neo4j 保血缘 $n$ 元超图有界检索，关闭 AutoDream；
- **`M2` (`MIRIX-2.0` Graph + AutoDream)**：完整开启超图检索与离线 AutoDream 巩固（每 5 个 chunk 及末尾触发）。

#### （1）长程对话与文档 QA 五大基准对比（`2611.12068 Table 1, App. Table 4`）
主干模型为 `gpt-4.1-mini`（`temp=0, seed=42`），Topic 提取为 `gpt-4.1-nano`，LoCoMo 与 LongMemEval-S 采用 `gpt-4o-mini` 三票多数决评判：

| 方法 / 配置 | LoCoMo Overall | LoCoMo Multi-Hop | LoCoMo Temporal | LoCoMo Open | LoCoMo Single-Hop | **LongMemEval-S Acc** | **MAB: SHDocQA** | **MAB: MHDocQA** | **MAB: DetectiveQA** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `mem0` | 82.9 | 80.5 | 80.4 | 66.7 | 86.6 | 56.3 | 48.0 | 22.0 | 53.5 |
| `A-Mem` | 68.3 | 68.8 | 55.5 | 61.5 | 73.8 | 45.0 | 14.0 | 20.0 | 62.0 |
| `MemoryBank` | 59.5 | 70.9 | 14.6 | 52.1 | 73.6 | 39.7 | 34.0 | 28.0 | **67.6** |
| `Graphiti (Zep)` | 58.4 | 65.2 | 37.1 | 53.1 | 64.9 | 23.0 | 50.0 | 43.0 | 54.9 |
| `HyperMem` | 91.0 | 91.1 | 84.4 | **76.0** | **95.2** | 58.3 | 52.0 | 49.0 | 66.2 |
| **`MIRIX-1.0 (M0, Flat)`** | 85.7 | 83.3 | 85.0 | 70.8 | 88.3 | 58.8 | - | - | - |
| **`MIRIX-2.0 (M1, Graph)`** | 88.4 | 89.0 | 86.0 | 71.9 | 91.1 | 70.0 | **83.0** (`+31.0`) | **71.0** (`+22.0`) | 64.8 |
| **`MIRIX-2.0 (M2, Graph+Dream)`** | **91.4** | **91.8** | **89.4** | 74.0 | 94.1 | **72.6** (`+14.3`) | - | - | - |

- **核心消融结论**：
  1. 从 `M0 -> M1`（引入 $n$ 元超图与双通道预算检索）：LoCoMo Multi-Hop 直接跃升 **`+5.7` 个百分点**（`83.3% -> 89.0%`），LongMemEval-S 暴涨 **`+11.2` 个百分点**（`58.8% -> 70.0%`），单跳/多跳长文档 QA（SHDocQA / MHDocQA）分别领先最强基线 HyperMem **`+31.0`** 和 **`+22.0`** 个百分点。
  2. 从 `M1 -> M2`（引入 `SemanticDream` 离线实体锚点合并）：LoCoMo 全类别普涨，Overall 从 `88.4%` 提升至 **`91.4%`**（其中 Temporal 提升 `+3.4` 个百分点至 **`89.4%`**），LongMemEval-S 进一步提升至 **`72.6%`**（领先最强基线 `HyperMem` 达 **`+14.3` 个百分点**）。

#### （2）Agent 程序记忆评测：ALFWorld、WebShop 与 MetaClaw-Bench（`2611.12068 Tables 2, 3, 6, 7`）
验证 `ProceduralDream` 从训练任务会话（ALFWorld 39 题、WebShop 40 题）中自动蒸馏经验并编修 `Skill` 后，冻结记忆库在测试集（ALFWorld 134 题、WebShop 140 题，3 次独立运行均值 $\pm$ 标准差）上的泛化表现：

| 评测基准与主干模型 | 对比方法 | 训练 Token 开销 (M) $\downarrow$ | 测试 Token 开销 (M) $\downarrow$ | **测试集平均成功率 (%) $\uparrow$** | 平均步数 (全体 / 成功样本) $\downarrow$ |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **ALFWorld**<br>(`GPT-6 Luna`, 134 题) | `No memory` | 0 | 2.147 $\pm$ 0.048 | 69.4 $\pm$ 0.7 | 25.2 / 14.2 |
| **ALFWorld** (`GPT-6 Luna`) | `ReasoningBank` | **1.747 $\pm$ 0.122** | **3.351 $\pm$ 0.045** | 66.9 $\pm$ 2.8（发生负迁移） | 26.4 / 14.7 |
| **ALFWorld** (`GPT-6 Luna`) | `AWM` | 2.749 $\pm$ 0.059 | 3.674 $\pm$ 0.332 | 73.6 $\pm$ 1.9 | 23.2 / 13.6 |
| **ALFWorld** (`GPT-6 Luna`) | **`MIRIX-2.0`** | 2.253 $\pm$ 0.100 | 3.813 $\pm$ 0.490 | **76.4 $\pm$ 6.2**（Clean `+14.0`, Heat `+26.1`） | **21.9** / **13.2** |
| **ALFWorld**<br>(`GPT-5.6 Luna`, 134 题) | `No memory` / `ReasoningBank` / `AWM` | - | - | 54.2 $\pm$ 1.1 / 52.2 $\pm$ 0.7 / 58.0 $\pm$ 2.8 | 31.6 / 31.4 / 29.9 |
| **ALFWorld** (`GPT-5.6 Luna`) | **`MIRIX-2.0`** | - | - | **61.7 $\pm$ 14.0** | **26.8** / **12.4** |
| **WebShop**<br>(`GPT-6 Luna`, 140 题) | `No memory` | 0 | 4.238 $\pm$ 0.463 | 31.9 $\pm$ 1.8 | 7.9 / 6.2 |
| **WebShop** (`GPT-6 Luna`) | `ReasoningBank` | 2.010 $\pm$ 0.242 | 6.620 $\pm$ 0.674 | 25.7 $\pm$ 3.8（发生负迁移） | 10.2 / 6.9 |
| **WebShop** (`GPT-6 Luna`) | `AWM` | 1.909 $\pm$ 0.127 | 5.448 $\pm$ 0.356 | 36.0 $\pm$ 4.3 | 9.1 / 6.9 |
| **WebShop** (`GPT-6 Luna`) | **`MIRIX-2.0`** | **1.815 $\pm$ 0.054** | **4.975 $\pm$ 0.340** | **37.4 $\pm$ 2.1**（成本最低且成功率最高） | **8.2** / **6.3** |
| **MetaClaw-Bench Part I**<br>(`GPT-5.2`, 跨 30 天 346 题) | `Baseline` / `MetaClaw Skills` / **`MIRIX-2.0`** | - | - | Acc: `41.1%` / `44.0%` / **`49.2%`**<br>文件检查完成率: `14.7%` / `17.1%` / **`27.7%`** | - |

#### （3）系统摄取耗时与单题检索作答延迟对比（`2611.12068 App. Table 8`）
在全部 5 个计时基准上，`MIRIX-2.0 (M1)` 的**单题平均作答耗时（`Ans./q`）全面快于最强超图基线 `HyperMem`**：
- **LoCoMo**：摄取耗时 `21,416 s`（对比 HyperMem `69,467 s`，**快 3.2 倍**），单题作答 **`5.46 s`**（对比 HyperMem `9.70 s`），构建超图规模为 `23,820` 节点 / `32,394` 边。
- **LongMemEval-S**：摄取耗时 `70,626 s`（对比 HyperMem `170,224 s`，**快 2.4 倍**），单题作答 **`10.10 s`**（对比 HyperMem `10.73 s`），超图规模 `181,131` 节点 / `205,428` 边。
- **SHDoc / MHDoc / DetectiveQA**：单题作答分别为 **`5.45 s / 9.01 s / 7.24 s`**（均显著快于 HyperMem 的 `10.55 s / 10.65 s / 13.05 s`），但长文档建图使摄取耗时较扁平记忆 `M0` 增加约 `3.8~4.0` 倍。

---

## 五、论文-源码深度对账与对我们项目的直接启发 (`repos/MIRIX`)

### 5.1 开源仓库中的工程演进与未写入论文正文的实战机制
通过审阅 `D:\coding\sharing\papers\repos\MIRIX\mirix\services\` 源码，发现开源实现包含多项极具价值的工程设计：
1. **从 `v7.10` 二元边到 `v7.12` $n$ 元框架的真实重构教训（`frame_extractor.py:1-98`）**：
   - 源码注释坦诚披露：早期版本 `v7.10` 虽名为超图，但底层提取器只输出 `(subject, predicate, object)`，实测 534 条事实中 **100% 都是二元边（arity=2）**，且把 `"42 campsites"`、日期等数值当成实体锚点，严重污染了实体合并空间。`v7.12` 因此强制引入 `_ROLE_CANON` 角色归一表、`_LITERAL_ROLES` 数值剥离规则以及当フレーム元数 `arity > 4`（`_CLIQUE_MAX_ARITY = 4`）时将二元投影从完全图（Clique）退化为星型图（Star）以防组合爆炸（`lines 48-50, 169-180`）。
2. **显式冲突消解策略与 `prior_values` 历史被替代值保留（`meta_agent.py:160-186`）**：
   - 在 `MetaAgent` 的 `_CONFLICT_RESOLUTION_POLICY_PROMPT` 中，源码明确禁止 LLM 在遇到前后矛盾事实（如出生地变更或套餐变更）时自行编造折中摘要（`"X, though some data says Y"`），而是强制以 `"<entity> / <relation>"` 为键、最新原话为 `summary`，并由 `SemanticMemoryManager` 自动将旧值标记为 `superseded` 存入 `prior_values` 列表！
3. **Graph Context 注入位置实测教训（`graph_retriever_v7.py:122-129`）**：
   - 源码注释指出：如果把超图检索到的事实拼成一段静态文本塞进 System Prompt，实测在 60 道探针题上 **“60/60 次被回答模型完全无视（moved nothing）”**；只有将超图事实转化为结构化行（`V7MemoryRow`）并直接作为回答 Agent 自身调用的搜索工具返回值（Tool Output）合并进去，才能真正提升 QA 准确率。

### 5.2 对我们「联接 Agent 多源记忆架构与评测体系」的落地启发
1. **直接支撑主报告 `3.2 节 / 3.4 节` 的分库与“证据平面 + 索引平面分离”原则**：
   - MIRIX-2.0 的 **“Typed Evidence Plane（PostgreSQL 唯一事实源）+ Provenance Hypergraph（只存 ID 与结构索引、带 `C_f` 原文行引文）”** 完美契合我们的网元单据与对话混合架构：原始网元单据与对话原话作为不可篡改的底层证据表（System of Record），上层画像槽位与关联表仅作为携带 `source_row_ids` 的索引层，任何后台合并（AutoDream）只更新实体对齐索引而绝不覆写原始单据与对话记录。
2. **借鉴 `Occurrence Identity`（`Eq. 7–8`）与 `s_state`（区分 `planned` 与 `completed`）解决多单据/多轮次混淆**：
   - 在通信排障与保障场景中，用户常在不同日期多次发起相似诉求（如多次“晚间打王者荣耀卡顿”）或先咨询计划（`planned`）后实际办理（`completed`）。引入 `id_E(f) = H(u, p, \sigma(f), \chi(f))` 及事件完成态字面量，能从根源上防止无显式日期的多次历史卡顿单据在记忆库中被错误去重坍缩为 1 次（保障频次阈值 $N_{\text{min}}$ 统计的准确性）。
3. **借鉴 `ProceduralDream` 的“原文 Quote 存在性硬核验 + 外部工具结果定成败”机制（对齐 `3.3.3 节` 慢路径经验沉淀）**：
   - MIRIX-2.0 在 `session_experience_distiller.py` 中发现：若不加校验，LLM 极易把 Agent 自己的礼貌回复当成任务成功，或凭空捏造经验。强制要求提炼经验规则时必须附带**真实网元运行回执/用户确认的原话子串 Quote 校验（`check_reply_outcome`）**，并对仅有 Agent 自述而无网元侧实测支撑的经验降级处理，可直接作为我们慢路径经验规则入库前的确定性安全门控。

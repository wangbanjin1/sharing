# 2 MemoryOS：操作系统式三级分层存储与段页式热度晋升

← [精读索引](../reading_notes.md)　·　[上一篇：01 Mem0](01_memory_mem0.md)　·　[论文目录](../../README.md)　·　[数据集图鉴](../datasets.md)

**出处**：Jiazheng Kang, Mingming Ji, Zhe Zhao, Ting Bai（北京邮电大学 & 腾讯），*MemoryOS of AI Agent*，`arXiv:2506.06326v2`，录用于 *EMNLP 2025 Main Conference (Oral)*。  
**本地材料**：[MemoryOS_2025.pdf](../../memory/MemoryOS_2025.pdf)　·　[LaTeX 转 Markdown 全文](../../memory/2506.06326/2506.06326.md)　·　[LaTeX 源码 `acl_latex.tex`](../../memory/2506.06326/source/latex/acl_latex.tex)　·　[开源仓库 `repos/MemoryOS`](../../repos/MemoryOS)  
**标注层级**：〔正文〕论文原文明确写出 / 〔图表〕见于图或表 / 〔注释〕见于 LaTeX 源码注释块 / 〔实现〕开源仓库代码与配置 / 〔推导〕按原文数字算出 / 〔推断/评价〕基于原文与主报告场景的对照分析

## 2.1 背景、定位与操作系统内存类比（Sec 1–2, Fig. 1）

论文将现有大模型记忆机制归纳为三类，并指出其各自的单维局限〔正文 Sec 1–2.1〕：

1. **知识组织型（Knowledge-Organization，如 `TiM`、`A-Mem`）**：将中间推理或对话构造成互联笔记网络，但多步建链导致写入延迟与累计误差随轮数急剧上升（`A-Mem` 平均每轮需 13 次 LLM 调用）〔正文 Sec 2.1, Sec 4.2〕；
2. **检索机制导向型（Retrieval-Oriented，如 `MemoryBank`、`EmotionalRAG`）**：引入艾宾浩斯遗忘曲线衰减历史记录，但缺乏中期主题聚合层，长对话下极易发生主题漂移与跨轮语境断裂〔正文 Sec 2.1, Sec 4.2〕；
3. **架构驱动型（Architecture-Driven，如 `MemGPT`、`SCM`、`Mem0`）**：`MemGPT` 虽借鉴了操作系统内存/磁盘两级换页，但其扁平 FIFO 队列在超长对话中会把不同主题混杂在一起，且每次检索注入高达 16,977 tokens〔正文 Sec 2.1, Sec 4.2, 图表 Table 3〕。

为此，MemoryOS 引入经典操作系统（如 Multics，Bensoussan et al. 1972；Denning 1970）的**段页式内存管理（Segmented Paging）**与**基于热度的页面置换（Heat-Based Eviction）**思想，将记忆系统划分为 **存储（Storage）**、**更新（Updating）**、**检索（Retrieval）**与**生成（Generation）**四大协同模块〔正文 Sec 1, Sec 2.2, Sec 3.1, 图表 Fig. 1〕。

---

<a id="c2-2"></a>

## 2.2 三级分层存储架构与数学定义（Sec 3.2, Eq. 1–3）

MemoryOS 的存储模块由 **短期记忆（STM）**、**中期记忆（MTM）**与**长期个人记忆（LPM）**三级组成〔正文 Sec 3.2〕：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. 短期记忆 (STM: Short-Term Memory) —— 定长 FIFO 对话页队列 (论文 N=7)       │
│    • 对话页：page^chain_i = {Q_i, R_i, T_i, meta^chain_i}           (Eq. 1) │
│    • 对话链：LLM 判定前后页连续性 (pre_page ↔ next_page)，生成滚动摘要        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ 队列满：FIFO 弹出最老页
                                       │ LLM 多主题切分 (Multi-Summary)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. 中期记忆 (MTM: Mid-Term Memory) —— 段页式 (Segmented Paging, 论文上限 200) │
│    • 段合并准则：F_score = cos(e_s, e_p) + |K_s ∩ K_p| / |K_s ∪ K_p| > θ    │
│    • 热度评分：  Heat = α·N_visit + β·L_interaction + γ·exp(-Δt / μ) (Eq. 4)│
│    • 容量控制：  段数超上限时淘汰最低热度段（注：源码实际为纯 LFU 淘汰）       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ 段热度 Heat > τ (论文 τ=5.0)
                                       │ 抽取未分析页后重置 L_interaction ← 0
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. 长期个人记忆 (LPM: Long-Term Personal Memory) —— 双主体六子项持久化画像    │
│    • 用户侧 (User Persona)：                                                 │
│      ① User Profile（静态属性：姓名/性别/出生年）                             │
│      ② User KB（动态私有事实库，FIFO 容量 100 条）                            │
│      ③ User Traits（3 大类 90 维偏好标签：High / Medium / Low 三档演化）      │
│    • 助手侧 (Agent Persona)：                                                │
│      ④ Agent Profile（固定角色设定） + ⑤ Agent Traits / KB（FIFO 容量 100 条）│
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1. 短期记忆（STM）：带链式元信息的对话页（Sec 3.2, Eq. 1）

STM 以固定长度队列存储实时对话，基本单元为**对话页（Dialogue Page）**。为防止跨轮对话在语义表面跳跃但上下文实际连贯时丢失指代，每页附带由 LLM 维护的对话链元信息 $\text{meta}^{\text{chain}}_i$〔正文 Sec 3.2, Eq. 1〕：

$$\text{page}^{\text{chain}}_i = \big\{Q_i,\ R_i,\ T_i,\ \text{meta}^{\text{chain}}_i\big\}$$

其中 $Q_i$ 为用户查询，$R_i$ 为模型回复，$T_i$ 为时间戳。$\text{meta}^{\text{chain}}_i$ 分两步生成：① 调用 LLM 判断新页与前序页是否处于同一连续语境（若连贯则挂载 `pre_page / next_page` 双向链表指针，若话题切换则重置新链）；② 将当前链上的对话浓缩为 1～2 句链级背景摘要 $\text{meta}^{\text{chain}}_i$〔正文 Sec 3.2，实现 `updater.py:55-97`〕。

### 2. 中期记忆（MTM）：段页式（Segmented Paging）聚合（Sec 3.2, Eq. 2–3）

MTM 将逻辑上属于同一话题的多条对话页（Pages）聚合进同一个**主题段（Segment）**。每个主题段定义为满足综合相似度门限 $\theta$ 的对话页集合〔正文 Sec 3.2, Eq. 2–3〕：

$$\text{segment}_i = \big\{\text{page}_j \;\big|\; \mathcal{F}_{\text{score}}(\text{page}_j, \text{segment}_i) > \theta\big\}$$

$$\mathcal{F}_{\text{score}} = \cos(\mathbf{e}_s, \mathbf{e}_p) + \mathcal{F}_{\text{Jaccard}}(K_s, K_p), \qquad \mathcal{F}_{\text{Jaccard}}(K_s, K_p) = \frac{|K_s \cap K_p|}{|K_s \cup K_p|}$$

符号解释如下：

- $\mathbf{e}_s, \mathbf{e}_p$：分别为主题段摘要与对话页的语义嵌入向量；
- $K_s, K_p$：分别为 LLM 从主题段摘要与对话页中抽取的关键词集合；
- $\theta$：段合并阈值，论文实验固定设为 $\theta = 0.6$〔正文 Sec 3.2, Sec 4.1〕。

### 3. 长期个人记忆（LPM）：用户与助手双主体画像（Sec 3.2）

LPM 细分为 **User Persona** 与 **Agent Persona** 两部分〔正文 Sec 3.2〕：

| 主体              | 子模块名称            | 性质与容量设定                  | 存储内容（Sec 3.2 & Appendix）                                                                                                                                                                                                                                      |
|:----------------- |:--------------------- |:------------------------------- |:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **User Persona**  | **User Profile**      | 静态结构化字段                  | 姓名、性别、出生年份等固定人口统计学属性〔正文 Sec 3.2〕                                                                                                                                                                                                            |
| **User Persona**  | **User KB**           | 动态 FIFO 队列（上限 $100$ 条） | 从高热度 MTM 段中持续提炼的用户客观私有事实条目（附时间戳与向量）〔正文 Sec 3.2, Sec 3.3〕                                                                                                                                                                          |
| **User Persona**  | **User Traits**       | 动态定维槽位（固定 **90 维**）  | 借鉴 ALIGNX 心理模型，划分为 **心理需求与大五人格（16 维）**、**AI 对齐偏好（8 维）**与**内容平台兴趣与沟通风格（66 维）**三大类共 90 个维度，每维由 LLM 评定 `High / Medium / Low` 强度并附对话证据〔正文 Sec 3.3，源码 `acl_latex.tex` L1300–1384，`prompts.py`〕 |
| **Agent Persona** | **Agent Profile**     | 静态设定                        | 助手扮演的角色定位与固定性格设定〔正文 Sec 3.2〕                                                                                                                                                                                                                    |
| **Agent Persona** | **Agent Traits / KB** | 动态 FIFO 队列（上限 $100$ 条） | 对话中用户对助手新增的要求或助手自身做出的承诺、推荐记录（如 *"I recommend Interstellar on 2023-10-01"*），防止助手跨会话“言行不一”〔正文 Sec 3.2, 源码 `acl_latex.tex` L1263–1269〕                                                                                |

---

<a id="c2-3"></a>

## 2.3 跨层动态更新与两阶段检索机制（Sec 3.3–3.4, Eq. 4–5）

### 1. STM → MTM 更新（FIFO 弹出与多主题切分）

每当新问答对写入 STM 导致队列满（论文设长度 $N=7$〔正文 Sec 4.1〕）时，最老的对话页按 FIFO 原则弹出并迁移至 MTM〔正文 Sec 3.3〕：

1. 先执行对话链连续性判定与 $\text{meta}^{\text{chain}}_i$ 更新；
2. 调用多主题摘要提示词（最多拆出 2 个子主题 `{"theme", "keywords", "content"}`〔源码 `acl_latex.tex` L1132–1140〕），计算与现有 MTM 各段的 $\mathcal{F}_{\text{score}}$：若最大得分 $> \theta$（$0.6$），则追加进该段并累加该段的交互页数 $L_{\text{interaction}}$；否则新建一个主题段〔正文 Sec 3.2–3.3〕。

### 2. MTM → LPM 更新（基于热度 $\text{Heat}$ 的晋升、清零与淘汰，Eq. 4）

MTM 中每个主题段实时维护热度分数 $\text{Heat}$〔正文 Sec 3.3, Eq. 4〕：

$$\text{Heat} = \alpha \cdot N_{\text{visit}} + \beta \cdot L_{\text{interaction}} + \gamma \cdot R_{\text{recency}}, \qquad R_{\text{recency}} = \exp\!\left(-\frac{\Delta t}{\mu}\right)$$

| 参数符号                 | 物理含义                                           | 论文设定值（Sec 3.3 & Sec 4.1）                                               |
|:------------------------ |:-------------------------------------------------- |:----------------------------------------------------------------------------- |
| $N_{\text{visit}}$       | 该主题段在检索阶段被命中的累计次数（高频访问指标） | 初始为 $0$，每次检索命中 $+1$〔正文 Sec 3.3, Sec 3.4〕                        |
| $L_{\text{interaction}}$ | 该主题段内当前未沉淀的对话页数量（深度参与指标）   | 随新页合并入段而累加，**晋升 LPM 后重置为 $0$**〔正文 Sec 3.3〕               |
| $R_{\text{recency}}$     | 距上次检索访问的时间衰减系数，$\Delta t$ 为秒数    | 时间常数设为 $\mu = 10^7\text{ 秒}$（约 $115.7$ 天）〔正文 Sec 3.3, Sec 4.1〕 |
| $\alpha, \beta, \gamma$  | 三项指标的加权系数                                 | 论文设 $\alpha = \beta = \gamma = 1$〔正文 Sec 4.1〕                          |
| $\tau$                   | MTM 向 LPM 晋升的热度触发阈值                      | 论文设 $\tau = 5$〔正文 Sec 3.3, Sec 4.1〕                                    |

基于 $\text{Heat}$ 执行两项核心操作〔正文 Sec 3.3〕：

1. **容量淘汰（Segment Eviction）**：论文规定当 MTM 段总数超过上限（$200$ 个段）时，淘汰 $\text{Heat}$ 最低的段，并在删除前修复被删页的 `pre_page / next_page` 双向链表指针以防断链〔正文 Sec 3.3，注释 `acl_latex.tex` L534–535〕；
2. **长期画像晋升与热度清零（LPM Promotion & Reset）**：当堆顶主题段的 $\text{Heat} > \tau$（$5$）时，系统提取该段中尚未分析的对话页（`analyzed == False`），调用 LLM 同步更新 `User Traits`（90 维）、`User KB` 与 `Agent Traits`（后两者入 100 条 FIFO 队列）。**关键防重设计**：晋升完成后，将该段内页面标记为已分析，并将公式中的 **$L_{\text{interaction}}$ 重置为 $0$**，使该段的 $\text{Heat}$ 立即回落至阈值以下，从而只允许后续新产生的未分析对话再次触发画像演化〔正文 Sec 3.3 `acl_latex.tex` L623〕。

### 3. 三层协同检索（Memory Retrieval, Sec 3.4, Eq. 5）

给定用户查询 $Q$，检索算子 $\mathcal{F}_{\text{Retrieval}}(\text{STM}, \text{MTM}, \text{LPM} \mid Q)$ 并行汇总三路结果拼入最终生成 Prompt〔正文 Sec 3.4–3.5〕：

- **STM 检索**：全量取回队列中最近的 $7$ 个对话页；
- **MTM 两阶段段页式检索**：第一阶段按 Eq. 3 的 $\mathcal{F}_{\text{score}}$ 选出 Top-$m$（实验设 $m=5$）个候选主题段；第二阶段在这些候选段内部，计算查询向量与每个对话页向量的余弦相似度，选出全局 Top-$k$（GVD 设 $k=5$，LoCoMo 设 $k=10$〔正文 Sec 4.1 `acl_latex.tex` L914〕）个对话页（连同其 $\text{meta}^{\text{chain}}$），并刷新命中段的 $N_{\text{visit}}$ 与 $R_{\text{recency}}$；
- **LPM 检索**：全量读取静态 `User Profile`、`Agent Profile` 与 90 维 `User Traits`，同时用向量相似度分别从 `User KB` 和 `Agent Traits` 中检索 Top-10 条事实知识〔正文 Sec 3.4〕。

---

<a id="c2-4"></a>

## 2.4 实验设置、完整结果矩阵与消融分析（Sec 4, Table 1–3, Fig. 2–3）

> 注：LaTeX 源码 [`acl_latex.tex`](../../memory/2506.06326/source/latex/acl_latex.tex#L808-L905) 中的 Table 2（`table*`）与 Fig. 2（`figure*`）在 pandoc 转换时被折叠，以下完整表格与实验数据均直接核对自 `acl_latex.tex` 源码与 PDF 原文。

### 1. Table 1：GVD 长对话基准对比（`acl_latex.tex` L808–837）〔图表 Table 1〕

**GVD 数据集设定**：基于 MemoryBank 构建的 15 名虚拟用户跨 10 天（每天至少 2 个话题）的多轮长对话，由 `DeepSeek-R1` 自动评测三项指标：**记忆检索准确率 `Acc.`（0/1 二值）**、**回复正确性 `Corr.`（0 / 0.5 / 1 三档）**与**上下文连贯性 `Cohe.`（0 / 0.5 / 1 三档）**〔正文 Sec 4.1〕：

| 底座模型（Model） | 方法（Method）       | 检索准确率 `Acc.` $\uparrow$ | 回复正确性 `Corr.` $\uparrow$ | 上下文连贯性 `Cohe.` $\uparrow$ |
|:----------------- |:-------------------- |:----------------------------:|:-----------------------------:|:-------------------------------:|
| **GPT-4o-mini**   | TiM                  | 84.5                         | 78.8                          | 90.8                            |
| **GPT-4o-mini**   | MemoryBank           | 78.4                         | 73.3                          | 91.2                            |
| **GPT-4o-mini**   | MemGPT               | 87.9                         | 83.2                          | 89.6                            |
| **GPT-4o-mini**   | A-Mem（次优）        | 90.4                         | 86.5                          | 91.4                            |
| **GPT-4o-mini**   | **MemoryOS（Ours）** | **93.3**（$+3.2\%$）         | **91.2**（$+5.4\%$）          | **92.3**（$+1.0\%$）            |
| **Qwen2.5-7B**    | TiM                  | 82.2                         | 73.2                          | 85.5                            |
| **Qwen2.5-7B**    | MemoryBank           | 76.3                         | 70.3                          | 82.7                            |
| **Qwen2.5-7B**    | MemGPT               | 85.1                         | 80.2                          | 86.9                            |
| **Qwen2.5-7B**    | A-Mem（次优）        | 87.2                         | 79.5                          | 87.8                            |
| **Qwen2.5-7B**    | **MemoryOS（Ours）** | **91.8**（$+5.3\%$）         | **82.3**（$+3.5\%$）          | **90.5**（$+3.1\%$）            |

### 2. Table 2：LoCoMo 四类题型与双底座完整对比（`acl_latex.tex` L839–878）〔图表 Table 2〕

> **关键列序核对**：在 `acl_latex.tex` L848–851 中，Table 2 的四列顺序依次为 **Single-Hop $\rightarrow$ Multi-Hop $\rightarrow$ Temporal $\rightarrow$ Open-Domain**，且第二个开源小模型底座在 LoCoMo 上实际使用的是 **`Qwen2.5-3B`**（而非 GVD 上的 7B），表中 $\text{A-Mem}^*$ 为作者在相同环境下复现的结果〔图表 Table 2〕：

| 底座模型        | 方法                               | Single-Hop F1 / B1      | Multi-Hop F1 / B1      | Temporal F1 / B1          | Open-Domain F1 / B1     | 平均排名（F1 / B1）$\downarrow$ |
|:--------------- |:---------------------------------- |:-----------------------:|:----------------------:|:-------------------------:|:-----------------------:|:-------------------------------:|
| **GPT-4o-mini** | TiM                                | 16.25 / 13.12           | 18.43 / 17.35          | 8.35 / 7.32               | 23.74 / 22.05           | 3.8 / 4.0                       |
| **GPT-4o-mini** | MemoryBank                         | 5.00 / 4.77             | 9.68 / 6.99            | 5.56 / 5.94               | 6.61 / 5.16             | 5.0 / 5.0                       |
| **GPT-4o-mini** | MemGPT                             | 26.65 / 17.72           | 25.52 / 19.44          | 9.15 / 7.44               | 41.04 / 34.34           | 2.2 / 2.5                       |
| **GPT-4o-mini** | A-Mem（原论文报分）                | 27.02 / 20.09           | **45.85 / 36.67**      | 12.14 / 12.00             | 44.65 / 37.06           | — / —                           |
| **GPT-4o-mini** | $\text{A-Mem}^*$（作者同环境复现） | 22.61 / 15.25           | 33.23 / 29.11          | 8.04 / 7.81               | 34.13 / 27.73           | 3.0 / 2.5                       |
| **GPT-4o-mini** | **MemoryOS（Ours）**               | **35.27 / 25.22**       | 41.15 / 30.76          | **20.02 / 16.52**         | **48.62 / 42.99**       | **1.0 / 1.0**                   |
| **GPT-4o-mini** | *相对次优复现基线提升*             | *$+32.35\% / +42.33\%$* | *$+23.83\% / +5.67\%$* | *$+118.80\% / +111.52\%$* | *$+18.47\% / +25.19\%$* | —                               |
| **Qwen2.5-3B**  | TiM                                | 4.37 / 5.01             | 2.54 / 3.21            | 6.20 / 5.37               | 6.35 / 7.34             | 4.3 / 3.5                       |
| **Qwen2.5-3B**  | MemoryBank                         | 3.60 / 3.39             | 1.72 / 1.97            | 6.63 / 6.58               | 4.11 / 3.32             | 4.8 / 4.8                       |
| **Qwen2.5-3B**  | MemGPT                             | 5.07 / 4.31             | 2.94 / 2.95            | 7.04 / 7.10               | 7.26 / 5.52             | 2.8 / 3.8                       |
| **Qwen2.5-3B**  | A-Mem（原论文报分）                | 12.57 / 9.01            | **27.59 / 25.07**      | 7.12 / 7.28               | 17.23 / 13.12           | — / —                           |
| **Qwen2.5-3B**  | $\text{A-Mem}^*$（作者同环境复现） | 10.31 / 8.76            | 16.31 / 11.07          | 6.94 / 7.31               | 12.34 / 10.62           | 2.3 / 2.0                       |
| **Qwen2.5-3B**  | **MemoryOS（Ours）**               | **23.26 / 15.39**       | 21.44 / 14.95          | **10.18 / 8.18**          | **26.23 / 22.39**       | **1.0 / 1.0**                   |

> **Table 2 中的一处跨论文题型映射错位（需特别注意）〔图表 Table 2 对比 Mem0 Table 1〕**：
> 在 `A-Mem` 原论文与 `Mem0` Table 1 中，`A-Mem` 的四个 F1 分数依次是 `Single-Hop = 27.02`、`Multi-Hop = 12.14`、`Open-Domain = 44.65`、`Temporal = 45.85`；而在 `MemoryOS` 的 Table 2（`acl_latex.tex` L860）中，作者把 `A-Mem` 的 `45.85` 填到了 `Multi-Hop` 列，把 `12.14` 填到了 `Temporal` 列（即将 LoCoMo 的 `category` 编号 2 和 3 的列头对调了）！这也解释了为什么 `MemoryOS` 在 Table 2 中报出的 `Temporal` F1 为 `20.02`（实际对应 Multi-Hop 类）、而 `Multi-Hop` F1 为 `41.15`（实际对应 Temporal 类）。

### 3. Table 3：LoCoMo 检索 Token 开销与平均 LLM 调用次数对比（`acl_latex.tex` L880–897）〔图表 Table 3〕

| 方法（Method）       | 每次回答召回 Token 数（Tokens） | 全流程平均 LLM 调用次数（Avg. Calls） | LoCoMo 四类平均 F1（Avg. F1） |
|:-------------------- |:-------------------------------:|:-------------------------------------:|:-----------------------------:|
| **MemoryBank**       | 432                             | 3.0                                   | 6.84                          |
| **TiM**              | 1,274                           | 2.6                                   | 18.01                         |
| **MemGPT**           | 16,977                          | 4.3                                   | 29.13                         |
| **$\text{A-Mem}^*$** | 2,712                           | 13.0                                  | 26.55                         |
| **MemoryOS（Ours）** | **3,874**                       | **4.9**                               | **36.23**                     |

Table 3 明确给出 MemoryOS 从接收查询到记忆写入稳定化的平均 LLM 调用次数为 **4.9 次/轮**（显著低于 `A-Mem*` 的 13.0 次，与 `MemGPT` 的 4.3 次相当，但召回 Token 数仅为 `MemGPT` 的 $22.8\%$）〔正文 Sec 4.2 `acl_latex.tex` L969–975〕。

### 4. 模块消融实验与超参 $k$ 敏感度分析（Sec 4.3–4.4, Fig. 2–3）

1. **三核心模块消融（Sec 4.3, Fig. 2 & `acl_latex.tex` L999–1006 注释表）**：
   在 GVD（`Qwen2.5-7B`）上逐一移除三个核心组件后，指标从完整模型（`Acc. = 91.8`, `Corr. = 82.3`, `Cohe. = 90.5`）的跌落幅度依次为〔注释 `acl_latex.tex` L999–1006，图表 Fig. 2〕：
   - **`w/o MTM`（移除段页式中期记忆，暴跌最剧烈）**：`Acc.` 从 $91.8\%$ 暴跌至 **$46.4\%$**（$-45.4$ 个百分点），`Corr.` 跌至 **$44.6\%$**（$-37.7$ 个百分点），`Cohe.` 跌至 $66.0\%$；
   - **`w/o LPM / Persona Module`（移除长期个人画像，次之）**：`Acc.` 跌至 **$77.1\%$**（$-14.7$ 个百分点），`Corr.` 跌至 $70.5\%$，`Cohe.` 跌至 $72.3\%$；
   - **`w/o Dialogue Page Chain`（移除对话链 $\text{meta}^{\text{chain}}$，影响相对最小）**：`Acc.` 跌至 **$87.3\%$**（$-4.5$ 个百分点），`Corr.` 跌至 $80.5\%$，`Cohe.` 跌至 $88.3\%$。
     这一消融结果证明：**MTM 段页式主题聚合是承接短期对话与长期画像的核心桥梁**，缺少 MTM 会导致未达到长期画像门限的具体对话细节直接丢失〔正文 Sec 4.3〕。
2. **MTM 召回页数 $k \in \{5, 10, 20, 30, 40\}$ 敏感度（Sec 4.4, Fig. 3）**：随 $k$ 增大，LoCoMo 各题型 F1 稳步上升，在 $k=10$ 后边际收益显著放缓（简单题型在 $k=30$ 饱和，过多页面会引入无关噪声并增加 Token 成本），因此论文折中选取 $k=10$〔正文 Sec 4.4〕。

---

<a id="c2-5"></a>

## 2.5 开源仓库四套变体与论文实现的六处关键落差（`repos/MemoryOS`）

开源仓库 [`repos/MemoryOS`](../../repos/MemoryOS) 包含四套独立实现目录：`eval/`（论文跑 LoCoMo 实验的原始脚本）、`memoryos-pypi/`（标准 Python 包，引入线程池并发）、`memoryos-chromadb/`（ChromaDB + Redis 生产版）与 `memoryos-mcp/`（MCP Server 封装）〔实现〕。

将论文正文公式/参数与 `eval/` 及 `memoryos-pypi/` 源码逐行比对，存在 **6 处直接影响复现的落差**：

| #     | 机制维度                                                  | 论文正文写法〔正文〕                                                                                                   | 源码实际实现〔实现〕                                                                                                                                                                                                                                                                                                                                                                                                                        | 复现与机制后果                                                                                                                                                        |
|:----- |:--------------------------------------------------------- |:---------------------------------------------------------------------------------------------------------------------- |:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |:--------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1** | **MTM 段满溢淘汰策略**                                    | Sec 3.3 称当段数超上限时，**淘汰热度 $\text{Heat}$ 最低的段**（*"segments with the lowest heat are evicted"*）         | [`mid_term.py:71-101`](../../repos/MemoryOS/memoryos-pypi/mid_term.py#L71-L101) 与 [`eval/mid_term_memory.py:56-76`](../../repos/MemoryOS/eval/mid_term_memory.py#L56-L76) 的 `evict_lfu()` 实际执行 `min(self.access_frequency, key=self.access_frequency.get)`，即**纯 LFU（仅按检索命中次数淘汰）**；而 `self.heap` 存的是 `-H_segment` 最大堆，仅用于挑最热段晋升 LPM                                                                   | 新写入的长对话段（$L_{\text{interaction}}$ 很高但尚未被检索命中，$N_{\text{visit}}=0$）哪怕 $\text{Heat}$ 很高，在触发淘汰时也会因 `access_frequency == 0` 被优先误删 |
| **2** | **评测脚本 `eval/` 的真实容量配置**                       | Sec 4.1 声明：`STM = 7`、`MTM = 200`、`User KB = 100`                                                                  | 在跑出论文 LoCoMo 分数的 [`eval/main_loco_parse.py:233-235`](../../repos/MemoryOS/eval/main_loco_parse.py#L233-L235) 中：<br/>• `ShortTermMemory(max_capacity=1)`（**每 1 轮立即刷入 MTM**）；<br/>• `MidTermMemory(max_capacity=2000)`（远超单样本总轮数，**从不触发 MTM 淘汰**）；<br/>• [`eval/long_term_memory.py:9`](../../repos/MemoryOS/eval/long_term_memory.py#L9) 用无限长 `list` 存储知识（**无 100 条上限**）                   | 论文在 LoCoMo 上的跑分实际上是在 **“零容量淘汰（MTM=2000 + LPM 无限容量）+ 逐轮全量归档（STM=1）”** 条件下测得的，并未检验容量受限时的淘汰抗损能力                    |
| **3** | **时间衰减常数 $\mu$ 与热度权重 $\alpha, \beta, \gamma$** | Eq. 4 与 Sec 4.1 写明 $\Delta t$ 以秒为单位，$\mu = 10^7\text{ 秒}$（约 $115.7$ 天），且 $\alpha = \beta = \gamma = 1$ | ① [`mid_term.py:24`](../../repos/MemoryOS/memoryos-pypi/mid_term.py#L24) 设 `RECENCY_TAU_HOURS = 24`（即 $8.64 \times 10^4\text{ 秒}$，衰减快 115 倍），且权重设为 $\alpha=1, \beta=1, \gamma=2$；<br/>② [`eval/mid_term_memory.py:24, 213`](../../repos/MemoryOS/eval/mid_term_memory.py#L24) 设 $\alpha=0.8, \beta=0.8, \gamma=0.0001$，且检索时将时间衰减项 `#lambda_t = np.exp(-delta/tau)` 注释掉、硬编码为 `lambda_t = 1`             | 在论文评测脚本 `eval/` 中，时间衰减项 $R_{\text{recency}}$ 的权重为 $10^{-4}$ 且检索衰减被置为 $1$，实际上完全关闭了时间衰减                                          |
| **4** | **$\mathcal{F}_{\text{score}}$ 中的关键词相似度公式**     | Eq. 3 定义为标准 Jaccard：$\frac{\|K_s \cap K_p\|}{\|K_s \cup K_p\|}$                                                  | ① 在 `acl_latex.tex` L528 注释草稿与 [`eval/mid_term_memory.py:149, 218`](../../repos/MemoryOS/eval/mid_term_memory.py#L149) 中，实际计算的是双向覆盖率均值 $\frac{1}{2}\!\left(\frac{\|K_s \cap K_p\|}{\|K_s\|} + \frac{\|K_s \cap K_p\|}{\|K_p\|}\right)$；<br/>② 在 [`memoryos-pypi/mid_term.py:292`](../../repos/MemoryOS/memoryos-pypi/mid_term.py#L292) 检索函数中，直接写死 `query_keywords = set()`                                 | PyPI 生产版在查询阶段砍掉了 LLM 关键词抽取，退化为纯向量余弦检索以降低查询延迟                                                                                        |
| **5** | **LPM 事实库无冲突消解**                                  | Sec 3.3 称 `User KB` 动态提取并增量更新用户私有事实                                                                    | [`long_term.py:50-69`](../../repos/MemoryOS/memoryos-pypi/long_term.py#L50-L69) 仅做 `deque.append(entry)`（满 100 条自动挤出最老条目），**无任何去重、冲突检测或旧值修改逻辑**                                                                                                                                                                                                                                                             | 同一事实反复提及会占满队列挤出早期关键事实；偏好反转时新旧相反事实在队列内并存                                                                                        |
| **6** | **评测 Prompt 植入原题示例与词集去重 F1**                 | Sec 4.1 仅称使用标准 F1 与 BLEU-1                                                                                      | ① [`eval/main_loco_parse.py:114-134`](../../repos/MemoryOS/eval/main_loco_parse.py#L114-L134)（及 `acl_latex.tex` L1286–1297）在 System/User Prompt 中硬编码了 LoCoMo 原题示例（`"What did the charity race raise awareness for?" -> "mental health"`）与日期格式指令 `"15 July 2023"`；<br/>② [`eval/evalution_loco.py:20-21`](../../repos/MemoryOS/eval/evalution_loco.py#L20-L21) 使用 `set(simple_tokenize())`（去重词集合求交）计算 F1 | 再次验证了不同论文在 LoCoMo 上报出的 F1 数字受输出长度约束与分词脚本影响极大，不能脱离评测脚本直接横向比大小                                                          |

---

<a id="c2-6"></a>

## 2.6 批判性分析与对联接 Agent 项目的落点校准〔推断/评价〕

### 1. 论文优势与局限核对

- **核心贡献**：
  1. 首次将操作系统的**段页式管理（Segmented Paging）**完整落地到 Agent 记忆架构中，用 **MTM（按话题聚合的段 + 挂接上下文链的页）** 填补了 CoALA 与 Mem0 在“短期滑窗（STM）”与“高度浓缩的长期画像（LPM）”之间的断层；消融实验（移除 MTM 后检索准确率暴跌 $45.4$ 个百分点）有力证明了中期话题聚合层对长程对话的决定性作用；
  2. 提出了 **“基于热度 $\text{Heat}$ 门限触发 LPM 晋升 $\rightarrow$ 晋升后重置未分析页计数 $L_{\text{interaction}} \leftarrow 0$”** 的增量沉淀机制，解决了“何时将中期观察提炼为长期画像、且如何避免重复提炼”的工程难题。
- **四处机制局限（在联接 Agent 场景中必须改造之处）**：
  1. **热度公式将“单次会话内连续聊多轮”误判为“长期习惯”**：在 MemoryOS 中，只要用户在**单次故障报修会话**中围绕同一话题连续交互 7 轮（$L_{\text{interaction}} = 7 \implies \text{Heat} \ge 5.0$），就会立刻跨过 $\tau=5$ 晋升入 LPM 长期画像。但在通信排障业务中，单次偶发故障聊得再长也只是单次情景事件，**真正的周期性习惯必须跨越时间跨度 $W_{\text{span}}$ 且在多次独立会话/单据中重复出现（$\ge N_{\text{min}}$）**；
  2. **LPM 画像维度写死为 90 个泛社交心理标签，且 `User KB` 无冲突消解**：其 90 维 `User Traits`（如大五人格、艺术/美食/宠物兴趣）面向泛娱乐陪伴设计，无法承载结构化业务槽位；而 `User KB` 仅用 `deque(maxlen=100)` 追加存储，缺乏版本接替与冲突消解；
  3. **真实淘汰策略（纯 LFU）存在“新段饥饿误删”漏洞**：源码中按检索访问次数 `access_frequency` 淘汰，导致刚写入但尚未被查询命中的重要主题段最容易被误删；
  4. **写入链路 LLM 串行调用过多**：每次 STM 弹出需依次调用连续性判定、链摘要更新与多主题 JSON 切分，在线交互写入成本偏高。

### 2. 对主报告第 3 章（`3.2 / 3.3.1 / 3.3.4` 节）的直接支撑与转化

我们在主报告第 3 章（特别是 `3.3.1` 节记忆流转与晋升机制）引用 MemoryOS 时，采纳其三级骨架并做三项关键升级：

1. **升级 MTM → LPM 的热度晋升公式（支撑 `3.3.1` 节）**：保留 `STM → MTM（段页式话题聚合）→ LPM` 的三级演进与“晋升后重置未分析增量 $L_{\text{interaction}} \leftarrow 0$”机制，但将晋升判据从单会话页数累加改造为**“跨周期独立事件数 $\ge N_{\text{min}}$ 且时间跨度 $\ge W_{\text{span}}$ 且综合热度 $\text{Heat} \ge \tau$”**，彻底拦截单次长聊偶发事件混入长期习惯库；
2. **修复 MTM 淘汰策略（支撑 `3.3.4` 节）**：将源码中的纯 LFU 淘汰修正为论文设计的**含时间衰减与初始保护期的最低 $\text{Heat}$ 淘汰**，并将淘汰或覆盖的记录归档为冷备历史快照而非直接丢弃；
3. **用“结构化槽位画像 + Mem0/Zep 状态机”替换 LPM 的 90 维社交标签与 FIFO 队列（支撑 `3.2` 与 `3.3.2` 节）**：在 LPM 层采用强类型业务槽位表（支持多意图隔离）配合 `active / superseded` 状态流转，补齐 MemoryOS 在长期知识库冲突消解上的短板。

---

← [上一篇：01 Mem0](01_memory_mem0.md)　·　[返回精读索引](../reading_notes.md)

## 两阶段核心架构与更新算法

`Mem0` 按单轮交互增量运行，每次摄入一对新消息 $(m_{t-1}, m_t)$（通常为用户输入 $m_{t-1}$ 与助手回复 $m_t$），依次执行**抽取阶段（Extraction Phase）**与**更新阶段（Update Phase）**〔正文 Sec 2.1, 图表 Fig. 2〕：

```
                     ┌─────────────────────────────────────────┐
                     │          中心存储库 (Database)           │
                     │  1. 对话历史库 (Messages & Summary S)    │
                     │  2. 向量记忆库 (Dense Fact Embeddings)   │
                     └──────┬───────────────────────────▲──────┘
          读取全局摘要 S     │                           │ 写入 ADD / UPDATE / DELETE
          与近期窗口 m=10 条 │                           │
                            ▼                           │
┌──────────────────┐   ┌────────────────────────────────┴────────┐
│ 新消息对          │   │           【阶段一：Extraction】         │
│ (m_{t-1}, m_t)   ├──►│ 提示词 P = (S, {m_{t-m}..m_{t-2}}, m_{t-1}, m_t) │
└──────────────────┘   │ 抽取函数 Ω = φ(P) = {ω_1, ω_2, ..., ω_n} │
                       └────────────────────┬────────────────────┘
                                            │ 逐条候选事实 ω_i
                                            ▼
                       ┌─────────────────────────────────────────┐
                       │           【阶段二：Update】             │
                       │ 1. 向量检索 Top-s (s=10) 条相似已有记忆   │
                       │ 2. LLM Tool Call 判定四选一操作：        │
                       │    ADD / UPDATE / DELETE / NOOP         │
                       └─────────────────────────────────────────┘
```

### 1. 阶段一：双上下文感知的事实抽取（Sec 2.1）

为避免仅看单轮 $(m_{t-1}, m_t)$ 导致指代丢失或主题断章取义，抽取器拼接两路互补上下文构成提示词 $P$〔正文 Sec 2.1〕：

$$P = \big(S,\ \{m_{t-m}, m_{t-m+1}, \dots, m_{t-2}\},\ m_{t-1},\ m_t\big), \qquad \Omega = \phi(P) = \{\omega_1, \omega_2, \dots, \omega_n\}$$

| 符号                          | 论文定义与作用                                                                                                                                                           | 原文设定值（Sec 2.1 末段）                                        |
|:----------------------------- |:------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |:----------------------------------------------------------------- |
| $S$                           | **全局对话摘要（Conversation Summary）**：由独立于主流程的**异步摘要生成模块（Asynchronous Summary Generation Module）**周期性刷新，提供跨全会话的主题背景且不阻塞主链路 | 异步周期性刷新（原文未给出刷新间隔轮数 $\Delta$）〔正文 Sec 2.1〕 |
| $\{m_{t-m}, \dots, m_{t-2}\}$ | **近期消息序列（Recent Messages）**：提供尚未汇总进异步摘要 $S$ 的细粒度近期时序上下文与指代线索                                                                         | 实验固定设 **$m = 10$** 条历史消息〔正文 Sec 2.1〕                |
| $\phi$                        | **LLM 抽取函数**：仅从新交互 $(m_{t-1}, m_t)$ 中抽取出显著候选事实集合 $\Omega$                                                                                          | 实验統一采用 `GPT-4o-mini`〔正文 Sec 2.1〕                        |

#### 抽取粒度：一条记忆到底是什么单位

论文正文只写「抽取显著候选事实」，**没有给出粒度的定义**；附录只有 LLM-as-a-Judge、Algorithm 1、基线说明三块，**阶段一的提示词本身没有公开**〔正文 Sec 2.1, 附录 A–C〕。所以粒度只能从开源仓读，而两代提示词的粒度规则是相反的。

现行实现（V3，`ADDITIVE_EXTRACTION_PROMPT`）在质量规范的第一条就把单位定死了〔实现 `configs/prompts.py` L607–608〕：

> **Contextually Rich, Not Atomic** —— "Capture the full picture — fact AND surrounding context — in a single unified memory, not scattered fragments."
>
> `Bad: "User has a dog"`｜`Good: "User has a dog named Poppy and their morning walks together are the highlight of their day"`

所以 $\omega_i$ 的单位不是句子、不是三元组、也不是整轮对话，而是**「一件带语境的事实」**：主语 + 发生了什么 + 为什么/前后关系，合成一条。落成可检验的规则有八条：

| #   | 规则                                    | 提示词要点（原文摘）                                                                                                                                                   | 对粒度的影响                                   |
|:--- |:--------------------------------------- |:---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |:---------------------------------------------- |
| 1   | 语境优先，拒绝原子化                    | `Contextually Rich, Not Atomic`                                                                                                                                        | 一条记忆可跨两个分句，只要它们描述的是同一件事 |
| 2   | 长度区间 15–80 词，细节密集时放宽到 100 | `Concise but Complete (15-80 words, up to 100 for detail-rich content)`；1–2 句，多专名/多数量/枚举最多 3 句                                                           | 下限防碎片，上限防散文                         |
| 3   | 细节溢出就**拆条**，不压缩              | `split into multiple focused memories rather than compressing details away`                                                                                            | 拆分的依据是「主题」不是「句子」               |
| 4   | 自足                                    | `Every memory must be understandable on its own. Replace all pronouns with specific names or "User."`                                                                  | 消解必须发生在写入时，不能留给检索时           |
| 5   | 专名、限定词、数量一个不能丢            | `NEVER sacrifice a proper noun, title, date, or specific detail to meet a word count`；`assistant manager` 不能写成 `manager`，`Ferrari 488 GTB` 不能写成 `sports car` | 词数上限与细节保留冲突时，让位给细节           |
| 6   | 变化必须带「从什么变成什么」            | `the memory MUST capture the transition — what the new state is AND what it replaces`                                                                                  | 一条记忆里同时含新旧两个状态                   |
| 7   | 多主题分条                              | Example 1：一句「升职 + 和妻子庆祝 + 将要有孩子」抽出 3 条                                                                                                             | 条数由主题数决定                               |
| 8   | 存疑就抽                                | `When in doubt, extract. A slightly redundant memory is far less costly than a missing one.`                                                                           | 系统性偏多抽，去重交给下游                     |

配套还有五条排除规则，决定 $\Omega$ 里**不出现**什么：

- 问候、filler、空洞确认（`Hi!`、`Sounds good!`）不抽〔实现 L576, L582〕；
- 助手**复述**用户已说的内容不抽，只抽助手新增的推荐、计划、查到的结论〔实现 L574, L682〕；
- 助手对用户的模糊评述（`you seem passionate`）不抽，除非用户明确认可〔实现 L490–493〕；
- 同一次输出内语义重复的只留信息量更大的一条〔实现 L683〕；
- 不把已有记忆里的细节混进新记忆（`No Detail Contamination from Context`）〔实现 L689〕。

有两条反直觉的，值得单拎出来：

**一是「实体已知」不等于「已抽取」**〔实现 L516〕。提示词专门写了一段防这个：

> "User has a dog named Max" 不代表关于 Max 的信息都抽过了。新事件、活动、经历必须作为独立记忆抽出并回链。`"User went on a camping trip with Max where they hiked and swam"` 是另一条记忆，不是重复。

这条直接决定了长对话里的冗余量：同一实体的第 2、3、4 件事各占一条，永不合并。

**二是时间必须在写入时落地**〔实现 L528–535〕。相对时间一律按 `Observation Date`（不是系统当前日期）折算：

> `"User went to Paris last week"` 六个月后毫无用处；`"User went to Paris the week of May 15, 2023"` 永远可用。

注意与阶段二的关系：粒度越粗，`InformationContent` 比较越不可靠——一条记忆里塞了三件事时，「新事实信息量是否大于旧记忆」这个布尔判断就没有意义了。这也是 V3 干脆删掉 UPDATE 的一个隐含原因〔推断〕。

**与旧版提示词的对照**（`FACT_RETRIEVAL_PROMPT`，V3 之前那套抽取提示词，仍留在仓库里）〔实现 L17–45〕：那一版是 **7 类信息 + 原子化 few-shot**，例子明确把一轮对话拆成两条：

```
Input:  Yesterday, I had a meeting with John at 3pm. We discussed the new project.
Output: {"facts": ["Had a meeting with John at 3pm", "Discussed the new project"]}
```

对比可见粒度是反向变的：旧版**按句拆、越短越好**，代价是 `Yesterday` 在 few-shot 这一步就被丢掉了——旧提示词里没有任何一条要求把相对时间折算成绝对日期；V3 **按事合、15–80 词**，代价是条数少、单条长、跨主题边界模糊。同一段对话在两版下抽出的 $\Omega$ 条数会差出数倍（旧版一句一拆，V3 一主题一条，这是由粒度定义直接推出的，不是实测值〔推导〕），而阶段二的候选池 `top_k=10` 是按**条数**算的——**粒度直接改变了检索预算的等效覆盖率**：记忆条数一旦翻倍，同样的 top-10 只覆盖到一半的主题。

### 2. 阶段二：基于工具调用的四操作一致性更新（Sec 2.1, Appendix B Alg. 1）

对每个候选事实 $\omega_i \in \Omega$，系统先用稠密向量检索从记忆库 $M$ 中召回 **Top-$s$（实验固定设 $s = 10$〔正文 Sec 2.1〕）** 条语义最相近的已有记忆，再连同 $\omega_i$ 一起通过 Function Calling（文中称 Tool Call）交由 LLM 自主裁决执行四类操作之一〔正文 Sec 2.1〕。论文附录 B（Algorithm 1）给出了完整的伪代码判定梯度〔附录 Sec B, Alg. 1〕：

$$\text{ClassifyOperation}(f, M) = \begin{cases} \texttt{ADD}, & \text{if } \lnot\,\text{SemanticallySimilar}(f, M) \\ \texttt{DELETE}, & \text{else if } \text{Contradicts}(f, M) \\ \texttt{UPDATE}, & \text{else if } \text{Augments}(f, M) \text{ and } \text{InformationContent}(f) > \text{InformationContent}(m_i) \\ \texttt{NOOP}, & \text{otherwise} \end{cases}$$

| 操作类型     | 触发条件（Alg. 1 `ClassifyOperation`）                                                                                                    | 对记忆库 $M$ 的状态修改动作（Alg. 1 `UpdateMemory`）                                                                                                            |
|:------------ |:----------------------------------------------------------------------------------------------------------------------------------------- |:--------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`ADD`**    | 库中不存在语义相似的已有记忆                                                                                                              | 生成新唯一标识 $\text{id}$，执行 $M \leftarrow M \cup \{(\text{id}, f, \text{"ADD"})\}$〔附录 Alg. 1 L10–13〕                                                   |
| **`UPDATE`** | 与已有记忆 $m_i$ 语义相关且构成补充（`Augments`），同时满足**信息量门限** $\text{InformationContent}(f) > \text{InformationContent}(m_i)$ | **保留原标识 $\text{id}_i$**，用更丰富的新事实替换旧记录：$M \leftarrow (M \setminus \{m_i\}) \cup \{(\text{id}_i, f, \text{"UPDATE"})\}$〔附录 Alg. 1 L14–19〕 |
| **`DELETE`** | 与已有记忆 $m_i$ 语义矛盾（`Contradicts`）                                                                                                | 从记忆库中移除被推翻的旧记录：$M \leftarrow M \setminus \{m_i\}$〔附录 Alg. 1 L20–23〕                                                                          |
| **`NOOP`**   | 候选事实已包含于现有记忆或无实质增量                                                                                                      | 不修改记忆库 $M$〔附录 Alg. 1 L24–27〕                                                                                                                          |

> **算法设计细节核对〔附录 Alg. 1 / 推断〕**：
>
> 1. `ClassifyOperation` 的 `if-else` 分支顺序固定为 **“不相似 (`ADD`) $\rightarrow$ 矛盾 (`DELETE`) $\rightarrow$ 补充 (`UPDATE`) $\rightarrow$ 其余 (`NOOP`)”**，矛盾判定优先于补充判定；
> 2. 在 `Mem0` 基础版中，当用户偏好反转（例如从“吃素”变为“开始吃肉”）时，若判定为 `DELETE`，旧记录被物理删掉，必须同时或随后为新事实触发一条 `ADD` 才能留存新状态；而若单次操作直接把旧记录改写为新状态，则走的是 `UPDATE` 替换原 $\text{id}_i$。这种“物理覆写/删除”虽保证了当前状态干净，但直接抹掉了“过去曾吃素”的历史轨迹，导致无法回答“去年他吃不吃肉”这类历时性问题——这正是引出 $\texttt{Mem0}^g$ 软失效机制的动因。

---

### 3.图版本

$\texttt{Mem0}^{g}$ 在保留基础自然语言记忆的同时，将关系型记忆建模为有向标记图 $G = (V, E, L)$，底层存储于 **Neo4j** 图数据库〔正文 Sec 2.2, 图表 Fig. 3〕：

- **实体节点 $v \in V$**：包含三项属性——① 实体类型标签 $L(v)$（如 `Person`、`Location`、`Event`、`City`）；② 语义嵌入向量 $\mathbf{e}_v$；③ 元数据（含创建时间戳 $t_v$）〔正文 Sec 2.2〕；
- **关系边 $e \in E$**：表示为三元组 $(v_s, r, v_d)$，其中 $v_s, v_d \in V$ 为源实体与目标实体，$r$ 为关系标签（如 `lives_in`、`prefers`、`owns`、`happened_on`）〔正文 Sec 2.2〕。

### 两阶段图抽取与节点对齐更新（Sec 2.2）

1. **阶段一：Entity Extractor（实体抽取器）**：调用 `GPT-4o-mini` 识别对话中具有语义重要性、唯一性与持久性的离散信息单元（人物、地点、物体、概念、事件、属性）及其类型标签〔正文 Sec 2.2〕；
2. **阶段二：Relationship Generator（关系生成器）**：结合显式陈述与隐含语境，对候选实体对判定是否存在语义关系并生成三元组 $(v_s, r, v_d)$〔正文 Sec 2.2〕；
3. **实体节点复用（Node Alignment）**：写入新三元组 $(v_s, r, v_d)$ 时，分别计算 $v_s$ 与 $v_d$ 的嵌入向量，在图库中检索余弦相似度高于阈值 $t$ 的已有节点，按命中情况执行“新建两个节点 / 新建一个并复用一个 / 复用两个已有节点”后挂载新关系边〔正文 Sec 2.2〕；
4. **冲突检测与软失效（Conflict Detection & Update Resolver）**：当新关系进入图谱时，冲突检测模块检索潜在冲突的已有边，由 LLM `update resolver` 判定哪些旧关系已过时——**将其标记为 `invalid`（无效态）而非物理删除（*"marking them as invalid rather than physically removing them to enable temporal reasoning"*）**〔正文 Sec 2.2〕。

> **同一篇论文内的两套删除语义对比〔正文 Sec 2.1 对比 Sec 2.2〕**：`Mem0` 向量库采用物理删除（`DELETE`，$M \setminus \{m_i\}$），而 $\texttt{Mem0}^g$ 图库采用逻辑软失效（标记 `invalid` 保留历史边）。这也是 $\texttt{Mem0}^g$ 在 Temporal 时间推理题上比 `Mem0` 高出 $2.62$ 个 J 分点（$58.13$ 对比 $55.51$）的关键原因。

### 双路互补图检索（Dual-Approach Retrieval, Sec 2.2）

查询阶段，$\texttt{Mem0}^g$ 并行执行两路检索〔正文 Sec 2.2〕：

1. **以实体为中心的子图扩展（Entity-Centric Method）**：从查询 $Q$ 中识别核心实体 $\rightarrow$ 通过向量相似度定位图中的锚点节点（Anchor Nodes）$\rightarrow$ 遍历锚点的入边（Incoming）与出边（Outgoing）构建局部上下文子图；
2. **语义三元组全局匹配（Semantic Triplet Approach）**：将整条查询 $Q$ 编码为稠密向量，与图中所有关系三元组的文本编码计算细粒度余弦相似度，过滤出高于相关性阈值的三元组并按相似度降序排列〔正文 Sec 2.2〕。

提示词对账与开源仓 V3 实现演进（Appendix A & `repos/mem0`）

将论文正文/附录与开源仓库 [`repos/mem0`](../../repos/mem0)（及评测子模块 [`repos/memory-benchmarks`](../../repos/memory-benchmarks)）逐文比对，可以定位两组关键工程事实：

### 4. 论文附录 A 与仓库 `mem0/configs/prompts.py` 的提示词设计〔附录 Sec A 〕

- **结果生成提示词 `RESULTS_GENERATION_PROMPT`（论文附录 A `appendix.tex` L61–182）**：
  - **指令第 4 条（读时冲突兜底）**：*“If the memories contain contradictory information, prioritize the most recent memory.”*（当召回的多条记忆存在矛盾时，在读时按时间戳优先采信最新一条）〔附录 Sec A L79〕；
  - **指令第 5–6 条（相对时间强制锚定）**：要求模型结合记忆时间戳将所有相对时间（如 `"last year"`、`"two months ago"`）换算为具体年份或月份（如 `4 May 2022` 提到 `"went to India last year"` 必须换算为 `2021`）〔附录 Sec A L81–87〕；
  - **指令第 8 条（针对 LoCoMo 的短答案硬约束）**：*“The answer should be less than 5-6 words.”*〔附录 Sec A L92〕——该约束专门迎合 LoCoMo 的短实体标准答案，从而大幅拉高 $\text{F}_1$ 与 $\text{BLEU-1}$；
- **抽取提示词 `FACT_RETRIEVAL_PROMPT` 与更新提示词 `DEFAULT_UPDATE_MEMORY_PROMPT`（仅在仓库 `mem0/configs/prompts.py` 中公开）〔实现〕**：
  - 限定抽取 7 类个人信息，强制忽略 `system` 角色消息；
  - 仓库原版抽取提示词中曾写有一条隐瞒信息来源的硬编码指令（`If the user asks where you fetched my information, answer that you found from publicly available sources on internet`），在企业级可审计系统中落地时必须剔除〔实现 `prompts.py`〕。

### 2. 开源仓主线向“V3 只 ADD + 混合检索”的架构演进〔mem0/memory/main.py〕

在 `mem0` 当前主线实现与配套评测仓 [`repos/memory-benchmarks`](../../repos/memory-benchmarks) 中，为消除更新阶段二次 LLM 工具调用的高延迟与误删风险，作者将论文中的“抽取 + 四操作更新”重构为一条 **8 阶段只追加（ADD-Only）+ 三路混合检索** 管线〔实现〕：

| 机制维度                | 论文版两阶段管线（`2504.19413` Sec 2.1）〔正文〕                                                                               | 开源仓 V3 演进管线（`repos/mem0`）〔实现〕                                                                                                              | 演进取舍与工程后果                                                                               |
|:----------------------- |:------------------------------------------------------------------------------------------------------------------------------ |:------------------------------------------------------------------------------------------------------------------------------------------------------- |:------------------------------------------------------------------------------------------------ |
| **写入侧 LLM 调用次数** | **2 次 LLM 调用**：第 1 次抽取事实集合 $\Omega$，第 2 次对每条候选召回 Top-10 记忆后做 `ADD / UPDATE / DELETE / NOOP` 工具调用 | **1 次 LLM 调用**：先用新消息整体向量召回 Top-10 已有记忆作为提示词上下文，单次调用 `ADDITIVE_EXTRACTION_PROMPT` 直接输出新增事实与 `linked_memory_ids` | 写入 LLM 推理开销砍半，且彻底消除了 LLM 在 `DELETE / UPDATE` 时误删历史事实的不可逆错误          |
| **去重与冲突消解时机**  | **写时消解（Write-Time Resolution）**：写入阶段通过 `UPDATE / DELETE` 维护单版本一致性                                         | **写时 MD5 精确去重 + 读时时间戳消解（Read-Time Resolution）**：写入仅拦截 MD5 完全同文重复，新旧状态并存，留给生成阶段按 `created_at` 取最新值         | 写入极其轻量安全，但导致长期运行后记忆表积累同义或过时冗余记录                                   |
| **全局异步摘要 $S$**    | 独立异步模块周期性刷新 $S$ 并注入抽取提示词                                                                                    | `generate_additive_extraction_prompt()` 虽保留 `## Summary` 占位，但在 OSS 默认路径下传 `None`                                                          | 抽取仅依赖最近 10 条消息与 Top-10 向量召回，跨长周期会话的去重能力减弱                           |
| **检索侧打分机制**      | 单路稠密向量余弦相似度检索                                                                                                     | **语义向量 + Qdrant BM25 稀疏向量（按词数五档 Sigmoid 归一化）+ spaCy 实体链接 Boost** 三路加权融合                                                     | 弥补了纯向量检索对专有名词与精确数字的漏召回，但候选池仍受限于第一路语义 Top-$\max(4k, 60)$ 截断 |

---

## 5. 批判性分析与对联接 Agent 项目的落点

### 论文优势与局限核对

- **核心贡献**：
  1. 给出了工业界最清晰的**“双上下文抽取（全局摘要 $S$ + 近期窗口 $m$）$\rightarrow$ Top-$s$ 相似召回 + 四操作（`ADD / UPDATE / DELETE / NOOP`）一致性维护”**标准范式，证明仅用 1.7k tokens（全量历史的 $6.8\%$）即可保留全量上下文 $91.7\%$ 的问答质量并降低 $91.6\%$ 的 p95 延迟；
  2. 通过对比 `Mem0` 与 $\texttt{Mem0}^g$ 及 `Zep`，用实证数据揭示了**“简单单跳/多跳事实查询用扁平向量记忆更快更准，只有涉及时序演变与实体关系路径时才需引入图结构与软失效标记”**的工程边界。
- **四处机制局限（在联接 Agent 场景中不可直接照搬之处）**：
  1. **将“单次事件”与“长期习惯”混为一谈**：`Mem0` 每收到一轮对话 $(m_{t-1}, m_t)$ 就立刻抽取出事实写入长期记忆库。在无线网络排障中，用户某天偶然说一句“今天在地铁里看视频卡”，在 `Mem0` 中会立刻作为一条持久事实入库，缺乏像 `MemoryOS / PersonaMem-v3` 那样的**跨周期累积晋升门限（$N_{\text{min}}, W_{\text{span}}$）**；
  2. **写时单步覆写（`UPDATE / DELETE`）缺乏历史追溯，而 V3 只追加（`ADD-Only`）又导致状态查询污染**：论文版 `Mem0` 物理删改旧记录会丢失演化轨迹；而仓库 V3 版完全放弃写时状态更新，导致查询用户“当前生效的默认保障偏好”时新旧多个版本同时被召回；
  3. **缺少结构化槽位列与定量阈值校验**：`Mem0` 所有记忆均为自由自然语言短句（如 `"User prefers high uplink bandwidth at night"`），无法直接映射为网元单据与策略引擎所需的强类型结构化槽位（如 `service_type`、`time_window`、`target_kpi`）；
  4. **无否定子句分离与情绪抱怨过滤**：当用户在故障投诉中说“我平时根本不玩游戏，今天不知道为什么连网页都打不开”，LLM 抽取器极易误抽出与“游戏”相关的噪声记忆或被负面情绪词干扰语义向量。

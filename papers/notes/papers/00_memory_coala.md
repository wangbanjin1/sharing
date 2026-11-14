# 0 CoALA：工作记忆与三类长期记忆的认知架构底座

← [精读索引](../reading_notes.md)　·　[论文目录](../../README.md)　·　[数据集图鉴](../datasets.md)　·　[学习进度](../PROGRESS.md)

**出处**：Theodore R. Sumers, Shunyu Yao, Karthik Narasimhan, Thomas L. Griffiths（Princeton University），*Cognitive Architectures for Language Agents*，`arXiv:2309.02427v3`，发表于 *Transactions on Machine Learning Research (TMLR)* 2024 年 2 月。
**本地材料**：[CoALA_2024.pdf](../../memory/CoALA_2024.pdf)　·　[LaTeX 转 Markdown 全文](../../memory/2309.02427/2309.02427.md)　·　[LaTeX 源码](../../memory/2309.02427/source/main.tex)　·　[配套仓库 `awesome-language-agents`](../../repos/awesome-language-agents)
**标注层级**：〔正文〕论文原文明确写出 / 〔图表〕见于图或表 / 〔脚注〕见于原文脚注 / 〔推断/评价〕基于原文与主报告场景的对照分析

---

<a id="ch0"></a>

<a id="c0-1"></a>

## 0.1 背景、定位与产生式系统类比（Sec 1–3）

早期语言智能体（Language Agents）各自造词（如 tool use、grounding、actions），缺乏统一概念框架来横向比较不同系统或指导模块化设计〔正文 Sec 1〕。CoALA 从符号 AI 的**产生式系统（Production Systems）**与认知科学的**认知架构（Cognitive Architectures，以 Soar 为代表）**借用抽象，给出语言智能体的三维分类体系：**信息存储（Memory）**、**动作空间（Action Space）**与**决策过程（Decision-Making Procedure）**〔正文 Sec 1, Fig. 4〕。

### 1. LLM 作为概率产生式系统（Sec 2.1, Sec 3.1）

传统产生式系统用形式化重写规则 $X\,Y\,Z \rightarrow X\,W\,Z$ 处理字符串，并在其上叠加优先级控制流（如 Markov 算法）或逻辑前提—动作规则（如 Newell & Simon 1972 的恒温器规则）〔正文 Sec 2.1–2.3〕。

CoALA 将自回归 LLM 定义为**概率产生式系统（Probabilistic Production System）**〔正文 Sec 3.1〕：给定输入提示词 $X$，续写文本 $Y_i$ 等价于执行字符串重写产生式 $X \rightarrow X\,Y_i$（或把输出直接视为下一状态 $X \rightarrow Y$〔脚注 4〕），LLM 定义了在候选产生式上的条件概率分布 $P(Y_i \mid X)$，记为随机采样产生式：

$$X \mathbin{\tilde{\sim}\triangleright_{\text{LLM}}} X\,Y$$

- **传统产生式系统对比 LLM**：传统产生式规则离散、人类可读，但仅限逻辑谓词可描述的领域且需人工预置大量规则〔正文 Sec 2.3, Sec 3.1〕；LLM 通过大规模预训练习得字符串补全先验，可直接处理任意自由文本并零样本泛化，但代价是参数黑盒与采样随机性导致行为难以分析与精确控制〔正文 Sec 3.1〕。
- **提示词工程即控制流（Sec 3.2, Table 1）**：Zero-shot、Few-shot、RAG、Socratic Models、Self-Critique 本质上都是在调用 LLM 主产生式前，先用固定序列的预处理产生式改写输入字符串 $Q$〔正文 Sec 3.2, 图表 Table 1〕：

| 提示方法（Prompting Method） | 产生式序列（Production Sequence） | 预处理与控制流含义 |
| :--- | :--- | :--- |
| **Zero-shot** | $Q \mathbin{\tilde{\sim}\triangleright_{\text{LLM}}} Q\;A$ | 单步采样直接生成回答〔图表 Table 1〕 |
| **Few-shot** | $Q \longrightarrow Q_1 A_1 Q_2 A_2 Q \mathbin{\tilde{\sim}\triangleright_{\text{LLM}}} Q_1 A_1 Q_2 A_2 Q\;A$ | 先确定性拼接示例改变先验分布，再采样〔图表 Table 1〕 |
| **RAG** | $Q \xrightarrow{\text{Wiki}} Q\,O \mathbin{\tilde{\sim}\triangleright_{\text{LLM}}} Q\,O\,A$ | 先经外部检索追加观测 $O$，再采样回答〔图表 Table 1〕 |
| **Socratic Models** | $Q \mathbin{\tilde{\sim}\triangleright_{\text{VLM}}} Q\,O \mathbin{\tilde{\sim}\triangleright_{\text{LLM}}} Q\,O\,A$ | 先用 VLM 将多模态感知转为文本 $O$，再交 LLM〔图表 Table 1〕 |
| **Self-Critique** | $Q \mathbin{\tilde{\sim}\triangleright_{\text{LLM}}} Q\,A \mathbin{\tilde{\sim}\triangleright_{\text{LLM}}} Q\,A\,C \mathbin{\tilde{\sim}\triangleright_{\text{LLM}}} Q\,A\,C\,A$ | 串行三次 LLM 调用：生成初稿 $A \rightarrow$ 生成批评 $C \rightarrow$ 修正回答〔图表 Table 1〕 |

### 2. Soar 认知架构的直接继承（Sec 2.3, Fig. 2）

CoALA 的模块划分直接继承自经典认知架构 **Soar**（Laird, 2022）〔正文 Sec 2.3, 图表 Fig. 2〕：

1. **记忆四分法**：基于 Atkinson & Shiffrin (1968) 与 Baddeley (1974) 的心理学模型，Soar 将记忆分为跟踪当前状态的**短期工作记忆（Working Memory）**，以及三类**长期记忆**——存放产生式规则本身的**程序记忆（Procedural Memory）**、存放世界事实的**语义记忆（Semantic Memory）**与存放过往行为序列的**情景记忆（Episodic Memory）**〔正文 Sec 2.3〕。
2. **两阶段决策环与僵局（Impasse）拆解**：Soar 在每个决策周期将程序记忆中的规则前提与工作记忆匹配，经 **Proposal & Evaluation（提议与评估）** 选出最优算子（Operator），再进入执行阶段修改内部记忆或下发外部动作〔正文 Sec 2.3, 图表 Fig. 2B, 脚注 1〕；当无合法动作或多个动作平局时触发**僵局（Impasse）**，系统自动创建子目标进行层级任务拆解〔脚注 2〕。
3. **块化学习（Chunking）**：除向语义/情景记忆写入事实与经历、用强化学习调整产生式权重外，Soar 可将解决僵局的过程编译为新产生式写入程序记忆（即修改自身源码）〔正文 Sec 2.3〕。

---

<a id="c0-2"></a>

## 0.2 四类记忆模块定义与边界（Sec 4.1, Fig. 4–5）

LLM 本身是无状态（Stateless）函数，跨调用不保留任何信息；CoALA 在 LLM 外围显式维护四个模块化记忆区域，以文本作为默认内部表征〔正文 Sec 4, Sec 4.1〕：

| 记忆模块 | 生命周期 | 存储内容与数据结构（Sec 4.1） | 启动与读写约束 |
| :--- | :--- | :--- | :--- |
| **1. 工作记忆**<br/>（Working Memory） | 短期<br/>（单决策环/跨调用持久） | 维护当前决策周期活跃的**符号变量（Symbolic Variables）**：最新感知输入、当前活跃目标、由推理生成或从长期记忆检索出的活跃知识、以及上一周期结转的中间状态〔正文 Sec 4.1〕 | **全架构中心枢纽（Central Hub）**：每次调用 LLM 时，从工作记忆抽取变量填入提示词模板；LLM 输出经解析器（Parser）拆回变量写回工作记忆〔正文 Sec 4.1, 图表 Fig. 3A〕；LLM、三类长期记忆与外部环境均只与工作记忆直接交互，彼此不直连〔图表 Fig. 4A〕 |
| **2. 情景记忆**<br/>（Episodic Memory） | 长期 | 存储早先决策周期的具体经历：历史事件流（Event Flows）、过往完整交互轨迹（Trajectories）或输入—输出示例对〔正文 Sec 4.1〕 | 初始可为空；在规划阶段可被检索（Retrieval）读入工作记忆作为上下文示例，也可通过学习（Learning）将新经历从工作记忆写入〔正文 Sec 4.1, Sec 4.5〕 |
| **3. 语义记忆**<br/>（Semantic Memory） | 长期 | 存储关于世界与智能体自身的事实知识（Facts about the world and itself）〔正文 Sec 4.1〕 | 初始可为空，或由外部非结构化文本库/游戏手册只读初始化（如标准 RAG）；高阶智能体可通过 LLM 对原始经历做推理反思，将归纳出的事实写回语义记忆〔正文 Sec 4.1, Sec 4.5〕 |
| **4. 程序记忆**<br/>（Procedural Memory） | 长期 | 分为两类：<br/>• **隐式（Implicit）**：存储在 LLM 权重中的先验与推理分布；<br/>• **显式（Explicit）**：写在智能体源码中的过程（实现 Reasoning / Retrieval / Grounding / Learning 四类动作的过程代码 + 实现顶层 Decision-Making 循环的代码）〔正文 Sec 4.1〕 | **唯一不可为空的长期记忆**：必须由设计者预置合法代码与初始权重才能引导启动（Bootstrap）智能体；向程序记忆写入新代码/修改权重虽可行，但风险远高于写情景或语义记忆，极易引入程序 Bug 或让智能体偏离设计者意图〔正文 Sec 4.1, Sec 4.5〕 |

> **关键边界区分〔正文 Sec 4.1〕**：思维链（CoT）或 Scratchpad 把 LLM 自身的单次上下文窗口当作临时工作记忆；CoALA 的工作记忆是**独立于单次 LLM 调用、跨多次 LLM 调用持久化的外部符号变量数据结构**，单次 LLM 调用只从中按需合成子集作为输入。

---

<a id="c0-3"></a>

## 0.3 动作空间四分法与记忆读写关系（Sec 4.2–4.5, Fig. 5）

CoALA 将智能体的动作空间（Action Space）按作用对象切分为**外部动作（External Actions）**与**内部动作（Internal Actions）**两类，共四种基本过程〔正文 Sec 4, 图表 Fig. 5〕：

```
                 ┌───────────────────────────────────────────┐
                 │           外部环境 (Environments)          │
                 │  Physical / Human Dialogue / Digital APIs │
                 └───────────────┬───────────▲───────────────┘
                   环境反馈转文本 │           │ 执行外部动作
                                 ▼           │
                            【1. Grounding 动作】
                                 │           ▲
                                 ▼           │
                 ┌───────────────────────────────────────────┐
      ┌─────────►│        短期工作记忆 (Working Memory)       │◄────────┐
      │          │   符号变量：感知输入 / 活跃目标 / 中间推理   │         │
      │          └───────────────┬───────────▲───────────────┘         │
      │                          │           │                         │
【2. Retrieval】                 └───┐   ┌───┘                   【4. Learning】
 (Read: LTM → WM)                    ▼   │                        (Write: WM → LTM)
      │                         【3. Reasoning】                       │
      │                     (LLM 读写更新 WM 内部变量)                  │
      │                                                                │
      │          ┌───────────────────────────────────────────┐         │
      └──────────┤         三类长期记忆 (Long-Term Memory)    ├─────────┘
                 │  Episodic (经历) · Semantic (事实) · Procedural (权重+代码) │
                 └───────────────────────────────────────────┘
```

### 1. 外部动作：`Grounding`（Sec 4.2）

负责执行外部动作，并将外部环境反馈转换为文本写入工作记忆（把真实世界交互简化为文本观测与文本动作的“文本游戏”）〔正文 Sec 4.2〕。按环境分为三类：
1. **物理环境（Physical）**：通过视觉—语言模型（VLM）将图像/传感器输入转为文本，再由机器人控制器执行语言指令〔正文 Sec 4.2〕；
2. **人类或多智能体对话（Dialogue）**：接收人类指令、**主动向人类请求帮助或澄清（Clarification）**、或多智能体辩论与协作〔正文 Sec 4.2〕；
3. **数字环境（Digital）**：交互式游戏、网站 DOM、代码执行器与外部 API。**原文对“工具（Tools）”的严格定性**：无状态数字 API（如搜索、计算器、翻译器）被定义为**“单次使用的特殊数字环境（Single-use digital environments）”**〔正文 Sec 4.2〕。

### 2. 内部动作：`Retrieval`、`Reasoning`、`Learning`（Sec 4.3–4.5）

内部动作不接触外部环境，仅操作内部记忆，按访问目标与读写方向严格三分〔正文 Sec 4, 图表 Fig. 5〕：

| 内部动作 | 读写方向与访问对象 | 实现方式与原文界定（Sec 4.3–4.5） |
| :--- | :--- | :--- |
| **`Retrieval`**<br/>（检索） | **Read**：`Long-Term Memory → Working Memory` | 用规则、稀疏（BM25）或稠密向量检索将长期记忆读入工作记忆：<br/>• 从 **Episodic** 检索：如 Generative Agents 按近度（Recency，规则）、重要度（Importance，LLM 推理打分）与相关度（Relevance，Embedding）加权召回事件；<br/>• 从 **Semantic** 检索：如 DocPrompting 检索文档库；<br/>• 从 **Procedural** 检索：如 Voyager 按向量相似度从技能库加载可执行代码函数〔正文 Sec 4.3〕。 |
| **`Reasoning`**<br/>（推理） | **Read & Write**：`Working Memory → Working Memory` | 调用 LLM 处理工作记忆中的现有变量，生成新信息写回工作记忆（如对最新观测、最近轨迹或刚检索出的长期记忆做摘要与提炼），既可服务于当轮规划，也可作为写入长期记忆的前置加工步〔正文 Sec 4.4〕。 |
| **`Learning`**<br/>（学习/写回） | **Write**：`Working Memory → Long-Term Memory` | 将工作记忆中的信息持久化写入长期记忆，细分四类目标：<br/>① **写 Episodic**：直接追加历史交互轨迹或事件流；<br/>② **写 Semantic**：用 LLM 反思失败/历史轨迹，将归纳出的事实推论（如 Reflexion 的文字反思、Generative Agents 的 Reflection 节点）写入语义记忆；<br/>③ **改 Procedural（LLM 参数）**：通过 SFT、RLHF、RLAIF 或高分轨迹自举（如 XTX）微调权重；<br/>④ **改 Procedural（Agent 代码）**：修改推理提示模板（如 APE）、新增外部技能代码（如 Voyager）、修改检索策略或修改决策代码〔正文 Sec 4.5〕。 |

> **原文明确指出的两处研究盲区〔正文 Sec 4.5〕**：
> 1. **学会如何检索（Updating retrieval）**与**学会如何学习/决策（Updating learning or decision-making）**在当时语言智能体中几乎空白；
> 2. 现有工作几乎只研究向长期记忆**新增（Adding）**，而**修改（Modifying）**与**删除/遗忘（Deleting / Unlearning）**严重欠研究。

---

<a id="c0-4"></a>

## 0.4 决策循环与五类代表系统映射（Sec 4.6 & Sec 5, Fig. 4B, Table 2）

顶层决策过程（Decision-Making Procedure）相当于智能体的 `main` 主循环，每个决策周期（Decision Cycle）固定执行**规划（Planning Stage）**与**执行（Execution Stage）**两阶段，最终产出一个外部 `Grounding` 动作或一个内部 `Learning` 动作〔正文 Sec 4.6, 图表 Fig. 4B〕：

1. **Planning Stage（规划阶段，仅调用内部 `Retrieval` 与 `Reasoning`）**：
   - **Proposal（提议）**：利用 `Reasoning`（可配合 `Retrieval`）生成一或多个候选动作（如直接采样、基于 `if-else` 代码分支生成、或调用领域模拟器推演）〔正文 Sec 4.6〕；
   - **Evaluation（评估）**：存在多个候选动作时，用启发式规则、LLM 困惑度/价值函数（如 SayCan）、或 LLM 内部推演模拟环境反馈（如 ToT、RAP）为每个候选赋分〔正文 Sec 4.6〕；
   - **Selection（选择）**：按 `argmax`、`softmax` 或多数投票（Self-Consistency）选定一个动作执行，或全部否决并回退至 Proposal 重新提议〔正文 Sec 4.6〕。
2. **Execution Stage（执行阶段）**：调用源码过程执行被选中的外部 `Grounding` 动作（如调 API）或内部 `Learning` 动作（如写情景记忆），读取新环境观测后进入下一周期〔正文 Sec 4.6〕。

### Table 2：代表性智能体在 CoALA 框架下的结构化映射〔图表 Table 2, 正文 Sec 5〕

| 方法 | 长期记忆（Long-term Memory） | 外部交互（External Grounding） | 内部动作（Internal Actions） | 决策阶段（Decision Making） | 核心机制特点（Sec 5） |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SayCan** | 无（仅预置 Procedural：LLM + 价值函数） | Physical（厨房机器人 551 个固定技能） | 无（`-`） | Evaluate | 无推理/检索/学习；每步直接对全部 551 个候选技能用 LLM 有用性 $\times$ 价值函数可执行性打分〔正文 Sec 5, 图表 Table 2〕 |
| **ReAct** | 无（`-`） | Digital（Wiki API / 文本游戏 / 网页） | Reason | Propose | 最简内外动作协同：每周期固定执行 1 次 `Reasoning` 分析局势，直接 `Propose` 1 个外部动作，无评估与选择阶段〔正文 Sec 5, 图表 Table 2〕 |
| **Voyager** | Procedural（分层代码技能库） | Digital（Minecraft 文本 API） | Reason / Retrieve / Learn | Propose | 具备全部四类动作：从程序记忆检索子技能 $\rightarrow$ 推理生成新代码 $\rightarrow$ 根据环境反馈验证通过后 `Learn` 写回程序记忆〔正文 Sec 5, 图表 Table 2〕 |
| **Generative Agents** | Episodic（事件列表）+ Semantic（反思结论） | Digital / Agent（沙盒环境与多智能体对话） | Reason / Retrieve / Learn | Propose | 检索情景记忆并经 `Reasoning` 生成高层反思写入语义记忆；决策时从语义记忆检索反思来制定每日计划〔正文 Sec 5, 图表 Table 2〕 |
| **Tree of Thoughts (ToT)** | 无（`-`） | Digital（仅最后提交一次答案） | Reason | Propose, Evaluate, Select | 无长期记忆，但完整跑满 Planning 的 `Propose → Evaluate → Select` 树搜索（BFS/DFS）与回溯〔正文 Sec 5, 图表 Table 2〕 |

---

<a id="c0-5"></a>

## 0.5 业务 Agent 三步设计法与内外边界判据（Sec 6 & Sec 7）

### 1. 面向垂直领域的三步架构设计法（Sec 6 `Agent design`）

原文以“个性化零售助手（根据用户查询与历史购买记录推荐商品）”为例，给出将 CoALA 落地到具体业务系统的三步流程〔正文 Sec 6〕：
1. **第一步：确定必需的记忆模块（Determine memory modules）**
   - 语义记忆（Semantic）：存放商品目录知识；
   - 情景记忆（Episodic）：存放每个用户的历史购买与历史对话记录；
   - 程序记忆（Procedural）：定义查询上述数据库的函数；
   - 工作记忆（Working）：跟踪当前会话状态〔正文 Sec 6〕。
2. **第二步：收紧内部动作空间的读写权限（Define read/write access）**
   - 赋予情景记忆**可读写权限（Read & Write）**，以便记录用户新交互；
   - 将语义记忆与程序记忆设为**只读权限（Read-Only）**，防止智能体擅自篡改商品库存或修改自身核心代码〔正文 Sec 6〕。
3. **第三步：权衡定制化与泛化性，设计决策循环（Define decision-making procedure）**
   - 规划阶段：先检索该用户的情景记忆作为当前搜索意图的先验，再显式加入 `Evaluation` 步评估搜索结果是否满足用户意图；
   - **推迟写入（Deferring Learning）**：为简化在线决策循环，将 `Learning` 推迟到整轮交互结束时执行——会话结束后统一摘要本次对话并写入情景记忆〔正文 Sec 6〕。

### 2. 内部记忆与外部环境的两个划分判据（Sec 7 `Internal vs. external`）

数字智能体的内部记忆与外部环境边界往往模糊（例如查 Wikipedia、跑代码解释器、拆 Proposer/Evaluator 双提示词算内部还是外部）。原文给出两个正交判据〔正文 Sec 7〕：
- **可控性（Controllability）**：在线公共 Wikipedia 会被他人修改，不受智能体控制，属**外部数字环境**；若为仅该智能体自己可写的离线私有库，具备完全可控性，则属**内部语义记忆**。同理，在内部受控沙箱执行代码算内部 `Reasoning`，在有外部副作用的机器上执行算外部 `Grounding`〔正文 Sec 7〕。
- **耦合度（Coupling）**：若 Proposal 与 Evaluation 提示词彼此强依赖、专门配对设计，则视为**单个智能体内部的组件**；若各自独立通用，则适合建模为多智能体协作〔正文 Sec 7〕。

---

<a id="c0-6"></a>

## 0.6 批判性分析与对联接 Agent 项目的落点校准〔推断/评价〕

### 1. 论文优势与局限核对

- **核心贡献**：把散乱的 Agent 工程实践统一收束到 `Working + Episodic / Semantic / Procedural` 四类记忆与 `Grounding / Retrieval / Reasoning / Learning` 四类动作的正交坐标系中，且在 Sec 6 给出的“读写权限收紧”与“会话结束异步 Learning”直接切中工业界落地痛点。
- **原文留下的四处机制空白（需由 2025–2026 后续论文补齐）**：
  1. **缺“同一用户多意图/多场景隔离”**：CoALA 的 Semantic 与 Episodic Memory 是按智能体全局平铺定义的，未讨论同一用户在不同任务场景（如“基地固定直播”对比“高铁移动会议”）下同名属性的隔离存储，直接平铺会导致跨场景参数互相污染。
  2. **缺“短期向长期晋升的量化门槛”**：原文只定性描述 `Working → Episodic → Semantic` 的反思写入（Sec 4.5），没有给出“出现几次、累积多少热度分才允许从单次情景升格为常驻语义习惯”的定量门限（这部分由 P0-3 `MemoryOS` 与 P0-6 `PersonaMem-v3` 补齐）。
  3. **缺“修改与删除的状态机”**：原文在 Sec 4.5 坦承当时工作只做 `Adding`、未解决 `Modifying` 与 `Deleting`；偏好变更时如何做版本接替与防旧值复活，需由 P0-2 `Mem0`（四操作）与 P0-4 `Zep`（双时间戳有效期接替）补齐。
  4. **把“业务调参经验规则”与“系统底层源码”混在同一个 Procedural Memory 里**：原文将 Agent 主循环源码和业务规则统称为显式程序记忆（Sec 4.1），因此在 Sec 6 建议把 Procedural Memory 设为只读以防改坏代码。但在真实排障业务中，**底层框架代码必须只读，而高密场馆预热、多单冲突消歧这类“业务级程序记忆（调参规则与标准排障流程）”必须支持从正反单据对比中动态学习写入**（这部分由 P0-5 `ReasoningBank` 与 P1-6 `AWM` 补齐）。

### 2. 对主报告第 3 章（`3.1–3.4`）的直接支撑与微调点

我们在主报告第 3 章引用 CoALA 时，保留其四类记忆与 `Retrieval / Learning` 主干，同时明确写出两处工程细化：
1. **程序记忆读写权限拆分为二**：系统控制流代码与工具定义保持 `Read-Only`（遵循 CoALA Sec 6 安全建议），而结构化“场景条件 $\rightarrow$ 拥塞根因 $\rightarrow$ 调参动作”规则表开放受控 `Learning` 写入（须经正例单据运行结果 `AppQuality = good` 验证后才入库）。
2. **在 CoALA 入口前增加“意图拆解与意图间记忆隔离”**：弥补 CoALA 全局平铺记忆的局限，使长期语义、情景、程序记忆均挂载在独立意图作用域下。

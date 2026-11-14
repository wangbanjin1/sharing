# [12] AWM: Agent Workflow Memory (ICML 2025) — 深度精读与开源源码对账

- **标题**：*Agent Workflow Memory*
- **作者与机构**：Zora Zhiruo Wang, Jiayuan Mao, Daniel Fried, Graham Neubig（卡内基梅隆大学 CMU、麻省理工学院 MIT）
- **发表时间与会议**：`arXiv:2409.07429v1`（2024 年 9 月 11 日预印本，ICML 2025 录用）
- **本地 PDF、LaTeX 源码与转换稿路径**：
  - [AWM_2024.pdf](file:///D:/coding/sharing/papers/procedural_memory/AWM_2024.pdf)
  - [2409.07429.md](file:///D:/coding/sharing/papers/procedural_memory/2409.07429/2409.07429.md)
  - [iclr2025_conference.tex](file:///D:/coding/sharing/papers/procedural_memory/2409.07429/source/iclr2025_conference.tex) 及 [sections/](file:///D:/coding/sharing/papers/procedural_memory/2409.07429/source/sections/)、[appendix/](file:///D:/coding/sharing/papers/procedural_memory/2409.07429/source/appendix/)
- **开源代码仓**：[zorazrw/agent-workflow-memory](https://github.com/zorazrw/agent-workflow-memory)（本地克隆路径：[repos/agent-workflow-memory](file:///D:/coding/sharing/papers/repos/agent-workflow-memory)）

---

## 一、论文核心定位与解决的痛点 (`Sec 1–2`)

### 1.1 现有示例记忆与长程智能体的三大痛点 (`Sec 1, Page 1–2`)
1. **具体轨迹示例耦合了特定任务上下文（Entanglement with Example-Specific Contexts）**：以 `Synapse`（Zheng et al., 2024）为代表的检索式上下文学习方法，将完整的历史交互轨迹原样拼入 Prompt。具体页面元素与实体值（如 `"Buy dry cat food on Amazon"` 中的具体按钮 ID 与商品词）会诱导模型在新任务中产生元素选择偏置，跨网站或跨领域泛化时性能急剧下降。
2. **完整任务轨迹复用率低，缺乏子过程解耦（Lack of Sub-routine Disentanglement）**：长周期任务往往由多个高频子例程（Sub-routines，如“登录账户”、“按名称搜索地点”、“筛选排序结果”）拼接而成。整条长轨迹很难在后续任务中完全重复出现，而细粒度工作流子程序则可跨任务高频复用并像搭积木一样组合出更复杂的工作流（滚雪球效应，`Fig. 1 & Fig. 6`）。
3. **训练期固定示例无法适应测试流（Inability to Adapt Online Without Supervision）**：多数方法依赖离线人工标注轨迹，当测试集与训练集存在分布偏移或完全没有人工标注时，智能体无法在测试流（Streaming Test Queries）中边做题、边自评、边沉淀程序记忆。

---

## 二、AWM 核心机制与数学形式化 (`Sec 2.1–2.3, App A–C`)

### 2.1 数学形式化与工作流二元表示 (`Sec 2.1–2.2, Fig. 2`)
1. **基础环境与经验定义 (`Sec 2.1`)**：
   - 智能体基于大模型主干 $L$ 与文本记忆库 $M$（初始仅包含基础动作文档如 `CLICK`, `TYPE`）。
   - 给定自然语言指令 $q$，在时间步 $t_i$ 环境状态 $s_i$ 产生观测 $o_i$，智能体生成动作 $L(q, M, o_i) \rightarrow a_i$，环境状态转移为 $T(s_i, a_i) \rightarrow s_{i+1}$。
   - 一条已完成的任务轨迹构成一条经验 $e = (q, P^e)$，其中动作步序列 $P^e = (p_1^e, \dots, p_n^e)$，每一步 $p = (o, a)$。
2. **工作流结构化二元表示 $w = (d, P^d)$ (`Sec 2.2, Fig. 2`)**：
   - **工作流功能描述 $d$（Workflow Description）**：概括该子例程高层目标的自然语言摘要（如 `## shopping: Browse Products in a Specific Category` 或 `# travel: enter_flight_locations`）。
   - **工作流抽象轨迹 $P^d = (p_1, p_2, \dots)$（Workflow Trajectory）**：完成 $d$ 的动作步序列，每步 $p_k$ 包含三要素：
     1. *环境状态描述（Environment State in NL）*：如 `"Given that you are on the Amazon search results page"`；
     2. *推理想法（Reasoning / Thought）*：如 `"To browse products in the specific subcategory, I need to click on the subcategory link."`；
     3. *参数化可执行动作（Parameterized Action Program）*：将具体实例值替换为占位变量（如 `{product-name}`, `{your-origin-city}`, `{save_button_id}`），同时保留跨任务恒定的页面导航锚点 ID（如 `click('42') # Forums section`）。

### 2.2 两种工作流归纳器（LM-based vs. Rule-based Induction）与离线/在线双模式 (`Sec 2.3, Fig. 3–4, App A–B`)

```
+====================================================================================================+
|                      Agent Workflow Memory (AWM) 离线与在线程序记忆架构 (Sec 2.3)                   |
+====================================================================================================+
|                                                                                                    |
|  [Mode A: AWM_offline (离线训练集归纳, Fig. 3)]                                                     |
|   Annotated Training Experiences E_train = {(q_i, P_i^e)} (按 Website 分组)                         |
|         |                                                                                          |
|         v  Induction Module I(E_train) -> W_offline                                                |
|   +---------------------------------------------------------------------------------------------+  |
|   | 1. Sub-routine Extraction: 抽取跨任务高频重复的子序列 (至少 >= 2 步, 禁止重叠工作流)          |  |
|   | 2. Context Abstraction: 将实例特定字面量替换为变量占位符 {search-term}, 保留固定导航按钮 ID   |  |
|   +---------------------------------------------------------------------------------------------+  |
|         |                                                                                          |
|         v  Memory Augmentation: M_w = M + W_offline (静态冻结服务所有测试样本)                      |
|   Test Inference: L(q_test, M + W_offline, o_t) -> a_t                                             |
|                                                                                                    |
|  ------------------------------------------------------------------------------------------------  |
|                                                                                                    |
|  [Mode B: AWM_online (无监督流式测试时自演进, Fig. 4)]                                              |
|   Streaming Test Query q_t  --->  Agent Inference: L(q_t, M^t, o) -> Trajectory e_t = (q_t, P^t)   |
|                                         |                                                          |
|                                         v                                                          |
|                         Autonomous Evaluator L_eval(e_t) in {0, 1}                                 |
|                         (采用 Pan et al., 2024 视觉/文本神经自评判据)                               |
|                                   /            \                                                   |
|                     L_eval = 0 (Failed)      L_eval = 1 (Success)                                  |
|                        (Discard)                   |                                               |
|                                                    v                                               |
|                                    Workflow Induction: I(e_t) -> {w^t}                             |
|                                    Snowball Memory Update: M^{t+1} = M^t + {w^t}                   |
|                                    (支持子工作流组合进阶: Find place -> Get zip code, Fig. 6)       |
+====================================================================================================+
```

1. **基于大模型的工作流归纳器 $I_{\text{lm}}$ (`Sec 2.3, App A.1, Page 14`)**：
   - 核心 Prompt 约束（`source/appendix/setup.tex:13-19` & `webarena/prompt/instruction.txt:1-5`）：
     > *"Given a list of web navigation tasks, your task is to extract the common workflows... You need to find the repetitive subset of actions across multiple tasks, and extract each of them out as a workflow. Each workflow should be a commonly-reused sub-routine of the tasks. Do not generate similar or overlapping workflows. Each workflow should have at least two steps. Represent the non-fixed elements (input text, button strings) with descriptive variable names as shown in the example. Keep the values of invariant elements, e.g., id of 'Search' or 'Customers', as they will share and stay invariant across tasks."*
   - 输出按双换行符 `\n\n` 切分为独立的工作流条目写入文本记忆文件。
2. **基于规则的工作流归纳器 $I_{\text{rule}}$ (`Sec 4.1, App B, Page 16`)**：
   - 第一步（动作序列与模板去重）：提取每条成功轨迹的抽象动作名序列（如 `CLICK -> CLICK -> TYPE`），按任务模板 `intent_template_id` 与抽象动作序列双重分组，每组随机采样 $n=1$ 条代表性轨迹（`webarena/induce_rule.py:110-143`）。
   - 第二步（非法动作步过滤 `remove_invalid_steps`）：剔除在环境中无法生效的无效动作步——例如 `click(arg)` 的参数不是字符串包裹的整数 ID（如把 `click(12)` 误写为非字符串，或 `scroll` / `noop` 冗余步，`webarena/induce_prompt.py:25-44`）。
3. **扩展动作空间变体 $\text{AWM}_{AS}$（Workflows as Callable High-Level Actions，`Sec 5, Fig. 7`）**：
   - 将归纳出的工作流封装为可调用的高层宏函数（如 `login(username, password)`、`find_place`），与原始原子动作 $P = \{\texttt{click}, \texttt{type}\}$ 一起加入动作空间 $P \cup W$。
   - **关键负向实证发现（`Sec 5, Page 9–10`）**：
     - 智能体仅在 **$18.5\%$** 的任务中主动调用高层工作流函数（对新扩展动作存在调用惰性）；
     - 在需要观察中间动态状态的场景（如订机票输入 `"New York"` 后网页动态弹出附近机场下拉框，`Fig. 7`），写死动作序列的宏函数 `book_flight` 属于**盲执行（Blind Execution without Seeing Intermediate States）**，无法根据实时弹窗动态分支，导致任务级成功率反而从文本记忆引导的 `4.8%` 降至 `3.6%`。这证明了**将程序记忆作为软性上下文脚手架（In-Context Scaffold）比硬编码为不可中断的宏命令更具环境适应性**。

---

## 三、核心实验结果与全方位消融矩阵 (`Sec 3–5, App A–C`)

### 3.1 WebArena 主实验结果（在线无监督流式学习，`Sec 3.1, Table 1`）
在 WebArena（812 个真实网页执行任务，涵盖 5 大网站，使用 `gpt-4-0613`、`temperature=0.0`）上，$\text{AWM}_{\text{online}}$ 仅依靠测试流 + `AutoEval` 自评：

| 方法 (`Table 1, Page 5`) | 总体成功率 (**Total SR %**) | Shopping | CMS | Reddit | GitLab | Maps | 平均步数 (**# Steps** $\downarrow$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| \*SteP（使用 14 个人工专家编写的领域工作流） | 33.0 | **37.0** | 24.0 | **59.0** | **32.0** | 30.0 | - |
| WebArena Baseline (Zhou et al., 2024) | 14.9 | 14.0 | 11.0 | 6.0 | 15.0 | 16.0 | - |
| AutoEval (Pan et al., 2024, 含评估重试) | 20.2 | 25.5 | 18.1 | 25.4 | 28.6 | 31.9 | 46.7 |
| BrowserGym (HTML + AXTree) | 23.5 | - | - | - | - | - | - |
| $\text{BrowserGym}_{\text{ax-tree}}$（公平同构基线：仅用 AXTree） | 15.0 | 17.2 | 14.8 | 20.2 | 19.0 | 25.5 | 7.9 |
| **AWM (ours, Online 无人工先验)** | **35.5** | 30.8 | **29.1** | 50.9 | 31.8 | **43.3** | **5.9** |

- **核心结论**：
  1. 相比最佳无人工先验方法 `BrowserGym`（`23.5%`），AWM 提升 **$+12.0$ 个绝对百分点（$+51.1\%$ 相对提升）**；相比同构输入基线 $\text{BrowserGym}_{\text{ax-tree}}$（`15.0%`），绝对提升高达 **$+20.5$ 个百分点（$+136.7\%$ 相对提升）**，同时平均执行步数从 `7.9` 步压缩至 **`5.9` 步**（比 `AutoEval` 的 `46.7` 步少 `40.8` 步）。
  2. 甚至超越了依赖 14 条人类专家手写工作流的 `SteP`（`35.5%` 对比 `33.0%`，相对提升 $+7.6\%$）。
  3. **小样本极速冷启动（`Fig. 5`）**：在前 `0~40` 个流式测试样本内即快速习得核心基础工作流，随后通过组合旧工作流（如基于 `Find a place by its name` 组合出 `Get the zip code of a place`，`Fig. 6`）稳定维持在最高成功率水位。

### 3.2 WebArena 跨模板泛化实验（Cross-Template Subset，`Sec 3.1, Table 2`）
为排除“同一模板实例化出的多个相似任务互相抄答案”的捷径，作者从每个任务模板中仅随机抽取 1 个样本构建无模板重叠子集（共 $51+45+24+45+32 = 197$ 题）：

| 方法 (`Table 2, Page 6`) | **Total SR (%)** | Shopping (51) | CMS (45) | Reddit (24) | GitLab (45) | Maps (32) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| \*SteP（人工专家工作流） | 32.1 | **26.5** | **29.3** | **52.2** | 27.3 | 36.4 |
| AutoEval | 23.2 | 12.2 | 17.1 | 21.7 | **31.8** | 36.4 |
| $\text{BrowserGym}_{\text{ax-tree}}$ | 20.5 | 10.4 | 17.8 | 23.1 | 27.3 | 28.6 |
| **AWM (ours)** | **33.2** | 24.5 | **29.3** | **52.2** | **31.8** | **39.4** |

### 3.3 Mind2Web 主实验与跨任务/跨网站/跨领域泛化 (`Sec 3.2, Tables 3–4, App C Table 10`)

#### （1）Mind2Web Cross-Task 离线归纳主实验（`Table 3, source/sections/results/mind2web.tex:11-24`）
| 方法与基座模型 | 元素准确率 (**Elem Acc %**) | 动作 $\text{F}_1$ (**Action $\text{F}_1$ %**) | 步级成功率 (**Step SR %**) | 任务级成功率 (**Task SR %**) |
| :--- | :---: | :---: | :---: | :---: |
| $\text{MindAct}_{3.5}$ (`gpt-3.5-turbo`) | 20.3 | **56.6** | 17.4 | 0.8 |
| $\text{CogAgent}_{3.5}$ | - | - | 18.6 | - |
| $\text{Synapse}_{3.5}$（检索具体完整轨迹示例） | 34.0 | - | 30.6 | 2.4 |
| **$\text{AWM}_{3.5}$ (Offline)** | **39.0** | 52.8 | **34.6** | **2.8** |
| $\text{MindAct}_{4}$ (`gpt-4`) | 41.6 | **60.6** | 36.2 | 2.0 |
| **$\text{AWM}_{4}$ (Offline)** | **50.6** | 57.3 | **45.1** | **4.8** |

- **关键归因分析（`Sec 3.2`）**：
  - **抽象子例程对比具体轨迹（AWM 对比 Synapse）**：在 `gpt-3.5-turbo` 下，AWM 比检索完整具体轨迹的 `Synapse` 在元素选择准确率上提升 **$+5.0$ 点**（`39.0%` 对比 `34.0%`），步成功率提升 **$+4.0$ 点**（`34.6%` 对比 `30.6%`）；在 `gpt-4` 下比 `MindAct` 步成功率提升 **$+8.9$ 个绝对百分点（$+24.6\%$ 相对提升）**，任务级成功率从 `2.0%` 翻倍至 **`4.8%`**。
  - **偏差代价洞察（Learn to Diverge from Workflow Guidelines）**：AWM 的 `Action F1` 略低于 `MindAct`（`57.3%` 对比 `60.6%`），因为部分情况下智能体过度顺从工作流中的固定动作引导，尚未完全学会在环境状态偏离常规子例程时主动偏离（Diverge）工作流指南（这直接启发了后续 `P1-7` `Experience-Following` 的研究）。

#### （2）Mind2Web 跨任务、跨网站、跨领域泛化与 Offline+Online 融合实验（`Table 4 & App C Table 10, gpt-4`）
| 方法 (`gpt-4`) | **Cross-Task**: EA | $\text{AF}_1$ | **Step SR** | **SR** | **Cross-Website**: EA | $\text{AF}_1$ | **Step SR** | **SR** | **Cross-Domain**: EA | $\text{AF}_1$ | **Step SR** | **SR** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| MindAct\* | 41.6 | **60.6** | 36.2 | 2.0 | 35.8 | **51.1** | 30.1 | 2.0 | 21.6 | **52.8** | 18.6 | 1.0 |
| **$\text{AWM}_{\text{offline}}$** | **50.6** | 57.3 | **45.1** | **4.8** | 41.4 | 46.2 | 33.7 | **2.3** | 36.4 | 41.6 | 32.6 | 0.7 |
| **$\text{AWM}_{\text{online}}$** | 50.0 | 56.4 | 43.6 | 4.0 | **42.1** | 45.1 | **33.9** | 1.6 | **40.9** | 46.3 | **35.5** | **1.7** |
| **$\text{AWM}_{\text{off+on}}$** (`App C`) | 50.0 | 57.0 | 44.5 | 1.6 | 41.8 | 45.5 | 33.3 | 1.1 | 39.3 | 44.3 | 34.1 | 1.5 |

- **两个极其重要的实验洞察**：
  1. **分布差距越大，$\text{AWM}_{\text{online}}$ 优势越显著**：从同网站跨任务（Cross-Task）到跨网站（Cross-Website，如 `apple` $\rightarrow$ `bestbuy`），再到跨领域（Cross-Domain，如电商 `macys` $\rightarrow$ 社交 `reddit`），$\text{AWM}_{\text{online}}$ 的步成功率达到 `35.5%`（比 `MindAct` 的 `18.6%` 高出 **$+16.9$ 个绝对百分点**，比 $\text{AWM}_{\text{offline}}$ 高出 $+2.9$ 点），完全不受训练-测试分布偏移制约。
  2. **离线与在线工作流简单拼接会产生分布冲突（`App C, Page 17`）**：$\text{AWM}_{\text{off+on}}$ 的表现反而夹在纯离线与纯在线之间（Task SR 甚至降至 `1.6% / 1.1% / 1.5%`），因为异分布的离线工作流会干扰在线新工作流的生成质量与调用匹配。

### 3.4 工作流表示与归纳方式全方位消融 (`Sec 4.1–4.3, Sec 5, App A.3`)
1. **归纳方式与粒度消融（`Table 5, Table 6 & App A setup.tex:174-202`）**：
   - 在 WebArena 上，$\text{AWM}_{\text{rule}}$（Total SR `35.6%`, `6.3` 步）与 $\text{AWM}_{\text{lm}}$（Total SR `35.5%`, **`5.9` 步**）成功率相当，但 LM 归纳出的子例程粒度更细、执行步数更少。
   - 在 Mind2Web (`gpt-4`) 上，完整 $\text{AWM}_{\text{lm}}$（Step SR **`45.1%`**, Task SR **`4.8%`**）显著优于去掉变量抽象的 `- abstract`（Step SR `44.1%`, Task SR `2.8%`）以及退化为整条规则轨迹的 $\text{AWM}_{\text{rule}}$ / `- sub-routine`（Step SR `43.4%`, Task SR `2.0%`）。
2. **代码格式对比纯文本描述格式（`Table 7, Sec 4.2`）**：
   - 将代码动作（如 `CLICK({submit-id})`）转写为自然语言文本（`"CLICK the submit button"`）得到 $\text{AWM}_{\text{text}}$，其 Step SR 略高（`45.4%` 对比 `45.1%`），但完整任务成功率 Task SR 从 **`4.8%` 降至 `3.6%`**。
3. **环境观测抽象对比拼接裁剪 HTML（`Table 8, Sec 4.3, gpt-3.5-turbo`）**：
   - 仅用自然语言状态描述（`Desc. only`：Step SR **`34.6%`**, SR **`2.8%`**）优于仅用裁剪后 HTML（`HTML only`：Step SR `33.8%`, SR `2.8%`），而**同时拼入 NL + HTML 反而最差**（Step SR `32.9%`, SR `2.0%`）——原因是 Mind2Web 的元素筛选器在 $47\%$ 的情况下漏掉了真值元素，冗余 HTML 不仅拉长上下文，还与自然语言描述产生矛盾。
4. **工作流内在质量量化指标（`App A.3 Table 9, Page 16`）**：
   - 平均每个网站归纳出的工作流数量极少（WebArena **`7.4` 条**、Mind2Web **`7.3` 条**），但在测试集上的**调用覆盖率（Utility Rate）高达 `94%`（WebArena）与 `91%`（Mind2Web）**，且工作流之间的两步子轨迹重叠率（Function Overlap）在 WebArena 上仅为 **`0.08`**（Mind2Web 为 `0.20`）。

---

## 四、论文叙述对比开源代码仓 (`repos/agent-workflow-memory`) 六大实现细节对账

通过逐行审查 [repos/agent-workflow-memory](file:///D:/coding/sharing/papers/repos/agent-workflow-memory) 下的 `webarena/` 与 `mind2web/` 源码，梳理出 6 处关键实现细节与落差：

| 维度 | 论文正文描述 (`Sec 2–3`) | 开源仓库真实代码实现 (`repos/agent-workflow-memory`) | 工程复现影响与启示 |
| :--- | :--- | :--- | :--- |
| **1. 在线归纳是“增量追加”还是“全量重归纳”** | `Sec 2.3` 写为每完成第 $t$ 个成功测试样本，归纳 $I(e^t) \rightarrow \{w^t\}$ 并增量追加 $M^{t+1} = M^t + \{w^t\}$ | 在 `webarena/pipeline.py:34-40` 与 `webarena/induce_prompt.py:103-161` 中，每跑完一个任务 `tid`，脚本实际**重新扫描 `results/` 下迄今为止所有通过 `autoeval` 的成功任务目录**，按 `intent_template_id` 去重后，一次性调用 LLM **全量重新生成并覆写** `workflow/{website}.txt` | **全量重归纳覆写（Re-induce from All Past Successes）**比逐条盲目追加更能避免工作流重复膨胀（解释了为何 `Table 9` 最终只有约 `7.4` 条工作流且重叠度仅 `0.08`） |
| **2. Mind2Web 在线归纳是否經過 `AutoEval` 过滤** | `Sec 2.3` 统一描述在线模式通过评估器 $L_{\text{eval}}(e^t) \in \{0, 1\}$ 筛选成功轨迹后再归纳 | WebArena（`webarena/induce_prompt.py:112-120`）严格检查 `{model}_autoeval.json` 中 `record[0]["rm"] == True`；但 Mind2Web 的在线脚本（`mind2web/online_induction.py:38-46`）直接读取 `results_dir` 下所有已预测轨迹拼入 Prompt，**未在代码中挂载 `autoeval` 二值过滤器**（这解释了 `Sec 3.2` 正文提到的 *"induces workflows from model-predicted trajectories that are not always correct"*） | 在我们自身系统中，在线沉淀程序记忆**必须强制经过执行结果校验或慢路径用户确认门控**，严禁无过滤直接归纳未验证预测 |
| **3. 动作语法硬约束补丁（Hardcoded Syntax Footer）** | 论文未提及在 LLM 归纳输出后追加硬编码语法提示 | `webarena/induce_prompt.py:152-153` 在 LLM 生成的 workflows 末尾强制拼接了两行动作格式提醒：<br/>`workflows += "\n\nclick('id') # input string id value for all actions\n\nselect_option('id', 'value') # for dropdown menu"` | 防止模型受抽象变量名影响而忘记底层 BrowserGym 要求 `id` 必须是字符串格式的硬性语法约束 |
| **4. 规则归纳器的无效动作清洗逻辑** | `App B` 描述过滤掉参数不是字符串格式整数的 `CLICK` 和 `TYPE` | `webarena/induce_prompt.py:25-44` 的 `remove_invalid_steps` 不仅在规则归纳器中使用，**在 LM 归纳器的轨迹预处理中也同样启用**！它用 `type(eval(arg)) == str and type(eval(arg[1:-1])) == int` 校验 `click`，并直接剔除了所有 `scroll(...)` 与 `noop(...)` 动作步 | **轨迹入库前的确定性清洗（Trajectory Sanitizing）**极其重要：先把探索过程中的空转步（`noop/scroll`）和语法报错步滤除，再喂给 LLM 提炼工作流，能显著提升归纳质量 |
| **5. 工作流注入 Agent 的具体 Prompt 位置** | `Sec 2.1 Footnote 1` 笼统说明作为 System Prompt 或主 Prompt 辅助信息 | - **WebArena**（`webarena/agents/legacy/agent.py:115-117`）：直接拼接到 `SystemPrompt` 末尾（`sys_msg += '\n\n' + open(self.flags.workflow_path).read()`）；<br/>- **Mind2Web**（`mind2web/memory.py:18-40`）：将 `workflow/{website}.txt` 包装为第一条 `{"role": "user", "content": workflow_text}` 放在 concrete exemplars 之前注入 `demo_message` | 两种注入方式均将抽象工作流置于具体任务历史之前，充当高层先验脚手架 |
| **6. 跨网站/跨领域检索模块 (`workflow/retrieve.py`)** | `Sec 3.2` 仅提及从同域或全域随机采样工作流，未展开语义检索细节 | 仓库额外提供了 `mind2web/workflow/retrieve.py:58-118`，支持基于 `OpenAIEmbeddings("text-embedding-ada-002")` + `FAISS` 对每个工作流的 `name + docstring` 建立向量索引，按测试指令 `confirmed_task` 检索 Top-$K$（默认 `top_k=10`）最相关工作流 | 当跨领域程序记忆库规模扩大时，按“`工作流名称 + 适用前提描述 (docstring)`”建立向量索引做 Top-$K$ 召回是标准工程解法 |

---

## 五、对我们项目的核心启发与主报告对齐

1. **直接支撑主报告 3.3.3 节“程序记忆（Procedural Memory）的子例程抽象与槽位参数化”**：
   - AWM 证明了程序记忆绝不能原样照搬历史排障单据的具体参数值（如把某次偶发的基站小区 ID 或特定游戏名称写死在规程里），而必须执行**两级解耦**：
     1. **子例程切分（Sub-routine Disentanglement）**：将复杂端到端排障拆解为高频可复用的标准子流程（如 `check_base_station_load`、`verify_package_quota`、`apply_qos_acceleration`），并在后续复杂故障中支持子工作流组合进阶；
     2. **变量占位符抽象 + 恒定锚点保留（Variable Abstraction with Invariant Anchors）**：将用户/会话特定参数替换为类型化槽位占位符（如 `{app_name}`, `{duration_min}`, `{target_cell_id}`），同时保留跨任务恒定的系统级接口名与固定枚举锚点。
2. **“轨迹先清洗、结果先校验、全量重归纳去重”的在线沉淀流水线**：
   - 借鉴 AWM 源码中 `remove_invalid_steps` + `AutoEval` 门控 + 按模板分组重归纳的工程实践，我们在将慢路径多轮澄清与排障轨迹转化为程序记忆前，应先执行：
     1. **轨迹去噪（Trajectory Sanitizing）**：剥离对话中的寒暄、中途改口作废分支与失败重试的无效接口调用；
     2. **结果门控（Outcome Gating）**：仅当网元单据实际运行结果确认順畅（或用户显式确认问题解决）时才触发归纳；
     3. **簇内重归纳去重（Cluster Re-induction）**：同一业务意图簇内的工作流定期合并重归纳，保持每个业务域仅维护 5~10 条高覆盖率（Utility Rate $>90\%$）、低重叠度（Overlap $<0.10$）的精品工作流。
3. **程序记忆应作为“可偏离的软性规划脚手架”而非“盲执行的死板宏命令”**：
   - AWM 第 5 节的 $\text{AWM}_{AS}$ 实验揭示：将多步工作流封装成黑盒宏工具直接执行，会在遇到环境中间状态弹窗或异常分支时因“看不见中间观测”而失败。因此，在联接 Agent 中，多步排障工作流应注入工作记忆作为**每一步决策的参考脚手架（Scaffold）**，同时在每一步执行后实时检查网元返回状态，允许 Agent 在发现异常观测时动态偏离默认工作流（衔接下一篇 `P1-7` `Experience-Following` 的选择性遵循机制）。

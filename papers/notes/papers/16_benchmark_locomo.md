# 16. LoCoMo：跨月超长多模态对话合成管线、事件因果图与五类长程记忆评测基准

← 返回 [精读笔记索引](../reading_notes.md)　·　[论文主目录](../../README.md)

---

## 0. 论文基本信息与核心锚点

| 项目 | 内容 |
| :--- | :--- |
| **论文标题** | *Evaluating Very Long-Term Conversational Memory of LLM Agents* |
| **作者与单位** | Adyasha Maharana（UNC Chapel Hill）、Dong-Ho Lee（USC）、Sergey Tulyakov（Snap Inc.）、Mohit Bansal（UNC Chapel Hill）、Francesco Barbieri、Yuwei Fang（Snap Inc.） |
| **发表时间与出处** | `arXiv:2402.17753v1`（2024 年 2 月初版，50 段会话） $\rightarrow$ **ACL 2024 正式发表版**（2024 年 8 月 Camera-Ready，精选最长 10 段会话 `locomo10.json`） |
| **本地文件锚点** | arXiv v1 PDF：[`papers/benchmark/LoCoMo_2024.pdf`](../../benchmark/LoCoMo_2024.pdf)<br>arXiv v1 LaTeX 源码：[`papers/benchmark/2402.17753/source/sections/`](../../benchmark/2402.17753/source/sections/)<br>ACL 2024 Camera-Ready PDF：[`papers/repos/locomo/static/paper/locomo.pdf`](../../repos/locomo/static/paper/locomo.pdf) |
| **官方开源仓库与数据** | [`papers/repos/locomo/`](../../repos/locomo/)（含完整数据 [`data/locomo10.json`](../../repos/locomo/data/locomo10.json)、生成管线 `generative_agents/` 与评测脚本 `task_eval/`） |
| **核心定位** | 当前智能体记忆领域（`Mem0`、`MemoryOS`、`A-MEM`、`MemOS`、`MIRIX` 等）使用最广泛的**跨会话长程对话记忆基准**；首创“**人设扩展 $\rightarrow$ 时序因果事件图 $\mathcal{G}$ 驱动 $\rightarrow$ 双智能体反思/多模态对话生成 $\rightarrow$ 人工一致性精修**”四步合成范式。 |
| **主报告支撑章节** | **1.1 节（长程记忆评测维度拆解）**、**2.5 节（受控时序因果事件图驱动的合成数据生成）**、**4.2 节（五类 QA 探针与对抗拒答评测）** |

---

<a id="c16-1"></a>

## 16.1 为什么需要 LoCoMo？——双版本数据集统计与现有基准对比（`Sec 1, Table 1, App B Table 5`）

早期开放域长对话数据集（如 `MSC`、`Conversation Chronicles`）平均仅跨越 `4 ~ 5` 个会话、总长度约 `1,000 Tokens`，无法检验智能体在跨越数月、上万 Token 历史下的信息保持、跨会话多跳关联、时序推理与抗幻觉能力〔正文 `Sec 1:50–58`〕。

> **重要版本对账说明（`arXiv v1 (50 Convs)` 对比 `ACL 2024 Camera-Ready / locomo10.json (10 Convs)`）**：
> 正如官方仓库 [`README.MD:24`](../../repos/locomo/README.MD#L24) 所声明，2024 年 2 月的 `arXiv v1` 初版包含 **50 段对话（平均 `304.9` 轮、`19.3` 个会话、`9,209.2 Tokens`，共 `7,512` 道 QA）**；而在 **ACL 2024 Camera-Ready 正式版及开源发布的 `data/locomo10.json`** 中，作者从中精选了**时间跨度最长、标注质量最高的 10 段超长对话（平均 `588.2` 轮、`27.2` 个会话、最高 `32` 个会话、平均 `16,618.1 Tokens`，共 `1,986` 道 QA）**以降低闭源大模型全量评测的 API 成本。后续学术界（如 `Mem0`、`A-MEM`、`MemoryOS`、`MIRIX`）评测所称的 `LoCoMo` 均指该开源的 **10 会话版本（`locomo10.json`）**。下表完整并列两个版本的精确统计数据〔图表 `Table 1` & 附录 `App B Table 5`〕：

| 统计维度 | `MSC`（Xu et al., 2022） | `Conversation Chronicles`（2023） | **LoCoMo (`arXiv v1` 50 会话版)** | **LoCoMo (`ACL 2024` / `locomo10.json` 10 会话开源版)** |
| :--- | :---: | :---: | :---: | :---: |
| **总对话段数（`Total Conversations` $h$）** | — | — | **50** | **10**（`locomo10.json` 实测 `10`） |
| **每段对话平均会话数（`Avg. Sessions` $k$）** | 4.0 | 5.0 | **19.3**（最高 35） | **27.2**（最高 **32**，`locomo10.json` 实测 `27.2`） |
| **每段对话平均总轮数（`Avg. Turns`）** | 53.3 | 58.5 | **304.9**（每会话 `15.8` 轮） | **588.2**（每会话 `21.6` 轮，`locomo10.json` 实测 `588.2`） |
| **每段对话平均 Token 数（`Avg. Tokens`）** | 1,225.9 | 1,054.7 | **9,209.2**（每轮 `30.2` tok） | **16,618.1**（约为 `MSC` 的 **16 倍**） |
| **每轮观察断言平均长度（`Avg. Observation` $o_{k_j}$）** | — | — | 18.2 tok | 19.2 tok |
| **每会话摘要平均长度（`Avg. Summary` $w_k$）** | — | — | 127.4 tok | 132.4 tok |
| **每段对话平均真值事件数 / 摘要长度** | — | — | 24.2 个事件 / 896.5 tok | **35.8 个事件 / 1,042.7 tok** |
| **每段对话平均分享图片数（`Multimodal`）** | 0（纯文本） | 0（纯文本） | 32.3 张 | **91.2 张** |
| **QA 评测集总题数（`Total QA Questions`）** | — | — | **7,512** | **1,986**（`locomo10.json` 实测 `1,986`） |
| ├─ **Single-hop（单跳事实检索，代码中 `cat=4`）** | — | — | 2,705 (`36.0%`) | **841 (`42.3%`)** |
| ├─ **Multi-hop（跨会话多跳综合，代码中 `cat=1`）** | — | — | 1,104 (`14.6%`) | **282 (`14.2%`)** |
| ├─ **Temporal reasoning（时序推理，代码中 `cat=2`）** | — | — | 1,547 (`20.6%`) | **321 (`16.1%`)** |
| ├─ **Open-domain knowledge（外部常识结合，代码中 `cat=3`）** | — | — | 285 (`3.9%`) | **96 (`4.8%`)** |
| └─ **Adversarial（对抗/不可回答识别，代码中 `cat=5`）** | — | — | 1,871 (`24.9%`) | **446 (`22.4%`)** |

---

<a id="c16-2"></a>

## 16.2 受控人机协同合成管线：从人设与时序因果事件图到多模态长对话（`Sec 3, App A, generative_agents/`）

为了让合成的跨月对话具备真实的长期生活演变脉络而非停留在原地闲聊，`LoCoMo` 设计了四阶段生成与校验管线〔正文 `Sec 3:15–67`，图表 `Fig. 3`，源码 `generative_agents/`〕：

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    LoCoMo Four-Stage Human-Machine Generative Pipeline (Fig. 3)                 │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                 │
│  [Stage 1: Persona Expansion (Sec 3.1 & App A.1)]                                               │
│   Sample 4–5 sentence seed persona p_c from MSC dataset (data/msc_personas_all.json)            │
│     ──► GPT-3.5-turbo expands p_c into detailed Persona Statement p (name, age, gender, job,    │
│         objectives, past experiences, daily habits, relationships)                              │
│                                      │                                                          │
│  [Stage 2: Causal Temporal Event Graph G Generation (Sec 3.2 & event_utils.py:88–171)]          │
│   Assign date range [start_date, end_date] spanning 6–12 months (default --num-days 240):       │
│     ├─► Step 2a (Init): Generate k = 3 independent seed events E1, E2, E3 with dates t_i        │
│     ├─► Step 2b (Iterative Causal Expansion): Condition on p + existing events to generate      │
│     │     batches of 4 new events caused by prior events: {"sub-event", "date", "caused_by":    │
│     │     ["E1", ...], "id": "E4"} ( enforce t_cause < t_effect )                               │
│     └─► Step 2c (Standalone Pruning — filter_events): Remove any isolated node that has neither │
│           parent ("caused_by" == []) nor child references (up to 25–36 causally linked events)  │
│                                      │                                                          │
│  [Stage 3: Dual Virtual Agents with Reflect & Respond + Multimodal Sharing (Sec 3.3)]           │
│   For each Session k on date t_k^s (triggered 1–2 days after new events occur):                 │
│     ├─► Event Injection: Feed events {e ∈ G | t_{k-1}^s < t_i^e < t_k^s} + their causal parents │
│     │     ("On <date>, <sub-event> Because previously, <parent_event> (<parent_date>)")         │
│     ├─► Short-Term Memory H_s: Iterative Session Summary w_k = LLM(h_k, w_{k-1})                │
│     ├─► Long-Term Memory H_l : Turn-level factual Observations o_{k_j} with source [dia_id]     │
│     │     encoded by text-embedding-ada-002 + Self/Other Reflections (3 salient insights)       │
│     └─► Multimodal Actions   : Caption c → Keywords → icrawler Web Search → BLIP-2 Reaction     │
│                                      │                                                          │
│  [Stage 4: Human Verification & Long-Range Consistency Editing (Sec 3.4 & App A.3)]             │
│   In-house human annotators audit full multi-month transcripts & event graphs:                  │
│     • Edited ~15% of dialogue turns to fix cross-session contradictions & align with G          │
│     • Removed or replaced ~19% of web-crawled images; pruned unmentioned events from G          │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 源码级关键生成细节（`repos/locomo/generative_agents/`）

1. **时序因果事件图 $\mathcal{G}$ 的两步迭代与孤立节点剪枝（[`event_utils.py:88–171`](../../repos/locomo/generative_agents/event_utils.py#L88-L171)）**：
   - 在 `get_events()` 中，先调用 `EVENT_KG_FROM_PERSONA_PROMPT_SEQUENTIAL_INIT` 生成 3 个初始事件 `E1, E2, E3`；随后在 `while len(agent_events) < args.num_events` 循环中每次续写 4 个新事件（`next_event_ids`），要求每个新事件的 `"caused_by"` 字段必须引用至少一个发生日期更早的已有事件 ID（如 `"started a vegetable garden" → "harvested tomatoes"`）。
   - 生成完毕后调用 `filter_events(agent_events)`（`line 147–171`）：检查每个节点 $e$，若其既无父节点（`len(e["caused_by"]) == 0`）又从未被任何后续事件列为 `"caused_by"`，则将其判定为孤立事件（`standalone event`）直接剔除，从而保证整张图 $\mathcal{G}$ 具有严密的跨月因果链条。
2. **因果回溯提示词注入（[`generate_conversations.py:240–262`](../../repos/locomo/generative_agents/generate_conversations.py#L240-L262)）**：
   - 当会话 $k$ 启动时，`get_event_string` 不仅把发生在区间 $(t_{k-1}^s, t_k^s]$ 内的当前事件注入智能体提示词，而且一旦发现 `len(e['caused_by']) > 0`，会自动拼接因果回溯子句：`"On <date>, <sub-event> Because previously, <parent_sub_event> (<parent_date>)"`。这从生成源头上保证了说话人在第 $k$ 个会话讨论近况时，会自然呼应数周或数月前第 $k'$ 个会话埋下的伏笔。
3. **短期会话摘要 $\mathcal{H}_s$、长期观察库 $\mathcal{H}_l$ 与双向反思（[`memory_utils.py:22–163`](../../repos/locomo/generative_agents/memory_utils.py#L22-L163)）**：
   - 每个会话结束后，`get_session_facts`（`line 35–79`）将带轮次编号 `[D<sess>:<turn>]` 的对话转换为客观事实断言列表（`Observations`，严格禁止生成“说话人很支持对方”这类空泛抽象评价，`line 23`），连同会话日期前缀编码为 `text-embedding-ada-002` 向量存入 `embeddings.pkl`；
   - `get_session_reflection`（`line 82–126`）分别让智能体 A 和 B 更新 3 条关于自己（`self`）与 3 条关于对方（`other`）的核心洞察；
   - 在下一会话的第 0 轮使用最近历史与上一会话摘要初始化，从第 1 轮起每轮调用 `get_relevant_context`（`line 146–162`）根据对方上一句话向量检索 Top-2 相关历史观察 + 随机采样 1 条反思注入上下文。

---

<a id="c16-3"></a>

## 16.3 三大评测任务、指标体系与全量实验结果（`Sec 4–6, Tables 2–4`）

### 1. 三大任务与评分算式（`Sec 4.1–4.3, task_eval/evaluation.py`）

1. **任务一：五类长程记忆问答（`Question Answering`，`Sec 4.1`）**：
   - 涵盖 **Single-hop**（单会话内事实定位）、**Multi-hop**（跨多会话信息综合）、**Temporal reasoning**（结合会话顶部 `DATE` 时间戳与对话内相对时间词推算日期/时长）、**Open-domain knowledge**（结合说话人信息与外部世界常识推断）、**Adversarial**（问题前提张冠李戴或询问未提及细节，测试模型能否识别不可回答）五类推理。
   - **评分指标**：对预测文本与真值执行去冠词（`a/an/the/and`）、去标点、转小写与 `PorterStemmer` 词干提取后计算词级 **部分匹配 F1（`Token-level F1 Score`）**（其中 `Multi-hop` 按逗号 `,` 切分子答案分别求最大 F1 后取均值，见 `evaluation.py:126–146`）；对 RAG 模型同时汇报真值证据轮次 `evidence` 的检索召回率 **`Recall@k`（`R@k`）**。
2. **任务二：因果事件图摘要（`Event Summarization`，`Sec 4.2`）**：
   - 要求模型从整段跨月对话历史中还原出每位说话人的关键人生事件列表，并以生成对话时底层的真值事件图 $\mathcal{G}$ 作为 Ground Truth。
   - **评分指标**：除常规 `ROUGE-1/2/L` 外，核心采用 **`FactScore`（Min et al., 2023）**——将预测摘要与真值事件图 $\mathcal{G}$ 拆解为原子事实（`Atomic Facts`），分别计算原子事实的精确率（`Precision`）、召回率（`Recall`）与综合 `FactScore F1`。
3. **任务三：多模态长程对话生成（`Multi-Modal Dialogue Generation`，`Sec 4.3`）**：
   - 在 50 段未经过滤的自动合成对话上微调 `MiniGPT-5`（对比 `Base`、`+ Summary`、`+ Observation` 三种训练配置），使用 `BLEU-1/2`、`ROUGE-L` 与多模态图文相关性指标 **`MM-Relevance`（`MM-R`）** 评测生成回复与分享图片的人设一致性。

### 2. 任务一（QA）全量基线结果：ACL 2024 正式版（10 会话，1,986 题）与 arXiv v1（50 会话，7,512 题）对照

#### (a) Base 与 Long-Context 模型表现（`ACL 2024 Table 2` 对比 `arXiv v1 Table 2`）

| 数据集版本 | 模型类别 | 模型名称 | 上下文窗口 | Single Hop (`F1`) | Multi Hop (`F1`) | Temporal (`F1`) | Open Domain (`F1`) | Adversarial (`F1`) | **Overall (`F1`)** |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **ACL 2024 正式版**<br>(`locomo10.json`,<br>10 会话, 1,986 题) | **Human** | 人类基准 | — | 95.1 | 85.8 | 92.6 | 75.4 | 89.4 | **87.9** |
| | **Base** (截断) | `Mistral-7B-Instruct-v0.2` | 8K | 19.1 | 15.1 | 9.3 | 8.6 | 28.9 | 18.7 |
| | | `Llama-2-70b-chat` | 4K | 20.8 | 18.2 | 15.9 | 18.8 | 15.7 | 18.4 |
| | | `Llama-3-70B-Instruct` | 4K | 17.0 | 17.0 | 12.0 | 13.0 | **80.0** | 30.1 |
| | **Long-Context** | `gpt-3.5-turbo` | 4K | 23.8 | 18.0 | 15.6 | 20.4 | 34.8 | 23.9 |
| | | `gpt-3.5-turbo` | 8K | 38.5 | 25.1 | 22.7 | 25.9 | 28.7 | 31.2 |
| | | `gpt-3.5-turbo` | 12K | 45.7 | 32.4 | 25.5 | 23.4 | 21.5 | 34.0 |
| | | `gpt-3.5-turbo-16k` | 16K | 52.6 | 36.7 | 24.3 | 24.0 | 14.8 | 35.9 |
| | | `gemini-1.0-pro` | 32K | 62.4 | 35.3 | 34.2 | 19.0 | 5.2 | 39.1 |
| | | `claude-3-sonnet` | 200K | 70.7 | 38.1 | 26.9 | **52.2** | 2.5 | 42.8 |
| | | **`gpt-4-turbo`** | **128K** | **72.3** | **51.5** | **51.4** | 38.5 | 15.7 | **51.6** |
| **arXiv v1 初版**<br>(50 会话, 7,512 题) | **Base** (截断) | `Mistral-Instruct-7B` | 8K | 10.2 | 12.8 | 16.1 | 19.5 | 17.0 | 13.9 |
| | | `Llama-2-Chat-70B` | 4K | 19.7 | 14.4 | 13.3 | 15.9 | 22.1 | 17.9 |
| | | `GPT-3.5-turbo` | 4K | 29.9 | 23.3 | 17.5 | 29.5 | 12.8 | 22.4 |
| | | `GPT-4-turbo` (截断至 4K) | 4K | 23.4 | 23.4 | 10.4 | 24.6 | **70.2** | 32.1 |
| | **Long-Context** | `GPT-3.5-turbo-16K` | 4K / 8K / 12K / 16K | 31.7 → **56.4** | 25.4 → **42.0** | 16.8 → **25.0** (12K) | 27.6 → **37.2** | 13.1 → **2.1** (16K) | 24.1 → **37.8** |

#### (b) RAG 不同检索粒度（`Dialog` vs. `Observation` vs. `Summary`）表现（`ACL 2024 Table 3` 对比 `arXiv v1 Table 3`，基于 `DRAGON` 检索器 + `gpt-3.5-turbo-16k` 阅读器）

| 检索库粒度（`Retrieval Unit`） | `top-k` | ACL 2024 `Single` (`F1` \| `R@k`) | ACL 2024 `Multi` (`F1` \| `R@k`) | ACL 2024 `Temporal` (`F1` \| `R@k`) | ACL 2024 `Open` (`F1` \| `R@k`) | ACL 2024 `Advers.` (`F1` \| `R@k`) | **ACL 2024 `Overall` (`F1` \| `R@k`)** | **arXiv v1 `Overall` (`F1` \| `R@k`)** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `None`（16K/4K 直接读） | — | 52.6 \| — | 36.7 \| — | 24.3 \| — | 24.0 \| — | 14.8 \| — | **35.9** \| — | 22.4 (4K) \| — |
| **`Dialog`（原始对话轮）** | `k=5` | 53.3 \| 68.0 | 31.2 \| 35.4 | 35.4 \| 70.4 | 25.0 \| 33.1 | 21.5 \| 43.9 | 38.8 \| 56.7 | 31.7 \| 58.8 |
| | `k=10` | 56.9 \| 77.7 | 34.6 \| 46.6 | 34.5 \| 77.3 | 23.9 \| 40.8 | 17.5 \| 54.7 | 39.7 \| 66.2 | 34.6 \| 67.5 |
| | `k=25` | 59.9 \| 87.1 | 38.7 \| 62.5 | **37.2** \| 83.5 | 25.0 \| 52.6 | 12.8 \| 66.3 | **41.0** \| 76.7 | **35.8** \| 79.9 |
| | `k=50` | **60.1** \| **91.1** | **40.6** \| **73.0** | 36.9 \| **89.6** | 22.4 \| **61.7** | 9.9 \| **72.5** | 40.5 \| **82.7** | 34.8 \| **84.8** |
| **`Observation`（结构化事实断言）** | **`k=5`** | 54.3 \| 67.1 | 36.3 \| 41.4 | **40.7** \| 73.1 | **26.5** \| 35.1 | **32.5** \| 37.7 | **`43.3`** \| 56.2 | **`41.4`** \| 49.6 |
| | `k=10` | 54.6 \| 70.5 | 39.2 \| 50.9 | 40.5 \| 76.4 | 24.4 \| 37.6 | 28.5 \| 45.1 | 42.8 \| 61.3 | 38.8 \| 57.1 |
| | `k=25` | **54.7** \| 74.7 | 41.2 \| 60.6 | 38.8 \| 80.3 | 25.8 \| 49.0 | 24.7 \| 53.5 | 42.1 \| 67.5 | 38.0 \| 66.0 |
| | `k=50` | 54.1 \| **76.3** | **41.6** \| **67.8** | 37.6 \| **82.0** | 24.4 \| **55.9** | 20.4 \| **59.5** | 40.6 \| **71.2** | 37.8 \| **71.1** |
| **`Summary`（会话级粗摘要）** | `k=2` | 32.8 \| 63.0 | 22.4 \| 33.0 | 32.9 \| 57.7 | 19.0 \| 31.5 | 25.3 \| 65.9 | 29.0 \| 65.9 | 29.9 \| 61.5 |
| | `k=5` | 35.1 \| 77.0 | 26.0 \| 54.3 | 37.4 \| 72.8 | 21.2 \| 47.6 | 23.5 \| 79.1 | 30.9 \| 72.1 | **32.5** \| 75.1 |
| | `k=10` | 36.0 \| **88.7** | 29.9 \| **72.7** | 37.5 \| **84.5** | 22.2 \| **67.3** | 24.0 \| **88.8** | 32.0 \| **84.7** | 31.5 \| **90.7** |

**核心实证发现（`Sec 6.1–6.2`）**：
1. **长上下文窗口引发“对抗题幻觉雪崩（Adversarial Hallucination Collapse）”**：
   - 将 `gpt-3.5-turbo` 的输入窗口从 `4K` 扩大到 `16K` 时，虽然单跳（`23.8 → 52.6`）与多跳（`18.0 → 36.7`）大幅上升，但**对抗题准确率却从 `34.8%` 断崖式暴跌至 `14.8%`**（在 `arXiv v1` 上更是从 `13.1%` 跌至 **`2.1%`**）；`claude-3-sonnet (200K)` 与 `gemini-1.0-pro (32K)` 在对抗题上也仅有 **`2.5%`** 与 **`5.2%`**！因为当整段万字对话塞入上下文时，模型极易发生**说话人张冠李戴（Speaker Misattribution）**，把 A 做的事强加给 B，丧失了“未提及则拒答”的判断力。
2. **为什么抽取为原子事实断言（`Observation top-5`，`43.3 F1`）远胜检索原始对话（`Dialog`）与会话摘要（`Summary`）？**
   - **对比 `Summary`（`30.9 ~ 32.0 F1`）**：尽管检索会话级摘要的会话命中率 `R@10` 高达 `84.7% ~ 90.7%`，但问答 F1 反而比不加 RAG 的 `16K` 基线（`35.9`）还低 `-3.9 ~ -6.9` 分——因为粗粒度会话摘要在压缩时丢失了回答细节问题所需的精确时间、地点与实体名。
   - **对比增大 `k`（`Observation k=5 → k=50`）**：当召回的 `Observation` 数量从 `top-5` 增加到 `top-50` 时，虽然证据召回率 `R@k` 从 `56.2%` 升至 `71.2%`，但最终问答 F1 却从 **`43.3`** 退化至 **`40.6`**（对抗题更是从 `32.5` 跌至 `20.4`）——再次印证了**提高检索上下文的信噪比（`SNR`）比盲目堆砌召回数量更关键**。
3. **事件图摘要任务（`Table 4`）与五类典型错误分类（`App D Table 6`）**：
   - 在 `ACL 2024 Table 4` 中，即便是最强的 `gpt-4-turbo (128K)`，其事件图摘要 `FactScore F1` 也仅为 **`53.5`**（`ROUGE-L = 22.8`），`claude-3-sonnet (200K)` 为 `44.2`，`gemini-1.0-pro (32K)` 为 `43.2`。
   - 作者人工归类了大模型在跨月事件归纳中的**五大顽疾（`Table 6`）**：① **跨期因果遗漏（`Missing Information`）**；② **跨事件嫁接幻觉（`Hallucination`）**（如把“游戏派对很成功、下月还想办”嫁接到同一会话提到的“做了纯素冰淇淋”上）；③ **语用/玩笑误判（`Misunderstanding of Dialog Cues`）**（把说话人随口开玩笑的话当成严肃人生事件）；④ **说话人归属颠倒（`Speaker Attribution`）**（把 Nate 请 Joanna 吃自制无乳糖冰淇淋记成 Joanna 请 Nate）；⑤ **寒暄噪声误判为重要事件（`Saliency`）**。

---

<a id="c16-4"></a>

## 16.4 开源仓 `repos/locomo` 源码实现与论文的五处关键差异对账

通过逐行比对 [`papers/repos/locomo/`](../../repos/locomo/) 源码、[`data/locomo10.json`](../../repos/locomo/data/locomo10.json) 数据集与论文正文，我们整理出复现与引用 `LoCoMo` 时必须掌握的五处底层差异：

| 维度 | 论文正文 / 表格描述 | 开源仓库与 `locomo10.json` 实际实现（附文件与行号） | 复现与评测横向对账影响 |
| :--- | :--- | :--- | :--- |
| **1. 五类 QA 的整数 `category` 编码顺序颠倒** | 正文 `Sec 4.1:8–13` 与 `Table 2 / Table 3` 均按 **(1) Single-hop、(2) Multi-hop、(3) Temporal、(4) Open-domain、(5) Adversarial** 的顺序编号和排列。 | 在 [`data/locomo10.json`](../../repos/locomo/data/locomo10.json) 与 [`task_eval/evaluation.py:203–221`](../../repos/locomo/task_eval/evaluation.py#L203-L221)、[`evaluation_stats.py:98`](../../repos/locomo/task_eval/evaluation_stats.py#L98) 中，底层 JSON 的整数标签实际映射为：<br>• `category == 1`：**Multi-hop**（282 题，按逗号拆分子答案算 F1）<br>• `category == 2`：**Temporal**（321 题，`gpt_utils.py:243` 追加日期提示）<br>• `category == 3`：**Open-domain**（96 题，`evaluation.py:203` 按分号截断）<br>• `category == 4`：**Single-hop**（841 题）<br>• `category == 5`：**Adversarial**（446 题）<br>因此 `evaluation_stats.py:98` 专门写死 `keys = [4, 1, 2, 3, 5]` 以对齐论文表头顺序！ | **这就是为什么后续论文（如我们在 `02_memory_memoryos.md` 与 `07_memory_amem.md` 中揭露的）直接按 `1..5` 循环打印时，会把 `Multi-hop (1)` 与 `Single-hop (4)`、`Temporal (2)` 与 `Open-domain (3)` 的列头彻底搞混！** |
| **2. `Category 5`（对抗题）在 JSON 中缺失 `'answer'` 键引发 `KeyError`** | 正文称每道 QA 均包含 `question`、`answer`、`category` 与 `evidence`。 | 在 `locomo10.json` 中，`category 1~4` 的键名为 `'answer'`，唯独 **`category == 5` 的 446 道题没有 `'answer'` 键，而是命名为 `'adversarial_answer'`**（存放误导性错误答案，如 `'self-care is important'`）！然而官方评测脚本 [`gpt_utils.py:248`](../../repos/locomo/task_eval/gpt_utils.py#L248) 与 [`evaluation.py:202`](../../repos/locomo/task_eval/evaluation.py#L202) 仍直接读取 `qa['answer']`，直接运行会抛出 `KeyError: 'answer'`。 | 复现时必须在读取 `category == 5` 时兼容 `qa.get('answer', qa.get('adversarial_answer'))`。 |
| **3. `Category 5` 评测形式：二选一选择题 vs. 开放拒答字符串匹配** | 正文 `Sec 4.1:13` 描述为测试智能体能否识别问题为不可回答（`unanswerable`）。 | 在 [`gpt_utils.py:245–256`](../../repos/locomo/task_eval/gpt_utils.py#L245-L256) 中，推理提示词实际将 `Category 5` 构造为 **(a)/(b) 二选一单项选择**：随机将 `'Not mentioned in the conversation'` 与误导答案 `qa['answer']` 放入 `(a)` 或 `(b)`，再由 `get_cat_5_answer` 还原选项文本后，在 [`evaluation.py:217–221`](../../repos/locomo/task_eval/evaluation.py#L217-L221) 中通过硬编码子串 `'no information available' in output.lower() or 'not mentioned' in output.lower()` 判 1 或 0 分。 | 这意味着原版 `LoCoMo` 的 Category 5 并非纯开放式拒答，而是二选一诱捕；若外部记忆系统不构造 `(a)/(b)` 选项而自由作答，只有输出中恰好包含 `'not mentioned'` 或 `'no information available'` 才能得分。 |
| **4. `Category 3`（Open-domain）真值分号截断规则** | 论文正文未说明多候选真值如何处理。 | 在 [`evaluation.py:203–204`](../../repos/locomo/task_eval/evaluation.py#L203-L204) 中写有：`if line['category'] == 3: answer = answer.split(';')[0].strip()`——即对于开放域问题，若标注中包含分号分隔的多个备选解释，评测代码仅取第一个分号前的短语算 F1。 | 解释了为什么各模型在 `Open-domain` 类别上词级 F1 普遍偏低（部分合理同义推断被词干匹配判为 0）。 |
| **5. `arXiv v1 Table 3` 排版笔误与 `ACL 2024` 修正** | 在 `arXiv v1` 的 [`6_results.tex:47`](../../benchmark/2402.17753/source/sections/6_results.tex#L47)（`Table 3`，`Dialog top-10` 的 `Multi Hop R@k`）中写为 `247.4`。 | 召回率不可能超过 `100%`，`247.4` 系 `47.4%` 前多打了一个 `2` 的 LaTeX 录入笔误；在 `ACL 2024 Camera-Ready` 正式版 `Table 3`（10 会话版）中已修正为 `46.6%`。 | 引用 `LoCoMo` 原表数据时应以 `ACL 2024 Camera-Ready` 的 10 会话版为准。 |

---

<a id="c16-5"></a>

## 16.5 对联接 Agent 主报告（1.1 / 2.5 / 4.2 节）的落地启发

`LoCoMo` 为我们主报告 [`storyline_and_evaluation_merged_technical_route_report.html`](../../../../.lavish/storyline_and_evaluation_merged_technical_route_report.html) 的**合成数据工程（第 2 章）**与**记忆系统评测设计（第 1、4 章）**提供了三项直接支撑：

1. **用“底层时序因果事件图 $\mathcal{G}$ + `caused_by` 显式回溯”驱动跨周期故事线生成（支撑 2.5 节）**：
   - 如果直接让大模型按人设自由生成 20 轮会话，生成的内容很快就会同质化或前后矛盾。`LoCoMo` 的 `event_utils.py` 证明：必须**先在底层生成一张带精确时间戳与 `"caused_by"` 因果有向边的事件图 $\mathcal{G}$（并调用 `filter_events` 剪除无因果关联的孤立事件）**，再按时间窗将事件连同其父事件（`"Because previously..."`）分段喂给对话生成器，才能合成出跨越数月依然逻辑自洽的“单据 + 对话”演化轨迹。
2. **记忆存储单元必须以“带溯源 ID 的客观事实断言（`Observation` + `[dia_id]`）”为主，而非仅存粗粒度会话摘要（支撑 3.3.1 / 3.3.2 节）**：
   - `Table 3` 的对比极具说服力：会话级摘要（`Summary`）虽然会话召回率高达 `84.7% ~ 90.7%`，但因丢失细粒度槽位导致 QA F1 仅 `30.9 ~ 32.0`（甚至不如不检索）；而将每轮对话抽取为带 `[D<sess>:<turn>]` 证据指针的客观事实断言（`Observation`，严格过滤主观寒暄），在仅召回 `top-5` 时即可取得 **`43.3`** 的最高分。
3. **长上下文下的“说话人归属错乱”与“对抗拒答崩塌”必须设立专项红线考核（支撑 1.1 / 4.2 节）**：
   - `LoCoMo` 揭示了当历史记录拉长到 16K~200K 时，大模型在对抗题（`Category 5`）上的准确率会从 `70%~80%` 暴跌至 `2.1%~15.7%`，并频繁发生张冠李戴（把同行旁人或历史误导信息安在主用户头上）。这直接支撑了我们在评测基准中设立**未知/未提及槽位拒答（`Abstention / Adversarial`）**与**多说话人归属隔离（`Speaker Attribution`）**两项核心指标。

---

← 返回 [精读笔记索引](../reading_notes.md)　·　[论文主目录](../../README.md)

# 17 · LoCoMo-Plus：超越显式事实的隐式认知约束记忆评测基准（2026-02）

> **所属梯队**：`P2-2` · `benchmark/`
> **论文标题**：*Locomo-Plus: Beyond-Factual Cognitive Memory Evaluation Framework for LLM Agents*
> **作者与机构**：Yifei Li, Weidong Guo, Lingling Zhang, Rongman Xu, Muye Huang, Hui Liu, Lijiao Xu, Yu Xu, Jun Liu（西安交通大学等；`ARR Jan 2026` / `arXiv:2602.10715v1`, `2026-02-11`）
> **本地 PDF**：[`LoCoMo_Plus_2026.pdf`](../../benchmark/LoCoMo_Plus_2026.pdf)
> **本地 Markdown / LaTeX 源码**：[`2602.10715.md`](../../benchmark/2602.10715/2602.10715.md)（源码：[`main.tex`](../../benchmark/2602.10715/source/main.tex)）
> **对应开源仓**：[`Locomo-Plus`](../../repos/Locomo-Plus/)（`https://github.com/xjtuleeyf/Locomo-Plus`）
> **在主报告中支撑的章节**：`1.1 方向一 & 2.5 节`（区分显式事实回忆与隐式认知约束记忆，在提示词/触发句与线索句零字面重合的语义断层下评测状态、目标、因果与价值观约束一致性，揭示长上下文干扰下的认知记忆塌缩与传统表面匹配评测偏差）

---

<a id="c17-1"></a>
## 17.1 背景与核心问题：为什么显式事实 QA 测不出真实的对话记忆

1. **现有基准的两大盲区**〔正文 `Sec 1–2`〕：
   - 以 [`LoCoMo`](16_benchmark_locomo.md) 为代表的长期对话记忆基准，把“记忆”等价于**显式事实回忆（Level-1 Factual Memory）**：关键信息在早期对话中被直白说出，后期问题又与原话存在明显语义/词汇对齐。
   - 真实助手交互中，记忆常常不是拿来回答“你哪天吃了什么”，而是作为**隐式行为约束（Level-2 Cognitive Memory）**起作用。例如：用户几个月前提到“自己表弟确诊了 2 型糖尿病，从此彻底戒掉了含糖饮料”，很久之后只感叹一句“真不敢相信以前自己从不顾长远后果乱喝乱吃”。触发句与原始线索之间**没有任何词汇重合**，但恰当的回复必须识别因果延续并保持约束一致。
2. **传统评测范式的双重失真**〔正文 `Sec 1 & 5`〕：
   - **输入端任务披露（Task Disclosure）**：评测时直接给模型加“这是一个记忆问答任务”或分类指令，诱导模型切换到应试/猜题策略，尤其人为拉高了时序推理与对抗拒答的得分。
   - **输出端字符串匹配（Surface-Form Matching）**：对存在多种合法表达的开放式回复强行算 `EM / F1 / BLEU / ROUGE-L`，把记忆保真度与生成长度、措辞风格混为一谈。

---

<a id="c17-2"></a>
## 17.2 问题定义与双层记忆分类体系（Level-1 vs. Level-2）

给定多轮交互历史 $\mathcal{H} = \{u_1, a_1, \dots, u_t, a_t\}$ 与后续查询 $q_{t+1}$，系统生成回复 $a_{t+1}$〔正文 `Sec 3`〕：

| 记忆层级 | 定义与约束形式 | 正确性判定 | 代表子维 |
| :--- | :--- | :--- | :--- |
| **Level-1 事实记忆（Factual Memory）** | 历史中显式陈述的对象事实或事件信息，存在明确标准答案 $y^\ast$ | $a_{t+1}$ 与 $y^\ast$ 在实体、时间或推理结论上语义一致 | 原 `LoCoMo` 五类（`single-hop / multi-hop / temporal / commonsense / adversarial`） |
| **Level-2 认知记忆（Cognitive Memory）** | 历史隐含的状态、目标、价值观或因果背景，诱导一个**隐式约束 $c$**，定义合法输出空间 $\mathcal{A}_c = \{a \mid a \text{ is consistent with } c\}$ | 不存在单一参考答案，只要 $a_{t+1} \in \mathcal{A}_c$ 即为正确 | **4 类隐式约束**：`Causal`（因果）、`State`（状态）、`Goal`（目标）、`Value`（价值观） |

〔实现〕在开源仓 [`locomo_plus.json`](../../repos/Locomo-Plus/data/locomo_plus.json) 中，`Level-2` 数据共 **401 条**：`causal` 101 条、`state` 100 条、`goal` 100 条、`value` 100 条。

---

<a id="c17-3"></a>
## 17.3 六阶段数据构造管线与语义断层过滤

```
┌────────────────────────────────────────────────────────────────────────────┐
│            LoCoMo-Plus 认知记忆样本构造与混合注入流水线 (Sec 4 & App 8)     │
└────────────────────────────────────────────────────────────────────────────┘
  Stage 1 隐式线索生成 ──► LLM 生成 2 轮自然日常短对话 c0（含可记忆细节，非直白事实）
         │
         ▼
  Stage 2 记忆价值人工核验 ──► 剔除可由局部语境推断或无长期约束价值的样本 ──► c1
         │
         ▼
  Stage 3 触发查询生成 ──► 针对每条 c1 从 5 个不同认知冲突/反思角度生成第一人称触发句 q
         │                 （要求时间跨度 ≥1 周，避免复用线索中的名词与动词）──► (c1, q, t)0
         ▼
  Stage 4 语义断层过滤 ──► 计算 BM25 + 稠密向量相似度，淘汰字面重复/近义改写快捷方式 ──► (c1, q, t)1
         │                 （源码 rank.py:68 融合 MPNet + BGE + BM25，均值 0.5786）
         ▼
  Stage 5 记忆诱发人工终审 ──► 确认必须回忆 c1 的隐式约束才能给出合理回应 ──► (c1, q, t)2 (401 条)
         │
         ▼
  Stage 6 嵌入 LoCoMo 长对话 ──► 按 time_gap 回推插入时间戳，把 A/B 映射为对话双方真实姓名
                                 （unified_input.py 合并原 LoCoMo 五类与第 6 类 Cognitive）
```

〔正文 `Sec 4` + 附录 `App 8`〕Prompt 设计要点（`Tables 4–5`）：
- **线索对话 Prompt（`cue_prompt`）**：固定 2 轮（`A` 说一件有辨识度细节的事，`B` 自然收尾闭合对话），跨工作、家庭、健康、旅行等主题，生成参数 $T=0.7$、单条上限 256 tokens、`num_samples=50`。
- **触发查询 Prompt（`trigger_prompt`）**：强制从同一人称 `A` 角度一次产出 **5 个互不重复的认知角度**（陈述、情绪、反问或反思），明确要求与 `cue_dialogue` **语义不相关但认知连通**、**禁用线索中的名词与动词**、**时间间隔 $\ge 1$ 周至数月**。

---

<a id="c17-4"></a>
## 17.4 统一评测框架与全量实验发现

### 17.4.1 输入/输出解耦与分级 Judge 设计

〔正文 `Sec 5.3` + 附录 `App 9`〕作者提出**统一输入、分化判分（Unified-Input, Differentiated-Judgment）**范式：
- **单/多跳与常识（`single-hop / multi-hop / common-sense`）**：采用三档标签 `correct (1.0) / partial (0.5) / wrong (0.0)`，避免把“说到上位概念（如 `seafood` 对应 `grilled salmon`）”当成完全失败。
- **时序推理（`temporal`）与对抗（`adversarial`）**：二值标签 `correct (1.0) / wrong (0.0)`，时间计算与幻觉拒答不给部分分。
- **认知记忆（`Cognitive`）**：二值标签 `correct (1.0) / wrong (0.0)`，**无参考答案 `gold`**，由 Judge 对比 `{evidence}`（即嵌入的 `cue_dialogue`）与 `{pred}`，判定回复是否显式或隐式体现并适配了该记忆约束。

### 17.4.2 主表全量对比（`Table 1` in `Sec 5`）

| 类别 / 方法 | `single-hop` | `multi-hop` | `temporal` | `commonsense` | `adversarial` | **LoCoMo 均值** | **LoCoMo-Plus** | **落差 (Gap)** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **开源大模型（全上下文）** | | | | | | | | |
| `Qwen2.5-3B-Instruct` | 68.25 | 38.65 | 18.38 | 48.44 | 11.69 | 42.20 | 10.82 | `-31.38` |
| `Qwen2.5-7B-Instruct` | 70.72 | 39.54 | 21.81 | 37.50 | 20.22 | 45.31 | 9.57 | `-35.74` |
| `Qwen2.5-14B-Instruct` | 76.33 | 48.23 | 38.94 | 57.29 | 68.09 | 63.45 | 19.24 | `-44.21` |
| `Qwen3-4B` | 69.52 | 46.10 | 33.33 | 55.21 | 48.76 | 54.91 | 15.70 | `-39.21` |
| `Qwen3-8B` | 69.34 | 43.79 | 39.88 | 59.90 | 53.48 | 56.86 | 17.68 | `-39.18` |
| `Qwen3-14B` | 65.96 | 46.45 | 53.89 | 59.38 | 60.45 | 59.65 | 19.09 | `-40.56` |
| **闭源大模型（全上下文）** | | | | | | | | |
| `gpt-5-nano` | 75.00 | 54.08 | 50.16 | 73.96 | 17.53 | 54.96 | 14.84 | `-40.12` |
| `gpt-4.1` | 80.30 | 53.90 | 58.88 | 72.92 | 37.30 | 62.21 | 18.63 | `-43.58` |
| `gpt-4o` | 78.13 | 52.30 | 45.79 | 69.79 | 48.99 | 62.99 | 21.05 | `-41.94` |
| `gemini-2.5-flash` | 77.71 | 54.26 | 66.04 | 66.67 | 65.84 | 69.25 | 24.67 | `-44.58` |
| `gemini-2.5-pro` | 77.83 | 52.48 | 73.83 | 63.54 | **73.03** | **71.78** | **26.06** | `-45.72` |
| **RAG 基线（GPT-4o, Top-5 片段）** | | | | | | | | |
| `text-ada-embedding-002` | 40.00 | 16.73 | 37.81 | 15.73 | 49.44 | 37.38 | 13.91 | `-23.47` |
| `text-embedding-small` | 39.17 | 17.79 | 34.69 | 14.61 | 51.90 | 37.23 | 12.29 | `-24.94` |
| `text-embedding-large` | 49.76 | 22.78 | 40.00 | 21.35 | 59.73 | 45.32 | 15.55 | `-29.77` |
| **专用记忆系统（GPT-4o）** | | | | | | | | |
| `Mem0` | 80.20 | 48.10 | 39.40 | 66.20 | 30.50 | 57.24 | 15.80 | `-41.44` |
| `SeCom` | 77.60 | 50.90 | 42.30 | 71.40 | 31.80 | 57.53 | 14.90 | `-42.63` |
| `A-Mem` | 76.90 | 55.60 | 49.30 | 68.10 | 35.20 | 59.64 | 17.20 | `-42.44` |

**核心结论**：
1. **全体系统在认知记忆上集体失灵**：哪怕全上下文 `gemini-2.5-pro` 在原 `LoCoMo` 达到 `71.78%`，在 `LoCoMo-Plus` 上仍骤降至 `26.06%`（落差 `45.72` 个百分点）；专用记忆系统 `Mem0 / SeCom / A-Mem` 仅得 `14.90%–17.20%`，甚至低于全上下文 `GPT-4o`（`21.05%`），说明基于语义相似度检索的外部记忆在 `cue–trigger` 零词汇重合下极易漏检。
2. **上下文增长对三类记忆的差异化冲击**（`Fig. 7`）：100 条代表性样本长度敏感性测试表明，对象事实记忆随轮数增长几乎稳健不降；情景记忆呈线性渐进退化；而认知记忆在长上下文干扰下发生**陡峭塌缩**。
3. **评测偏差实证与 Judge 可靠性**（`Sec 6.3, Tables 1–2, Fig. 5–6`）：
   - **长度偏差**：参考答案均值仅 `5.18 tokens`，传统 `EM / F1 / BLEU / ROUGE-L` 都在输出接近 `5 tokens` 时达到峰值，偏长或偏短均被系统性惩罚。
   - **Judge 一致性**：两位人类标注者间一致率为 `0.903`，`Gemini-2.5-Flash` Judge 与两位人类分别达到 `0.801` 和 `0.820`；更换 Judge 为 `GPT-4o` 时，6 个待测模型得分绝对差 $|\Delta|$ 在 `0.68–3.33` 分之间（`14B` 模型仅差 `0.68–0.72`）。此外作者展示了原 `LoCoMo` 中 `ground_truth` 本身标错星期几（`Sunday` vs. 对话原文 `Saturday`）导致人类按答案误判、而以对话证据为准的 LLM Judge 正确判分并指出真值矛盾的案例（`Table 3`）。

---

<a id="c17-5"></a>
## 17.5 论文与开源仓库（`repos/Locomo-Plus`）源码对账

经核查 [`Locomo-Plus`](../../repos/Locomo-Plus/) 全部源码与 [`locomo_plus.json`](../../repos/Locomo-Plus/data/locomo_plus.json)，存在 **五处重要细节差异**：

| 核查维度 | 论文表述 | 开源仓实际实现与数据 |
| :--- | :--- | :--- |
| **1. 生成模型分布与数据集规模** | `App 8` 写明使用 `gpt-5-nano, gpt-4o, gpt-4.1, gemini-2.5-flash, gemini-2.5-pro` 生成 | [`locomo_plus.json`](../../repos/Locomo-Plus/data/locomo_plus.json) 共 **401 条**，实际 `model_name` 分布为 `gpt-5.1` (220)、`gemini-2.5-flash` (90)、`gpt-5-nano` (44)、`gpt-4o-mini` (39)、`gpt-4o` (8)，不含 `gpt-4.1` 与 `gemini-2.5-pro` |
| **2. 语义过滤计算公式** | `Sec 4.4` 仅提及用 `BM25` 与 `MPNet` 过滤高相似度样本 | [`rank.py:36,68`](../../repos/Locomo-Plus/generation_pipeline/rank.py#L68) 实际同时加载了 `MPNet` 与 `BAAI/bge-small-en-v1.5`，加权式为 `0.8 * mean(mpnet, bge) + 0.2 * (bm25 / (bm25 + 1))`；401 条保留样本该分值区间为 `[0.4589, 0.6332]`（均值 `0.5786`） |
| **3. 时间插入与会话日期头丢失** | `Sec 4.6` 描述按 `time_gap` 嵌入 `LoCoMo` 长对话 | [`build_conv.py:94-96`](../../repos/Locomo-Plus/data/build_conv.py#L94-L96) 固定设 `query_time = session_times[-1] + 7 days`，再反推 `cue_time`；[`unified_input.py:165-169`](../../repos/Locomo-Plus/data/unified_input.py#L165-L169) 拼接 `Cognitive` 样本时只输出 `Speaker said, "..."`，**未像原 `LoCoMo` 五类那样保留 `DATE: ... CONVERSATION:` 头** |
| **4. 输入端“去任务披露”的源码折中** | `Sec 5.1 & 5.3` 主张去掉显式任务披露，以自然对话延续输入 | [`utils.py:20-35, 126`](../../repos/Locomo-Plus/evaluation_framework/task_eval/utils.py#L20-L35) 在真实调用 `call_llm` 前仍根据 `category` 拼接了不同提示：五类 QA 拼 `INSTRUCTION_QA`，`Cognitive` 仍显式拼入 `INSTRUCTION_COGNITIVE`（告知模型“这是记忆感知对话，请在回复中体现对线索上下文的感知”） |
| **5. Judge 模板字段差异** | `App 9 Table 3` 中 `Cognitive` 提示词含 `Question/Trigger` 交互说明，`Temporal` 未写 `{evidence}` | [`prompt.py:72-73, 118-134`](../../repos/Locomo-Plus/evaluation_framework/task_eval/prompt.py#L118-L134) 中 `Cognitive` 仅传 `{evidence}` 与 `{pred}`（未传 `trigger_query`）；`temporal` 模板也传入了 `{evidence}`；`llm_as_judge.py:73` 对 `adversarial` 与 `Cognitive` 传空字符串 `gold=""` |

---

<a id="c17-6"></a>
## 17.6 批判性评价与对主报告的落点启发

1. **对主报告 `1.1` 与 `2.5` 节的直接支撑**：
   - 提供了区分 **Level-1 显式事实** 与 **Level-2 隐式约束** 的清晰形式化定义（有效响应空间 $\mathcal{A}_c$），直接解释了为什么单纯依靠语义向量检索的记忆系统在“用户未直接复述历史词句、但当前诉求受前期状态/目标/习惯/忌口隐含约束”的场景下会严重失灵（`Mem0` 仅 `15.80%`，`A-Mem` 仅 `17.20%`）。
   - 为我们设计“**无字面重合的隐式线索—触发对（Zero-Lexical-Overlap Cue–Trigger）**”以及放弃单一字面 `EM/F1`、转向基于证据的**约束一致性 LLM Judge（三档事实判分 + 二值时序/拒答/认知感知判分）**提供了直接参考依据。
2. **自身局限与工程校准**：
   - `Cognitive` 类数据仅 401 条，且是先独立生成 2 轮 `cue` 再按时间戳硬插进 `LoCoMo` 两人日常闲聊中，缺少跨多轮渐进演化与状态反转（单条 `cue` 与原 `LoCoMo` 角色人物设定之间可能存在语义割裂）。
   - 开源版本 `utils.py` 中仍给 `Cognitive` 样本加了 `INSTRUCTION_COGNITIVE` 显式提示“请展示你记得先前的线索”，在真实端到端评测中若不去掉这段提示，模型得分还可能进一步下降；我们在复现评测时应统一使用无任务披露的自然对话续写提示。

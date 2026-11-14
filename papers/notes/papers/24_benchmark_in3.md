# 24. IN3（Intention-in-Interaction）：面向指令模糊度分级与主动消歧的基准及 Mistral-Interact（ACL 2024）

> **来源定位**：`papers/benchmark/IN3_2024.pdf`（arXiv: `2402.09205`，官方开源仓库：`papers/repos/Mistral-Interact/` → `HBX-hbx/Mistral-Interact`）  
> **作者机构**：Cheng Qian, Bingxiang He, Zhong Zhuang, Jia Deng, Yujia Qin, Xin Cong, Zhong Zhang, Jie Zhou, Yankai Lin, Zhiyuan Liu, Maosong Sun（清华大学 & 中国人民大学）  
> **核心定位**：指出既有 Agent 基准普遍假设用户首轮指令完全清晰（一旦指令模糊就会触发盲目规划和无效工具调用），提出 **IN3（Intention-in-Interaction）** 基准（`1,261` 训练 + `108` 测试任务，标注任务模糊性、缺失细节及 `Lv1/Lv2/Lv3` 三级重要度与候选选项），并基于 `IN3` 构造双 GPT-4 交互轨迹微调出轻量上游消歧模块 **`Mistral-Interact`**（7B），在不改动下游执行器（如 `XAgent`）的前提下将不必要子任务从 `22.22%` 降至 `1.85%`。

---

## 一、IN3 基准设计与三级缺失细节标注体系（`Sec 3.1`, `Table 1`）

```
[Step 1: 人类编写种子任务] ──► [Step 2: GPT-4 Self-Instruct 覆盖 200+ 领域扩展 1,369 条]
                                     │
                                     ▼
                           [Step 3: GPT-4 辅助 + 人工精标]
                             ├─ vague ∈ {True, False} (是否需要追问)
                             ├─ missing_details:
                             │     ├─ Lv3 (核心必需参数, 如“用户所在城市” — 缺则无法执行)
                             │     ├─ Lv2 (重要偏好条件, 如“最佳瑜伽馆评判标准”)
                             │     └─ Lv1 (次要补充细节)
                             └─ options: 每个缺失细节附带候选建议列表 (平均每条模糊任务 ~11 个选项)
```

| 统计维度（`Table 1`） | 训练集（`train.jsonl`） | 测试集（`test.jsonl`） |
| :--- | :---: | :---: |
| 总任务数（`Task`） | **1,261** | **108** |
| 模糊任务（`Vague`） / 清晰任务（`Clear`） | 1,012 / 249 | 95 / 13 |
| 覆盖任务类别数（`Categories`） | 250 | 50 |
| 标注缺失细节总数（`#MissingDetails`，均值） | 3,615（3.57/任务） | 350（3.68/任务） |
| 重要度分布 `Lv1 / Lv2 / Lv3`（%） | `15.44 / 67.75 / 16.81` | `9.14 / 72.29 / 18.57` |
| 候选选项总数（`#Options`，均值） | 11,523（11.39/任务） | 1,042（10.97/任务） |

---

## 二、先导失误分析与上游“意图缓冲器”架构（`Sec 3.2` & `Sec 4`）

### 2.1 先导测试揭示的三阶段典型失效（`Sec 3.2`, `Table 2`）

在 10 个代表性任务上测试 `LLaMA-2-7B-Chat`、`Mistral-7B-Instruct-v0.2` 与 `GPT-4`（满分 10 题与 24 个核心缺失细节）：
- **模糊度判断准确数**：`LLaMA-2` `6/10`，`Mistral-7B` `8/10`，`GPT-4` `9/10`；
- **必要追问命中率**：`LLaMA-2` `7/23`，`Mistral-7B` `7/8`（问得太少、过早跳去总结），`GPT-4` `16/24`；
- **三阶段病灶**：`LLaMA-2` 在“判断清晰指令时仍过度追问（`Over-Clarification`）”且单轮连珠炮式提问过多；`Mistral-7B` 容易追问不足而草率执行；甚至连强模型也可能在总结阶段凭空脑补未确认的参数或遗漏用户主动补充的约束。

### 2.2 `Mistral-Interact` 上游消歧缓冲架构（`Sec 4.1`–`4.2`）

将交互模块置于下游执行器 $f(\cdot)$ 上游作为“意图缓冲器”：$t \xrightarrow{\text{清晰直通 或 追问改写}} t_{\text{user}} \xrightarrow{} f(t_{\text{user}})$。训练数据由 `Assistant-GPT` 与 `User-GPT` 对话合成，包含四项关键设计：

1. **显式初始思考（`Explicit Initial Thought`）**：首轮先输出结构化判断（清晰/模糊 + 关键缺失细节清单 + 候选选项），再决定是否追问；若任务本身清晰，直接跳过对话输出 $t_{\text{user}} = t$；
2. **单轮单问 + 启发式选项（`Query with Options`）**：每轮只问 **1 个**问题并附带合理选项，降低用户认知负担，启发隐式偏好表达；
3. **多样化用户语气（`Diverse User Tones`）**：模拟“惜字如金型（`succinct`）”与“热情详述型（`passionate`）”两类回复风格，使训练样本翻倍；
4. **显式意图总结（`Explicit Intention Summary`）**：收集足够信息后，先在 Thought 中汇总所有确认条件与用户主动补充信息，再输出可直接交给下游 Agent 执行的清晰指令 $t_{\text{user}}$。

---

## 三、核心实验结果与指标体系（`Sec 5.1`–`5.2`, `Table 3`–`4`）

### 3.1 `IN3` 测试集交互理解全量指标（`Table 3`）

| 评测指标（`Sec 5.1.2`） | `Mistral-7B` | `LLaMA-2-7B` | `GPT-4` | **`Mistral-Interact`** |
| :--- | :---: | :---: | :---: | :---: |
| `Vagueness Judgement Accuracy (%)` $\uparrow$（清晰/模糊二分类） | 49.07 | 79.63 | 82.41 | **85.19** |
| `Missing Details Recover Rate - Lv3 (%)` $\uparrow$（核心细节） | 68.42 | 60.98 | **75.22** | 72.28 |
| `Missing Details Recover Rate - Lv2 (%)` $\uparrow$（重要偏好） | 56.94 | 38.76 | 63.14 | **67.08** |
| `Missing Details Recover Rate - Lv1 (%)` $\uparrow$（次要细节） | 23.08 | 28.92 | **37.50** | 27.94 |
| `Summary Intention Coverage Rate (%)` $\uparrow$（总结无遗漏） | 91.43 | 61.87 | **100.0** | 96.37 |
| `Options Presenting Rate (%)` $\uparrow$（提问附带选项比例） | 42.46 | 47.64 | 40.31 | **84.08** |
| `Options Reasonable Rate (%)` $\uparrow$（选项合理度） | **100.0** | 81.79 | **100.0** | 98.70 |
| `Average Provided Options`（平均每次给选项数） | 1.46 | 1.35 | 1.21 | 2.72 |
| `Average Inquired Missing Details`（总追问细节数） | 3.91 | 5.80 | 4.78 | 4.52 |
| `Average Conversation Rounds`（平均交互轮数） | 1.62 | 3.02 | 2.69 | 4.15 |
| `Average Inquired Details Per Round` $\downarrow$（每轮追问个数） | 2.80 | 2.49 | 2.31 | **1.26** |

- **核心结论**：`Mistral-Interact`（7B）在**模糊度判断准确率（`85.19%`）**、**Lv2 重要偏好召回（`67.08%`）**、**附带选项率（`84.08%`）**与**单轮克制提问（每轮仅 `1.26` 问）**上全面超越 `GPT-4`，同时在 `Lv3` 核心缺失细节召回（`72.28%`）与总结覆盖率（`96.37%`）上逼近 `GPT-4`。

### 3.2 下游执行增益验证（`Sec 5.2`, `Table 4`, 集成进 `XAgent`）

在 10 个真实需外部工具（搜索/代码/命令行/文件系统）的模糊任务上对比直接交给 `XAgent(GPT-4)` 执行 vs. 先经 `Mistral-Interact` 澄清后再执行：

| 执行配置 | 不必要子任务 / 里程碑（`%`）$\downarrow$ | 过于宽泛的子任务 / 里程碑（`%`）$\downarrow$ | 每子任务 / 里程碑平均工具调用次数 $\downarrow$ |
| :--- | :---: | :---: | :---: |
| `Vague Task (w/o Mistral-Interact)` | `22.22 / 21.48` | `22.22 / 12.08` | `5.22 / 2.21` |
| **`Detailed Task (w/ Mistral-Interact)`** | **`1.85 / 7.81`** | **`0.00 / 0.78`** | **`4.79 / 2.02`** |

---

## 四、论文与官方仓库（`HBX-hbx/Mistral-Interact`）核查差异

| 维度 | 论文描述（`2402.09205`） | 仓库实测（`papers/repos/Mistral-Interact/`） |
| :--- | :--- | :--- |
| **仓库地址** | 首页脚注明确给出 `HBX-hbx/Mistral-Interact` | 原清单误记为 `Cleanarken/IN3`（GitHub 404），实际仓库为 `HBX-hbx/Mistral-Interact` |
| **数据统计** | `Table 1` 报告训练集 `1,261`（`1,012` 模糊 / `249` 清晰）、测试集 `108`（`95 / 13`） | 实测 `data/IN3/train.jsonl` 与 `test.jsonl` 行数及 `vague` 布尔计数与 `Table 1` 100% 一致 |
| **完整产物开放度** | 包含训练对话与模型评测记录 | 仓库同时开放了 `data/interactions/interaction_data_{train,test}.jsonl`、4 个基线模型在测试集上的全量对话轨迹 `data/user_interaction_records/` 及 `src/sft.py` |

---

## 五、对我们主报告与联接 Agent 项目的落地启发

1. **缺失槽位必须按 `Lv3 / Lv2 / Lv1` 分级，区别对待“未澄清直接执行”与“冗余追问”**：对于网元保障中缺则无法下发的核心必需槽位（`Lv3`，如业务应用名或目标时长），禁止模型自行脑补参数直接调用工具（`Premature Execution`）；而对于清晰指令或已有个人画像默认值的次要偏好（`Lv1`），应当直接执行或给默认值，避免冗余追问（`Over-Clarification`）。
2. **采用“上游意图缓冲器 + 单轮单问带选项”交互策略**：在联接 Agent 决策流中把“模糊度判断 → 显式思考缺少哪些 `Lv3/Lv2` 槽位 → 单轮最多问 1~2 个关键参数并附候选选项 → 汇总成清晰可执行意图”作为显式前置步骤，可大幅削减下游网元 API 的无效试错调用。

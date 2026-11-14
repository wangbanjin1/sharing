# MediQ：信息残缺下的主动追问与置信度拒答（Abstention）交互基准

- **标题**：*MediQ: Question-Asking LLMs and a Benchmark for Reliable Interactive Clinical Reasoning* (NeurIPS 2024, arXiv:2406.00922)
- **作者 / 机构**：Shuyue Stella Li, Vidhisha Balachandran, Shangbin Feng, Jonathan S. Ilgen, Emma Pierson, Pang Wei Koh, Yulia Tsvetkov（华盛顿大学 UW、CMU、Cornell Tech、AI2）
- **PDF**：`papers/benchmark/MediQ_2024.pdf`（源码：`papers/benchmark/2406.00922/source/neurips_camera_ready.tex`）
- **配套仓库**：`https://github.com/stellalisy/mediQ`（已克隆至 `papers/repos/mediQ`，含 `data/all_dev_good.jsonl` 与 `data/all_craft_md.jsonl`）
- **核心定位**：将单轮静态医疗 QA（`MedQA` / `Craft-MD`）重构为信息残缺的交互式问诊：首轮仅提供“年龄 + 性别 + 主诉”，其余 $N$ 条原子事实隐藏在 **Patient 模拟器** 中按问释放；验证了直接提示 LLM 追问反而掉点 **11.3%**，必须通过**独立置信度拒答（Abstention）模块 + 理由生成（RG）+ 自洽投票（SC）** 才能抑制未达置信度抢跑作答。

---

## 一、核心背景与研究痛点

通用大模型在对齐训练时被激励“对任何问题尽量给出完整回答”，在信息残缺的高风险决策场景中极易**未澄清直接执行 / 抢跑盲猜（Premature Execution）**：
1. 现有静态基准（如 `MedQA`）首轮就把全部检查单与病史塞给模型，完全绕开了真实场景“用户不懂得主动汇报全部必要细节，需助手逐层追问”的核心能力（`Sec. 1`, `Fig. 1`）；
2. 直接在 Prompt 里允许模型“可以提问或直接作答（`Basic` 设定）”时，模型要么压根不提问直接瞎猜，要么重复追问无效问题并被冗长对话格式带偏，准确率反而比**不让提问的单轮基线（`Initial`）更低**（`Sec. 4.2`）。

---

## 二、双端系统架构与原子事实门控（`Sec. 2`, `Fig. 2–3`）

```text
  [完整病历 K = {k_0, k_1, ..., k_n}]
           │
           ├──► 首轮仅暴露 k_0 (年龄/性别/主诉) ──► Expert 系统 (MediQ-Expert 五步解耦流水线):
           │                                         1. Initial Assessment: 梳理症状与潜在知识缺口
           │                                         2. Abstention Module: 评估置信度 (Numeric / Binary / 1-5 Scale)
           │                                            + 理由生成 (RG) + 自洽 (SC=3) ──► 达阈值 → Step 5 作答
           │                                                                            ──► 未达阈值 → Step 3 追问
           │                                         3. Question Generation: 生成单一原子追问 q_t
           │                                         4. Information Integration: 追加问答对更新 K_t
           │
           └──► Patient 模拟器 (Fact-Select, Sec. 2.1 & patient.py:88-105):
                   • 先将完整病历拆分为独立原子事实列表 atomic_facts
                   • 仅原样返回匹配专家当前问题 q_t 的事实 r_t; 若病历未记载则固定拒答（严禁编造）
```

### 1. Patient 模拟器三种模式实测对比（`Sec. 4.1`, `Table 1`）
| Patient 模式 | Factuality (%) | Relevance (%) | 行为特征（`Sec. 4.1`） |
| :--- | :---: | :---: | :--- |
| **Direct** | 55.9 | 75.5 | 无约束时常只回 `Yes/No`，漏掉关键原子事实 |
| **Instruct** | 62.8 | 78.6 | 会自行推理脑补病历外结论 |
| **Fact-Select** | **89.1** | **79.9** | 先拆分原子事实再原样摘取，显著抑制模拟器剧透与幻觉 |

### 2. Expert 拒答策略演进（`Sec. 2.2.2`）
- **Basic（隐式决策）**：不拆模块，直接让 LLM 选择输出问题或答案选项；
- **Numerical / Binary / 5-Point Scale**：显式探测模型置信度（`1-5` 分量表最稳定），达到网格搜索阈值后才放行作答；
- **Rationale Generation (RG) + Self-Consistency (SC=3)**：先生成“当前缺少哪些关键鉴别证据”的推理理由再评定置信度（ECE 校准误差从 `2.9` 降至 `2.1`），并把理由传给提问器生成更精准的问题（`Sec. 5.2`, `Fig. 6`）。

---

## 三、核心实验结果（对照 `Table 2` 与 `Sec. 4.2–4.3` 核实）

在 **`iMedQA`**（1,272 条测试）与 **`iCraft-MD`**（140 条皮肤科病例）上的准确率对比（%）：

| 数据集 | 模型 | Full (全量上界) | Initial (仅首诉单轮) | None (无病历) | Interactive `Basic` | Interactive `Best` (Scale+RG+SC) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **iMedQA** | Llama-3-8B | 68.1 ± 1.3 | 52.0 ± 1.4 | 40.4 ± 1.4 | 33.0 ± 1.3 | 45.8 ± 1.4 |
| | **Llama-3-70B** | 84.7 ± 1.0 | 58.5 ± 1.4 | 46.3 ± 1.4 | 55.1 ± 1.3 | **60.9 ± 1.4** |
| | GPT-3.5 | 55.8 ± 1.4 | 45.6 ± 1.4 | 36.7 ± 1.4 | 42.2 ± 1.3 | **50.2 ± 1.4** |
| | **GPT-4** | 79.7 ± 1.1 | 54.5 ± 1.4 | 42.2 ± 1.4 | 55.4 ± 1.3 | **66.1 ± 1.3** |
| **iCraft-MD** | Llama-3-8B | 76.4 ± 3.6 | 51.4 ± 4.2 | 29.3 ± 3.8 | 42.9 ± 4.2 | 50.0 ± 4.2 |
| | **Llama-3-70B** | 82.1 ± 3.2 | 60.7 ± 4.1 | 52.9 ± 4.2 | 62.1 ± 4.1 | **72.1 ± 3.8** |
| | GPT-3.5 | 82.1 ± 3.2 | 53.6 ± 4.2 | 29.3 ± 3.8 | 45.0 ± 4.2 | **59.3 ± 4.2** |
| | **GPT-4** | 91.4 ± 2.4 | 67.9 ± 3.9 | 43.6 ± 3.7 | 73.6 ± 3.7 | **84.3 ± 3.1** |

- **四大关键实证结论（`Sec. 4.2–5.2`）**：
  1. **不加控制的交互反而帮倒忙**：`Basic` 交互设置相对 `Initial` 非交互平均掉点 **`11.3%`**（如 `Llama-3-8B` 在 `iMedQA` 从 `52.0%` 暴跌至 `33.0%`），因为大多数轮次模型根本不提问直接抢答，或者陷入无效重复提问；
  2. **置信度拒答 + 理由生成显著挽回差距**：`Scale + RG + SC(3)` 相对 `Basic` 提升 **`+22.3%`**，相对 `Initial` 提升 **`+12.1%`**（如 `GPT-4` 在 `iMedQA` 达 `66.1%`、在 `iCraft-MD` 达 `84.3%`），但距离 `Full` 上界仍仅闭合约 **`51.2%`** 的差距；
  3. **自洽投票不能单独使用（`Fig. 4`）**：若不配合 `RG`，单纯对置信度做 `SC` 投票反而略微掉点；
  4. **上下文去重与段落化重排提效（`Sec. 5.1`, `Fig. 5`）**：剔除“病历无法回答的无效追问（`Relevant`）”与“重复追问（`Unique`）”，并将对话历史整理为陈述段落格式（`Unique-Para`），仅凭这步预处理即可让 `Basic` 提升 **`+5.7 pp`**。

---

## 四、配套代码核查结论（`papers/repos/mediQ`）

| 核查项 | 论文描述 (`Sec. 2.1, 4.1`) | 代码仓实测 (`src/patient.py`, `src/expert.py`, `data/`) | 差异说明 |
| :--- | :--- | :--- | :--- |
| 数据集发布 | 转换 `MedQA` dev 1,272 与 `Craft-MD` 140 | `data/all_dev_good.jsonl` 与 `data/all_craft_md.jsonl` 完整在库 | 完全一致 |
| `FactSelectPatient` | 将病历拆为原子事实并按问提取 | `src/patient.py:88-105` 实现了原子事实缓存 `self.facts`，未匹配时固定回复拒答串 | 完全一致 |
| `DirectPatient` 输入范围 | 论文称访问完整患者病历 | `src/patient.py:73` 实际传给模型的是 `self.initial_info` 而非 `self.context_para` | `InstructPatient`（`line 82`）和 `FactSelectPatient`（`line 93`）正常使用全量 `self.context_para` |

---

## 五、对我们主报告与业务系统的落地启发

1. **信息残缺与“原子事实门控”用户模拟器（对应主报告 1.1 方向四）**：
   - 首轮只给用户 **1 句模糊主诉（对应 $k_0$）**，把其余 **$N$ 条背景约束（如套餐档位、终端类型、加速时段、预算上限）拆成独立原子事实池** 锁在模拟器内部；模拟器采用 `Fact-Select` 机制——**问到哪条放哪条、未问绝不剧透、不在事实池则明确回答“不知道/无要求”**，彻底封死单轮直接猜参数过关的漏洞。
2. **慢路径置信度拒答（Abstention）与工作记忆压缩（对应主报告快慢路径设计）**：
   - 将“**是否够信息执行**（Abstention）”与“**问什么问题**（Question Gen）”解耦：慢路径先生成“缺失槽位/置信度理由（RG）”再打 1–5 档置信度分，未达阈值禁止调用写接口；
   - 长期多轮追问后，将冗长问答日志按 MediQ `Unique-Para` 思路**去重并压缩为结构化事实陈述段落**喂给下游决策，避免无效重复问答分散注意力。

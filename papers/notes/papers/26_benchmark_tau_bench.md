# 26. $\tau$-bench：领域数据库 + API + 业务规程约束下的 Tool-Agent-User 交互与 $\text{Pass}^k$ 基准（ICLR 2025）

> **来源定位**：`papers/benchmark/Tau_Bench_2024.pdf`（arXiv: `2406.12045`，ICLR 2025，官方开源仓库：`papers/repos/tau-bench/` → `sierra-research/tau-bench`）  
> **作者机构**：Shunyu Yao, Noah Shinn, Pedram Razavi, Karthik Narasimhan（Sierra Research & 普林斯顿大学）  
> **核心定位**：指出传统对话与工具基准要么静态单轮、要么缺乏真实数据库状态持久化与业务规程（Domain Policy）约束，提出 **$\tau$-bench（Tool-Agent-User Interaction）**；以“隐藏结构化数据库 + Python API 工具 + Markdown 业务规程 + LLM 模拟用户”四位一体构造 $\tau$-retail（115 任务）与 $\tau$-airline（50 任务），并提出度量**多次独立运行稳定性**的 **$\text{pass}^k$** 指标（与探索型的 $\text{pass}@k$ 形成鲜明对比）。

---

## 一、形式化建模与系统架构（`Sec 3`, `Fig. 1`）

```
[Agent] (可见: 领域业务规程 Markdown + API 工具 Schema + 对话历史; 不可见: 数据库内容 & Task GT)
   ├──► 调用 API 工具 a_db ∈ A_db ──► [确定性 Python DB 引擎 T_db] ──► 返回观测 o_db / 错误检查
   └──► 回复用户消息 a_user ∈ A_user ─► [LLM 用户模拟器 T_user (gpt-4-0613)] ──► 返回 o_user 或 "###STOP###"
                                          │
                                          ▼ (回合结束, 最多 30 步动作)
                      [确定性规则判分: r = r_action × r_output ∈ {0, 1}]
                        ├─ r_action: 终态 DB 哈希 == 重放 GT 动作序列后的 DB 哈希
                        └─ r_output: Agent 对用户的回复文本覆盖全部必需输出子串 (outputs)
```

- **POMDP 状态分解（`Sec 3`）**：$\mathcal{S} = \mathcal{S}_{db} \otimes \mathcal{S}_{user}$，$\mathcal{A} = \mathcal{A}_{db} \cup \mathcal{A}_{user}$，$\mathcal{O} = \mathcal{O}_{db} \cup \mathcal{O}_{user}$。用户模拟器**看不见** Agent 与 API 之间的工具调用过程，Agent 必须主动用自然语言向用户核对身份、偏好、确认操作并汇报结果。
- **规则约束双层防线**：部分规程硬编码在 API 校验里（如支付方式不存在会返回 `Error: payment not found`），另一部分（如不同会员等级/舱位对应的免费托运行李件数、修改订单只能批量一次调用）仅写在业务规程文档中，考验 Agent 的规程阅读与推理执行能力。

---

## 二、$\text{pass}^k$ 稳定性指标与双领域设计（`Sec 3`–`4`, `Table 1`）

### 2.1 $\text{pass}^k$ 对比 $\text{pass}@k$（`Sec 3`）

代码生成常用 $\text{pass}@k$（$k$ 次尝试至少成功 1 次）；真实客服与网元配置场景要求**每次都做对**，因此定义 **$\text{pass}^k$** 为同一任务 $n$ 次独立随机运行中任意抽出 $k$ 次**全部成功**的概率无偏估计：
$$\text{pass}^k = \mathbb{E}_{\text{task}}\left[\frac{\binom{c}{k}}{\binom{n}{k}}\right], \qquad \text{pass}@k = 1 - \mathbb{E}_{\text{task}}\left[\frac{\binom{n-c}{k}}{\binom{n}{k}}\right]$$
其中 $c$ 为 $n$ 次运行中获得 $r=1$ 的成功次数。默认主指标为 $\text{pass}^1 = \mathbb{E}[c/n]$。

### 2.2 两个核心评测域统计（`Table 1`）

| 域 | 数据库规模（Stage II GPT-4 合成） | API 工具（写 / 读） | 人工校验任务数 | 核心难点 |
| :--- | :--- | :---: | :---: | :--- |
| **$\tau$-retail** | 500 用户 / 50 商品 / 1,000 订单 | `7 write` / `8 non-write` | **115** | 商品规格组合匹配、已送达订单仅能退换一次且需收集全量列表 |
| **$\tau$-airline** | 500 用户 / 300 航班（20 美国城市）/ 2,000 预订 | `6 write` / `7 non-write` | **50** | 会员等级/舱位/支付方式组合/改签退票与行李额多跳规程推理 |

> **Stage III 唯一终态校验（`Sec 4`）**：人工先写用户指令，再用 `gpt-4-turbo` 跑 `>40` 次试运行并排查零成功或歧义任务，迭代收紧指令直至确保**在规程约束下只存在唯一合法终态数据库**，从而彻底摆脱昂贵的主观 LLM-Judge。

---

## 三、核心实验结果与三大失败归因（`Sec 5`, `Table 2`–`3`, `Fig. 2`–`4`）

### 3.1 12 个模型 Function Calling 主表（`Table 2`, $\text{pass}^1$ `%`，Agent `T=0.0`，User `T=1.0`，至少 3 次试验）

| 模型 | $\tau$-retail | $\tau$-airline | 平均 Avg. |
| :--- | :---: | :---: | :---: |
| **`gpt-4o`** | **61.2** | **35.2** | **48.2** |
| `gpt-4-turbo` | 57.7 | 32.4 | 45.1 |
| `gpt-4-32k` | 56.5 | 33.0 | 44.8 |
| `claude-3-opus` | 44.2 | 34.7 | 39.5 |
| `claude-3-sonnet` | 26.3 | 27.6 | 27.0 |
| `mistral-large` | 30.7 | 22.4 | 26.6 |
| `mixtral-8x22b`（开源） | 17.7 | 31.6 | 24.7 |
| `gemini-1.5-flash` | 17.4 | 26.0 | 21.7 |
| `gemini-1.5-pro` | 21.7 | 14.0 | 17.9 |
| `claude-3-haiku` | 19.0 | 14.4 | 16.7 |
| `gpt-3.5-turbo` | 20.0 | 10.8 | 15.4 |
| `meta-llama-3-70B`（开源） | 14.8 | 14.4 | 14.6 |

### 3.2 关键机制发现与失败拆解（`Sec 5.1`–`5.2`）

1. **一致性严重不足（`Fig. 2`）**：即使是排名第一的 `gpt-4o`（$\tau$-retail $\text{pass}^1 > 60\%$），到 **$\text{pass}^8$ 时成功率直接跌破 `25%`**。
2. **原生 Function Calling 优于纯文本 ReAct/Act（`Fig. 2`）**；而额外给 FC 模型提供 `think` 空工具并未带来稳定增益。
3. **`gpt-4o` 失败案例拆解（115 条轨迹中 40 条失败，剔除 4 条指令笔误后分析 36 条，`Sec 5.2`）**：
   - **参数推理错误或关键信息遗漏/算错（~55%）**：工具选对了但传错复杂商品规格 ID、漏报追踪号或算错总价；弱模型更易直接幻觉编造不存在的 ID（每任务幻觉 ID 次数：`gpt-4o FC 0.46` 次对比 `gpt-3.5 FC 2.08` 次 / `Act 6.34` 次）。
   - **违背领域规程决策错误（25%）**：如规程要求“修改/换货只能调用一次，必须把多件商品放进同一列表”，`gpt-4o` 却先换了一件导致第二件无法再换；去掉 `domain policy` 后（`Table 3`），`gpt-4o` 在 $\tau$-retail 仅小降 `61.2 → 56.8`，在规则复杂的 $\tau$-airline 则暴跌 **`33.2 → 10.8`**（`-22.4%`）。
   - **复合多请求漏执行（19%，`Fig. 4`）**：任务包含多个数据库写动作时，模型常遗漏对话早期需求或只处理第一笔符合条件的订单就提前收工。

---

## 四、论文与官方仓库（`sierra-research/tau-bench`）源码核查差异

| 维度 | 论文描述（`2406.12045`） | 源码实测（`papers/repos/tau-bench/`） |
| :--- | :--- | :--- |
| **终态判分实现** | 比较终态数据库一致性和回复必需信息 | `tau_bench/envs/base.py:121-164` 用 `sha256(str(to_hashable(self.data)))` 比对全库哈希；`outputs` 判分为去掉英文逗号 `,` 后的大小写不敏感子串匹配（`base.py:153-154`） |
| **源码已知细节差异** | 同时返回动作与输出奖励信息 | `base.py:162` 当 `len(task.outputs) > 0` 时 `info = RewardOutputInfo(...)` 会覆盖 `info = RewardActionInfo(...)`（不影响 `reward` 乘积本身） |
| **版本演进提示** | 发布初版 `retail` 与 `airline` | `README.md:3-5` 明确提示本仓库任务已归档并存在部分旧任务缺陷，后续修复与新增 `banking` / `voice` 见 `tau2-bench` 与 `tau3-bench` |

---

## 五、对我们主报告与联接 Agent 项目的落地启发

1. **直接复用 `DB 状态哈希 + 业务规程约束 + Pass^k` 评测范式**：网元保障 Agent 本质上也是“隐藏网元配置库 + 网元控制 API + 运营业务规程 + 用户多轮交互”的 POMDP；用终态配置快照比对（`r_action`）+ 回复关键信息覆盖（`r_output`）+ 多次运行的 **$\text{pass}^3$**（而非单次运气 `pass@1`）才能真实暴露网元下发的一致性风险。
2. **严防“复合请求漏单”与“规程依赖盲区”**：参考 $\tau$-bench 的三类失败归因，在联接 Agent 中应对“一次修改多个业务/多个时间窗”做显式完成度核查（Checklist），并将核心套餐限额/互斥规则同时做**工具参数级强校验**与**规程显式提示**，不可只靠模型记忆软提示。

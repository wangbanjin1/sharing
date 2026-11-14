# 23. IntentDelta：面向动态演变用户意图的人工多轮轨迹与优先级权衡基准

> **来源定位**：`papers/benchmark/IntentDelta_2026.pdf`（arXiv: `2610.33806`，暂无随附开源代码仓链接）  
> **作者机构**：Jieyu Zhou, Zijian Wang（佐治亚理工学院）、Yun Wang（微软亚洲研究院）  
> **核心定位**：针对“现有改口基准多为合成交互且默认所有约束平等”的盲区，构建包含 **638 条人工交叉核验轨迹、3,766 轮对话**（覆盖 `WebShop` 与 `TravelPlanner`）的 **IntentDelta**；每轮显式标注“累计有效意图状态（含 `must-have / preferred / optional` 三级优先级）”与“人工参考执行动作”，并引入 **Intention Recovery**、**Action Score** 及 **Obsolete Retention（作废旧约束残留率）**，揭示 11 个前沿模型在长程保留旧约束与区分软硬约束上的系统性失守。

---

## 一、形式化建模：双端耦合决策与意图演化触发条件（`Sec 3.1`–`3.2`）

```
[用户进程 MDP: s_t^U = (I_t, C_t)]
   ├─ 当前有效意图 I_t: { (constraint, value, scope, priority ∈ {must-have, preferred, optional}) }
   ├─ 交互上下文 C_t:   环境观测 O_env + 人类参考结果 + Agent 上轮响应
   └─ 触发意图演化 I_t → I_{t+1} 的两类现实条件 (Sec 3.2):
        ├─ 1. 可行性受挫 (Feasibility-driven): 如“高性能+低预算”无解 → 放宽预算或妥协次要指标
        └─ 2. 偏好驱动改口 (Preference-driven): 看到候选方案后权衡取舍 → 把“性能”降级为“便携/续航”优先
   │
   ▼ 用户发出自然语言话语 u_t ∈ A_U
[Agent 进程 POMDP: (S_A, A_A, O_A, T_A)]
   └─ 每轮需同时输出: (1) 预测当前完整有效意图状态 I_t^pred  (2) 执行环境动作并产出结果
```

### 1.1 四类意图变更操作与三级优先级（`Sec 3.2`, `Table 2`）

| 维度 | 类别 | WebShop 占比 | TravelPlanner 占比 | 含义说明 |
| :--- | :--- | :---: | :---: | :--- |
| **变更操作**（`% of events`） | `Add`（新增约束） | 20.4% | 37.3% | 引入新需求条件 |
| | `Relax`（放宽约束） | 18.0% | 8.3% | 放宽原有数值/范围限制（如上调预算） |
| | `Override`（覆盖改口） | 15.0% | 8.5% | 用新值直接取代同一槽位的旧要求 |
| | `Reprioritize`（调整优先级） | **46.6%** | **46.0%** | 仅调整约束在 `must-have / preferred / optional` 中的权重层级 |
| **触发动因**（`% of change turns`） | `Feasibility-driven` | **45.1%** | 26.8% | 环境无解倒逼改口 |
| | `Preference-driven` | 54.9% | **73.2%** | 浏览候选方案后的主观偏好迁移 |
| **变更复杂度**（`% of change turns`） | `Compound changes` | **66.5%** | **81.5%** | **单轮同时触发多项约束修改**（非单一单槽改口） |

> **核心数据集规模与质量保障（`Sec 4.2`–`4.3`）**：人工共构造 **638 条轨迹**（`TravelPlanner` 304 条 / 1,946 轮，`WebShop` 334 条 / 1,820 轮），每条轨迹耗时 5–10 分钟，长度集中在 4–7 轮。全量经第二位作者交叉复核，另抽取 **20%（128 条轨迹）**由外部标注员独立重标，达到 **97% 一致率**；`GPT-5.6 Sol` 自动裁判抽样 100 条人工复核达到 **95% 一致率**（`Sec 5.1`）。

---

## 二、两级核心评测指标体系（`Sec 3.3` & `Appendix F`）

### 2.1 意图恢复级指标（Intention-Level）

每轮将模型预测约束原子与标准累计有效约束做语义对齐：
1. **Detection（召回率）**：$\frac{\text{\#detected gold constraints}}{\text{\#gold constraints}}$
2. **Content Accuracy**：$\frac{\text{\#correct contents}}{\text{\#detected constraints}}$（值与作用域正确）
3. **Priority Accuracy**：$\frac{\text{\#correct priorities}}{\text{\#detected constraints}}$（准确区分 `must-have / preferred / optional`）
4. **Intention Recovery（主指标）**：$\frac{\text{\#fully recovered constraints}}{\text{\#gold constraints}}$（内容与优先级**同时**正确）
5. **补充诊断（`Appendix F`, `Table 6`）**：
   - **Precision**：预测约束中命中有效金标准的比例；
   - **Obsolete Retention（作废旧约束残留率，$\downarrow$）**：用户执行 `Override / Relax / Remove` 后，模型在下一轮仍原样保留已被取代旧约束的比例。

### 2.2 动作执行级指标（Action-Level, `Eq. 1`）

软约束满足**不能**掩盖硬约束失败（`Sec 3.3`）：
- **Hard Success ($G_t$)**：若任务可行（`feasible`），需满足全部 $n_M$ 条 `must-have` 约束（$\mathbb{1}[M_a = n_M]$）；若不可行（`infeasible`），需至少满足不少于人类参考执行的硬约束数（$\mathbb{1}[M_a \ge M_g]$）。
- **Action Score**：为 `preferred` 赋权重 `2`、`optional` 赋权重 `1`，计算 $S_a = 2P_a + O_a$ 与 $S_g = 2P_g + O_g$：
  $$\text{ActionScore} = G_t \cdot \min\!\left(1,\, \frac{S_a}{S_g}\right)$$
  （当 $S_g = 0$ 时 $\text{ActionScore} = G_t$。`Table 5` 敏感性检验表明，更换线性/非线性权重比后模型排名 Kendall's $\tau \ge 0.964$。）

---

## 三、全量实验结果与失效归因（`Sec 5`, `Table 3` & `Table 6`）

所有 11 个模型均在统一 `ReAct` 框架下评测，每轮回放相同的人工话语序列并要求同步输出当前完整有效意图及环境动作（`Sec 5.1`）：

| 模型 | TravelPlanner Det.↑ | TravelPlanner Rec.↑ | TravelPlanner Hard Succ.↑ | TravelPlanner Action Score↑ | WebShop Det.↑ | WebShop Rec.↑ | WebShop Hard Succ.↑ | WebShop Action Score↑ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `gpt-5.6-sol` | 70.4 | 38.4 | 52.3 | 49.6 | 92.2 | 50.6 | **58.6** | **49.0** |
| `gpt-5.6-luna` | **72.1** | 38.2 | 46.5 | 42.3 | 91.6 | 49.4 | 54.6 | 45.1 |
| `claude-opus-4.8` | 68.4 | 37.3 | 47.0 | 42.3 | 89.2 | **52.0** | 52.0 | 41.9 |
| `claude-sonnet-5` | 70.8 | **39.1** | 55.6 | 51.6 | 90.6 | 50.6 | 52.0 | 42.7 |
| `deepseek-r1` | 43.1 | 23.4 | 36.2 | 28.9 | 66.0 | 35.6 | 48.0 | 38.6 |
| `grok-4.6` | 68.4 | 37.3 | **60.3** | **57.1** | **92.8** | 51.4 | 58.2 | 47.2 |
| `kimi-k2.5` | 69.6 | 36.2 | 31.9 | 26.6 | 89.0 | 49.3 | 52.1 | 42.9 |
| `minimax-m2.5` | 58.2 | 31.2 | 25.4 | 21.6 | 75.1 | 40.1 | 49.9 | 40.5 |
| `nova-pro` | 49.4 | 25.6 | 10.0 | 6.6 | 65.9 | 32.5 | 41.9 | 34.0 |
| `qwen3-235b` | 57.9 | 30.4 | 17.2 | 13.3 | 80.8 | 40.4 | 47.6 | 38.8 |
| `qwen3-32b` | 53.0 | 27.5 | 11.9 | 7.7 | 80.5 | 40.1 | 37.8 | 30.7 |
| **11 模型均值** | **61.9** | **33.1** | **35.8** | **31.6** | **83.1** | **44.7** | **50.2** | **41.0** |

### 核心诊断发现（`Sec 5.2`–`5.3`, `Fig. 3`, `Table 6`）

1. **意图追踪与执行解耦**：“识别最准的模型”与“执行最好的模型”并不一致（TravelPlanner 中 `Claude Sonnet 5` Intention Recovery 最高 `39.1%`，但 `Grok 4.6` Action Score 最高 `57.1%`；WebShop 中 `Claude Opus 4.8` Recovery 最高 `52.0%`，而 `GPT-5.6 Sol` Action Score 最高 `49.0%`），说明“记对意图”到“在复杂环境中按优先级权衡落地”之间存在显著鸿沟。
2. **软硬优先级辨别是最大瓶颈**：虽然 `Content Accuracy` 分别达 `88.1%`（TravelPlanner）和 `83.7%`（WebShop），但 `Priority Accuracy` 仅 **`58.9%`** 和 **`62.8%`**，直接拖累 `Intention Recovery` 跌至 `33.1%` 和 `44.7%`。
3. **跨轮旧约束遗忘断崖（`Fig. 3`）**：未在本轮改动的延续约束随轮次推移急剧丢失——引入 `1 轮 → 2–3 轮 → 4+ 轮` 后，TravelPlanner 恢复率从 **`58.7% → 34.8% → 31.6%`**，WebShop 从 **`63.1% → 32.7% → 27.6%`**（全部 11 个模型一致单调下滑）。
4. **作废旧约束残留率（`Table 6`）**：11 模型平均 `Precision` 为 `54.4%`（TravelPlanner）和 `84.5%`（WebShop），但 **Obsolete Retention（作废旧约束残留率）分别高达 `14.0%` 与 `13.8%`**，证明模型常把已被 `Override/Relax` 推翻的旧要求继续当作有效约束执行。

---

## 四、对我们主报告与联接 Agent 项目的落地启发

1. **明确多轮改口的四类操作与“复合改口”常态**：网元保障对话绝不只是简单的“把 100Mbps 改成 200Mbps（`Override`）”，真实用户常因“当前套餐不支持百兆上行（`Feasibility-driven`）”或“看到价位后改变想法（`Preference-driven`）”而在同一轮里同时放宽预算、替换应用并调整保障等级优先级（`Compound changes` 占 66%–81%）。
2. **引入三级约束权重与 `Obsolete Retention` 红线指标**：在联接 Agent 的记忆状态与工作记忆槽位评测中，应区分**硬性业务约束（`must-have`，如不得超套餐上限/指定会议时段）**与**软偏好（`preferred/optional`，如尽量低时延/尽量少占用带宽）**，严守“软偏好不能抵消硬约束失败”的 `Hard Success × Soft Ratio` 判分原则，并直接监测 **Obsolete Retention（旧配置残留率）** 与 **跨 4+ 轮延续约束遗忘率**。
3. **工作记忆显式状态追踪的必要性**：既然前沿大模型在 4 轮后延续约束恢复率普遍跌破 32%，仅靠把历史对话全文塞进上下文窗口无法守住复杂多轮意图状态，必须在每轮维护显式的结构化工作记忆快照（Working Memory Snapshot），并对 `Override / Relax / Remove` 做确定性状态覆写与作废标记。

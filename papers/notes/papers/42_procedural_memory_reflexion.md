# 补充-1：Reflexion — 基于语言自我反思与情景记忆滑窗的强化学习框架

> **对应报告位置**：`3.3.3 节`（程序/经验记忆演进起点：从早期单任务失败反思滑窗 `Reflexion`，演进到跨任务成败双源蒸馏 `ReasoningBank` 与 `REM`）  
> **原文与源码**：
> - **论文**：`D:\coding\sharing\papers\procedural_memory\Reflexion_2023.pdf` / arXiv `2303.11366v4`（Noah Shinn, Federico Cassano, Edward Berman, Ashwin Gopinath, Karthik Narasimhan, Shunyu Yao，NeurIPS 2023）；LaTeX 转 Markdown 全文见 `D:\coding\sharing\papers\procedural_memory\2303.11366\2303.11366.md`  
> - **官方仓库**：`D:\coding\sharing\papers\repos\reflexion`（`https://github.com/noahshinn024/reflexion`，涵盖 `alfworld_runs/`、`hotpotqa_runs/`、`programming_runs/`、`webshop_runs/`）

---

## 1. 核心架构：三角色闭环与“语义梯度”（Sec. 3, Alg. 1）

Reflexion 提出在不更新大模型权重的前提下，通过自然语言自我反思形成**语义梯度（Semantic Gradient）**，并写入持久化的情景记忆缓冲区 `mem` 中指导后续试验：

```text
  ┌──────────────────┐   生成轨迹 τ_t   ┌──────────────────────┐
  │ Actor (M_a)      │ ───────────────► │ Evaluator (M_e)      │
  │ π_θ(a_i | s_i),  │                  │ EM / 启发式 / 自测   │
  │ θ = {M_a, mem}   │                  └──────────┬───────────┘
  └────────▲─────────┘                             │ 标量/二值反馈 r_t
           │                                       ▼
           │ 注入上下文 mem ← mem ⊕ sr_t  ┌──────────────────────┐
           └────────────────────────────  │ Self-Reflection      │
             (|mem| ≤ Ω, Ω ∈ {1, 3})      │ (M_sr): 定位错因+改写 │
                                          └──────────────────────┘
```

- **三核心模块**（`2303.11366.md` Sec. 3）：
  1. **Actor ($M_a$)**：基于 CoT 或 ReAct 生成动作与文本，策略条件同时包含短期记忆（当前轨迹历史）与长期记忆 `mem`。
  2. **Evaluator ($M_e$)**：依据任务域分别采用三种评估器：推理题用 **Exact Match (EM)**、序列决策用**启发式规则 + LLM 二分类自评**、编程任务用**自生成单元测试套件**（最多采样 `n = 6` 个 AST 校验合法的单测）。
  3. **Self-Reflection ($M_{sr}$)**：将稀疏的二值/标量奖惩 $\{ \tau_t, r_t \}$ 放大为第一人称诊断与纠错计划 $sr_t$，追加至 `mem`。受上下文长度限制，**`mem` 本质上是定长滑动窗口**（ALFWorld / HotPotQA 取 $\Omega = 3$，编程任务取 $\Omega = 1$）。

---

## 2. 三大任务域与关键消融实验（`2303.11366.md` Sec. 4 & Appendix）

### 2.1 序列决策（ALFWorld，134 环境 × 6 类任务）与推理（HotPotQA，100 题）

- **ALFWorld**：基线 ReAct 在幻觉率 `22%` 处停滞（第 6–7 轮后不再增长）；加入 Reflexion 后在 12 轮内完成 **`130 / 134`** 个任务，较强基线绝对提升 **`+22%`**。
- **HotPotQA（表 `tbl:reasoning:othermodels`）**：

| 模型与推理底座 | 基线准确率 | Reflexion 准确率 |
| :--- | :---: | :---: |
| `CoT (GT) + text-davinci-003` | `0.60` | **`0.77`** |
| `CoT (GT) + gpt-3.5-turbo` | `0.57` | **`0.71`** |
| `CoT (GT) + gpt-4` | `0.68` | **`0.80`** |
| `ReAct + text-davinci-003` | `0.30` | **`0.55`** |
| `ReAct + gpt-3.5-turbo` | `0.26` | **`0.38`** |
| `ReAct + gpt-4` | `0.39` | **`0.51`** |

- **反思相对纯情景回放的净收益**：在 `CoT (GT)` 上对比仅拼接最近失败轨迹（`EPM`）与生成第一人称自我反思，后者额外带来 **`+8%`** 绝对准确率提升。

### 2.2 编程基准与测试—反思双消融（`tbl:programming:success`, `tbl:programming:failures`, `tbl:programming:ablation`）

| 基准与语言 | 前序 SOTA | 基线 GPT-4 Pass@1 | Reflexion Pass@1 | 自测假阳性率 `FP` |
| :--- | :---: | :---: | :---: | :---: |
| **HumanEval (Python)** | `65.8` (CodeT+GPT-3.5) | `80.1` | **`91.0`** (`+10.9`) | `0.01`（条件误判 `1.4%`） |
| **HumanEval (Rust, 最难 50 题)** | — | `60.0` | **`68.0`** | `0.13` |
| **MBPP (Python)** | `67.7` (CodeT+Codex) | **`80.1`** | `77.1`（反降） | **`0.16`**（条件误判 `16.3%`） |
| **MBPP (Rust)** | — | `70.9` | **`75.4`** | `0.16` |
| **Leetcode Hard (Python, 40 题)** | — | `7.5` | **`15.0`** | — |

**HumanEval Rust 最难 50 题消融（`tbl:programming:ablation`）**：
- `Base model`（无单测、无反思）：`0.60`；
- **去掉自生成单测，仅保留自我反思**：暴跌至 **`0.52`**（失去早停信号，盲目反复改写破坏原本正确的代码）；
- **保留自生成单测，去掉自我反思**：停留在 **`0.60`**（只报报错栈不总结错因，无法指导复杂修复）；
- **完整 Reflexion（单测 + 自我反思）**：**`0.68`**。

### 2.3 明确失效边界（Sec. 4.3 & Appendix WebShop Limitation）

1. **WebShop（100 个电商购物任务）失效**：2-shot `ReAct + Reflexion` 连续 4 轮几乎无提升即提前终止，证明当任务需要高度多样化搜索与开放域探索（局部极小值难以靠回溯单步纠正）时，Reflexion 难以跳出局部最优。
2. **底座能力门槛（`tbl:programming:starchat`）**：在较弱代码模型 `starchat-beta`（HumanEval Python，8 次试验均值）上，Baseline 与 Reflexion 同为 `0.26`，说明有效自我纠错属于较大规模模型的涌现能力。
3. **验证器假阳性陷阱**：MBPP Python 上因自生成单测存在 `16.3%` 的假阳性（错代码全过单测），导致 Reflexion 过早提交错误解，总分反低于基线 `GPT-4`（`77.1` 对比 `80.1`）。

---

## 3. 开源仓库源码核对（`D:\coding\sharing\papers\repos\reflexion`）

1. **滑窗实现硬编码为 `memory[-3:]`**（`alfworld_runs/alfworld_trial.py` L47–50、`alfworld_runs/generate_reflections.py` L39–45）：实际代码在每次 `alfworld_run` 与 `update_memory` 时严格截取 `memory[-3:]`，与论文 $\Omega = 3$ 完全一致，且没有任何跨任务检索、向量索引或去重合并逻辑——**经验仅限同一任务内部跨轮试错复用**。
2. **失败触发条件与步数上限差异**（`alfworld_runs/alfworld_trial.py` L56）：源码中 `while cur_step < 49:` 允许最多 49 步，比论文 Sec. 4.1 描述的“超过 30 步即触发反思”更宽松；`generate_reflections.py` L15 的反思提示词明确要求“不要总结环境，而是指出具体应该采取但遗漏的动作路径并给出 `Plan:`”。

---

## 4. 对我们当前方案的直接启发

1. **区分“单任务内试错滑窗”与“跨任务持久化程序记忆”**：`Reflexion` 证实了自然语言反思的有效性，但其 `memory[-3:]` 滑窗无法跨任务沉淀经验（这也是后续 `AWM`、`ReasoningBank`、`REM` 解决的核心问题）；在我们的系统设计中，应明确将“单次对话内的澄清纠偏”与“跨单据/跨周期沉淀的规则库”分层解耦。
2. **防止自评假阳性导致过早提交**：正如 `MBPP` 中伪单测 `16.3%` 假阳性直接拉低准确率，我们的 Agent 在执行高风险参数修改或单据提交前，绝不能只依赖模型自评“我认为用户意思清楚了”，必须引入确定性的槽位完备度检查与外部环境/用户二次确认。

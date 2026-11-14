# TIDE-Bench：链式条件歧义与非单调意图撤回（Intent Drift）评测基准

- **标题**：*Evaluating LLMs on Conversational Text-to-SQL under Chain Ambiguity and Intent Drift* (EMNLP 2026 / arXiv:2608.29543)
- **作者 / 机构**：Yujia Liu, Jiayan Lin, Zijin Hong, Zheng Yuan, Shengyuan Chen, Hao Chen, Qinggang Zhang, Xiao Huang, Feiran Huang（暨南大学、香港理工大学等）
- **PDF**：`papers/benchmark/TIDE_2026.pdf`（全文：`papers/benchmark/2608.29543/2608.29543.md`）
- **配套仓库**：`https://github.com/Rcrossmeister/TIDE-Bench`（已克隆至 `papers/repos/TIDE-Bench`，目前仅含 `README.md` 与 `LICENSE` 占位文件，尚未发布评测脚本与数据）
- **核心定位**：基于 **514 条 BIRD 锚点 SQL** 采用**配对析因设计（Paired Factorial Design）**构造 **1,542 个多轮交互样本**（`Chain-only` / `Drift-only` / `Joint` 各 514），分别通过**反事实因果测试**界定“后层澄清条件依赖于前层决议”的链式歧义（Chain Ambiguity），以及基于 AST 承诺集的**非单调集合包含测试**（$S_{\mathrm{pre}} \nsubseteq S_{\mathrm{post}}$）界定“撤回/替换已承诺约束”的用户意图漂移（Intent Drift）。

---

## 一、核心背景与研究痛点

现有多轮对话式 Text-to-SQL 与澄清评测存在两大盲区（`Sec. 1`）：
1. **将所有歧义视为单轮孤立问题**：已有基准（如 AmbiQT / AMBROSIA / PRACTIQ）只测单句内的静态词法/结构歧义，忽略了真实交互中**L1 澄清结果会决定 L2 澄清是否存在或如何表述**的跨轮条件依赖；
2. **仅用最终执行准确率掩盖非单调状态修正**：当用户在对话中途推翻先前的条件（“不要限定在 2000–2010 年，查全部年份”）时，单看端到端执行匹配（EX）无法区分模型是“真正从状态中撤回了旧约束”还是“碰巧猜对 SQL”。

---

## 二、核心形式化定义与基准构造

```text
  [BIRD 830 候选锚点 SQL]
           │
           ├──► 1. 链式歧义 (Chain Ambiguity, Sec. 2.1): L1 + L2 两层澄清
           │       • 反事实测试 (Counterfactual Test): 若 L1 取备选解释，L2 是否还成立？
           │         - Eliminated (49.4%): L2 前提完全失效（如 L1 选 "任期" 后，"是否排除退款" 失去指代）
           │         - Transformed (50.6%): L2 需改写指代/范围
           │         - Invariant (剔除): 独立叠加歧义，不构成链式依赖 → 保留 695/830 (94.7% 双裁判一致)
           │
           ├──► 2. 意图撤回/漂移 (User Intent Drift, Sec. 2.2 & Alg. 1): 基于 sqlglot AST 承诺集 S(y)
           │       • 非单调性检验: 发生漂移 ⟺ S_pre ⊈ S_post (至少有旧承诺被删改，排除纯追加)
           │       • 三类子型: Value-level (34.0%, 替换单字面值) / Constraint-level (31.3%, 删除 WHERE 过滤)
           │                   / Projection-level (34.6%, 改输出列/排序等) → 保留 514 条三元组
           │
           └──► 3. 配对析因组装 (Paired Factorial Design, Sec. 3.1):
                   • 同一锚点 y* 派生 3 个平行样本: Chain-only (C) / Drift-only (D) / Joint (J) = 1,542 样本
                   • 双协议评测 (Sec. 4.1): f-protocol (从头交互) vs p-protocol (预置 L1 答案，隔离测 L2)
```

- **七项核心评测指标（`Sec. 4.3`, `Table 2`）**：
  1. **DEA**（Dialogue Execution Accuracy）：整条轨迹中**所有**生成的 SQL（Chain 为 1 条，Drift/Joint 为前后 2 条）均通过执行匹配；
  2. **AR**（Ask Rate）：对话中是否发起了至少一次澄清；
  3. **L1-IR / L2-IR$^{p}$ / JIR**：用户模拟器路由判定模型在 $f$-协议中命中 L1、在 $p$-协议（L1 已预先喂给模型）中命中 L2、以及同时识别 L1+L2 的比例；
  4. **DRR**（Drift Recognition Rate）：模型是否识别到漂移并产出了满足 $S(y_{\mathrm{pre}}) \nsubseteq S(y_{\mathrm{post}})$ 的非单调修改；
  5. **DRA**（Drift Resolution Accuracy）：不仅满足 DRR，且漂移后的 $y_{\mathrm{post}}$ 执行完全正确。
- **人工抽检信度（`Sec. 3.3`, `Table 1`）**：对 250 组三元组（750 样本）由 5 位工程师盲评，多数同意率 **92.4%**（全部一致 83.1%，Fleiss' $\kappa = 0.81$）。

---

## 三、核心实验结果（对照原文 `source/table/dea.tex` 与 `Sec. 5` 核实）

### 1. 12 个大模型在三类配对任务上的 DEA（`Table 3 / source/table/dea.tex`, %）

| # | 模型 | Chain-only | Drift-Value | Drift-Constraint | Drift-Projection | Drift-All | Joint-Value | Joint-Constraint | Joint-Projection | Joint-All |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | **Claude-Sonnet-4.6** | **35.9** | **47.7** | **44.2** | 43.4 | **45.1** | **31.2** | 20.2 | **31.4** | **27.8** |
| 2 | **Qwen2.5-72B** | 32.4 | 44.3 | 41.1 | 44.0 | 43.2 | 30.1 | 21.5 | 28.6 | 26.8 |
| 3 | **o4-mini** | 32.9 | 42.6 | 41.1 | 40.0 | 41.2 | **31.2** | 21.5 | 27.4 | 26.8 |
| 4 | **GPT-4o** | 30.9 | 46.0 | 38.7 | **44.6** | 43.2 | 27.8 | **22.1** | 29.7 | 26.7 |
| 5 | **GPT-5.4** | 32.5 | 43.2 | 36.8 | 42.3 | 40.9 | 27.8 | 20.9 | 29.7 | 26.3 |
| 6 | **Llama-3.3-70B** | 32.7 | 40.3 | 39.3 | 38.9 | 39.5 | 29.5 | **22.1** | 26.9 | 26.3 |
| 7 | o3-mini | 32.6 | 40.9 | 37.4 | 38.9 | 39.1 | 29.5 | 18.4 | 28.6 | 25.7 |
| 8 | Gemini-2.5-Flash | 31.6 | 39.2 | 42.9 | 33.1 | 38.3 | 27.3 | 20.2 | 27.4 | 25.1 |
| 11 | DeepSeek-V4-Flash | 27.3 | 40.9 | 39.9 | 39.4 | 40.1 | 21.6 | 17.8 | 26.9 | 22.2 |

### 2. 三大诊断性发现（`Sec. 5.2–5.4`）

1. **链式歧义的根本瓶颈是“识别容量”而非“不爱追问”（`Sec. 5.2`, `Fig. 3`）**：
   - 12 个模型的同时识别两层歧义率（`JIR`）全部低于 **5%**（多数低于 2%）：哪怕是追问率（`AR`）高达 `60.1%` 的 `Qwen2.5-72B`，`JIR` 也仅 **`1.2%`**；而克制追问的 `Claude-Sonnet-4.6`（`AR = 9.7%`，且无歧义 Drift 样本追问率仅 `0.4%`）`JIR` 为 `0.6%`。
   - 即便用 $p$-协议预先把 L1 澄清答案直接喂给模型，模型对依赖层 L2 的识别率（`L2-IR^p`）依然只有 **`1.2%`（Gemini-2.5-Flash）~ `13.8%`（Claude-Sonnet-4.6）**，说明模型本质上不会“沿着已消歧前提继续推导次生条件歧义”。
2. **意图撤回的“识别—解决鸿沟”超过 40 个百分点（`Sec. 5.3`, `Fig. 4–5`）**：
   - 所有模型都能听懂用户在改口（`DRR ≥ 94.9%`），但能把旧约束干净撤回并产出正确新查询的 `DRA` 只有 **`45–55%`**，中间隔着 **>40 pp** 的执行鸿沟。
   - **反直觉难度排序**：在三类漂移中，生成后 SQL 语法最简单的 **`Constraint-level`（删除已有 WHERE 过滤条件）反而是 12 个模型中 10 个最难解决的子型**（如 `GPT-5.4` 在 Projection 上 `61.7%` vs Constraint 上仅 `42.3%`）——难点不在 SQL 生成本身，而在于**定位“先前究竟哪一条已承诺约束需要被精准移除”**。
3. **联合场景下错误高度重叠且前序错误被继承（`Sec. 5.4`, `Table 2`）**：
   - 从 `Drift-only` 切到 `Joint` 后，所有模型的 `DRR` 最多降 `5 pp`，但 `DRA` 掉 `6–12 pp`、`DEA` 掉 `13–18 pp`；因为前序链式歧义留下的错误假设会原封不动遗传到漂移后的状态中。

---

## 四、配套代码核查结论

| 核查项 | 论文声称 | 本地仓库实测 (`papers/repos/TIDE-Bench`) | 差异 |
| :--- | :--- | :--- | :--- |
| `Rcrossmeister/TIDE-Bench` | Abstract 称 "corresponding code of TIDE-Bench is released" | 仅包含 `README.md`（112 B）、`LICENSE`（1,091 B）、`.gitattributes`（68 B） | 仓库目前为 EMNLP 2026 录用占位库，源码与 1,542 条样本尚未上传 |

---

## 五、对我们主报告与业务系统的落地启发

1. **评测设计（对应主报告 1.1 方向三）**：
   - **构造“条件依赖式 L1→L2 链式追问”用例**：例如 L1 先确认“需要保障的是《王者荣耀》还是全局网速”，只有 L1 选《王者荣耀》时，L2 才需要进一步确认“是晚高峰排位延迟波动还是更新包下载慢”（若 L1 选“全局宽带”，则该 L2 自动消解——可用 TIDE 的**反事实测试**校验用例真伪）。
   - **引入非单调承诺撤回（`Constraint-level Drift`）**：明确测试用户“算了，把刚才加的周末限制去掉 / 不要自动续费了，改成单次”场景，用 **AST / 结构化槽位承诺集差集**（$S_{\mathrm{pre}} \nsubseteq S_{\mathrm{post}}$）自动化检验 Agent 是否真正从工作记忆中剔除了旧槽位，避免“口头答应改口、旧槽位仍残留进下轮工具调用”。
2. **工作记忆与状态追踪设计**：
   - 论文证明多轮对话不能靠把历史全文塞给 LLM 隐式覆盖，必须维护**显式的结构化承诺槽位集合（Commitment Set）**，并在用户改口时做显式 Diff 删除（Remove/Replace），而不是纯 Append。

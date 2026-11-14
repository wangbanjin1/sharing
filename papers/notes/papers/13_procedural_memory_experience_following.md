# 13. Experience-Following Study：经验记忆管理如何塑造智能体长程演化与两类退化治理

← 返回 [精读笔记索引](../reading_notes.md)　·　[论文主目录](../../README.md)

---

## 0. 论文基本信息与核心锚点

| 项目 | 内容 |
| :--- | :--- |
| **论文标题** | *How Memory Management Impacts LLM Agents: An Empirical Study of Experience-Following Behavior* |
| **作者与单位** | Zidi Xiong（Harvard University）、Yuping Lin（University of Georgia）、Wenya Xie（Michigan State University）、Pengfei He（Michigan State University）、Zirui Liu（University of Minnesota）、Jiliang Tang（Michigan State University）、Himabindu Lakkaraju（Harvard University）、Zhen Xiang（University of Georgia） |
| **发表时间与编号** | `arXiv:2505.16067v2`（2025 年 5 月，v2 修订版） |
| **本地文件锚点** | LaTeX 源码：[`papers/procedural_memory/2505.16067/source/main.tex`](../../procedural_memory/2505.16067/source/main.tex) |
| **官方开源仓库** | [`https://github.com/yuplin2333/agent_memory_manage`](https://github.com/yuplin2333/agent_memory_manage)（正文 `Sec 3.1:239` 脚注声明；本地已克隆至 [`papers/repos/agent_memory_manage/`](../../repos/agent_memory_manage/)） |
| **核心研究问题** | 当智能体将自身运行产生的历史轨迹（`Query-Execution Pairs`）不断回写至经验记忆库并用于后续任务的上下文示例（`In-Context Demonstrations`）时，记忆的**写入策略（`Memory Addition`）**与**删除策略（`Memory Deletion`）**如何通过智能体的**经验跟随特性（`Experience-Following Property`）**决定长程演化是持续提升还是雪崩退化？ |
| **主报告支撑章节** | **3.3.3 节（程序与经验记忆的写入准入与防退化校验）**、**3.3.4 节（基于下游复用效用的记忆遗忘与负迁移清洗）** |

---

<a id="c13-1"></a>

## 13.1 研究背景、核心现象与两类记忆诱导退化（`Sec 1–3`）

### 1. 经验记忆的动态自累积闭环（`Sec 1:34–48, Sec 2.2:123–149, Fig. 1–2`）

在真实长程运行场景中，智能体通常从一个较小的高质量初始种子记忆库 $\mathcal{M}_0 = \{(q_i, e_i)\}_{i=1}^{N_{\text{init}}}$（例如由人工标注或离线验证的少量正确轨迹）起步〔正文 `Sec 1:39–41, Sec 3.1:234–237`〕。每当收到新任务查询 $q$ 时，智能体执行三步循环〔正文 `Sec 2.2:128–149`，图表 `Fig. 2`〕：

1. **经验检索（`Experience Retrieval`）**：计算当前查询 $q$ 与记忆库 $\mathcal{M}_t$ 中各历史查询 $q_i$ 的输入相似度 $S_{\text{in}}(q, q_i)$，召回 Top-$K$ 最相似记录 $\mathcal{R}(q) = \{(q_{i_k}, e_{i_k})\}_{k=1}^K$ 作为上下文示例（`In-Context Demonstrations`）；
2. **执行生成（`Execution Generation`）**：大模型以 $\mathcal{R}(q)$ 与当前查询 $q$ 拼装提示词，生成当前任务的执行轨迹或求解代码 $e = \operatorname{Agent}(q \mid \mathcal{R}(q))$；
3. **记忆管理（`Memory Management`）**：
   - **选择性写入（`Selective Addition`）**：由评估器 $\Phi(q, e)$ 判断本次执行 $e$ 的质量，通过写入策略 $\pi(q, e) \in \{0, 1\}$ 决定是否将 $(q, e)$ 追加进记忆库；
   - **记忆删除（`Memory Deletion`）**：通过删除策略 $\phi(q_i, e_i, t) \in \{0, 1\}$ 定期或按步清理过期冷门记录与导致下游表现恶化的低质记录。

```
┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│                 Experience-Following Agent Memory Management Loop (Fig. 1 & Fig. 2)           │
├───────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                               │
│   Incoming Query q_t ──► [1. Retrieval: Top-K by S_in(q_t, q_i)]                              │
│                                      │                                                        │
│                                      ▼                                                        │
│                    Retrieved Demos {(q_{i_1}, e_{i_1}), ..., (q_{i_K}, e_{i_K})}              │
│                                      │                                                        │
│                                      ▼  Strong Experience-Following:                          │
│                              [2. LLM Agent Execution]  High S_in(q_t, q_i) ===> High S_out    │
│                                      │                                                        │
│                                      ▼                                                        │
│                            Generated Execution e_t                                            │
│                                      │                                                        │
│                     ┌────────────────┴────────────────┐                                       │
│                     ▼                                 ▼                                       │
│      [3a. Selective Addition Gate π]    [3b. Downstream Utility Attribution]                  │
│      Evaluate Φ(q_t, e_t):              Record task outcome Φ(q_t, e_t) back to               │
│      • Add All (π = 1)                  each retrieved record (q_{i_k}, e_{i_k})              │
│      • Coarse Evaluator (LLM Judge)     as a "Free Quality Label"!                            │
│      • Strict Evaluator (Env / Exec)                  │                                       │
│                     │                                 ▼                                       │
│                     │                   [3c. Memory Deletion Gate φ]                          │
│                     │                   • Periodical Deletion φ_per (Prune cold records)      │
│                     │                   • History-Based Deletion φ_hist (Prune records whose  │
│                     │                     avg downstream utility ≤ β after > n retrievals)    │
│                     ▼                                 │                                       │
│              ┌────────────────────────────────────────┴───────────────────────┐               │
│              │              Dynamic Experience Memory Bank M_t                │               │
│              └────────────────────────────────────────────────────────────────┘               │
└───────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2. 核心发现一：强经验跟随特性（`Strong Experience-Following Property`，`Sec 3.3:273–326, Fig. 3`）

作者定义一个通用指标体系来刻画检索记录对当前生成结果的牵引强度〔正文 `Sec 3.3:277–293`〕：
- **输入相似度（`Input Similarity`）**：当前任务查询 $q$ 与其召回的 Top-$K$ 记忆查询的平均相似度：
  $$\bar{S}_{\text{in}}(q) = \frac{1}{K} \sum_{k=1}^{K} S_{\text{in}}(q, q_{i_k})$$
- **输出相似度（`Output Similarity`）**：当前生成的执行结果 $e$ 与召回的 Top-$K$ 历史执行结果的平均相似度：
  $$\bar{S}_{\text{out}}(e) = \frac{1}{K} \sum_{k=1}^{K} S_{\text{out}}(e, e_{i_k})$$

跨四个领域的实证曲线（`Fig. 3` 与 `App C.1 Fig. 10`）揭示了两条规律〔正文 `Sec 3.3:294–326`〕：
1. **高输入相似直接诱导高输出相似（模仿复制效应）**：当新查询 $q$ 在记忆库中检索到高相似度的历史查询 $q_i$ 时，大模型生成的执行轨迹 $e$ 会高度模仿甚至直接照搬 $e_i$ 的结构与参数。在受控回归任务 `RegAgent` 中，随着记忆库规模增长，输入相似度与输出相似度的 Pearson 相关系数迅速逼近 $r \approx 1.0$〔正文 `Sec 3.3:303–309`，图表 `Fig. 3(a)`〕。
2. **记忆不断膨胀会单调推高经验跟随强度**：相比固定大小的初始记忆库（`Fixed Memory`），持续向记忆库写入新样本会不断提高新任务在记忆库中命中高相似查询的概率（$\bar{S}_{\text{in}}$ 单调上升），从而使 $\bar{S}_{\text{out}}$ 同步攀升〔正文 `Sec 3.3:310–326`，图表 `Fig. 3(b)`〕。

### 3. 核心发现二：经验跟随引发的两类系统性退化（`Sec 3.4:327–381, Sec 4.3:458–503`）

由于智能体具备强经验跟随特性，一旦记忆库的管理失控，原本旨在提升性能的经验检索反而会触发两类退化闭环：

| 退化类型 | 触发阶段 | 作用机理与退化链路 | 原文实证锚点 |
| :--- | :--- | :--- | :--- |
| **第一类：错误自举传播（`Error Propagation`）** | 记忆写入阶段（`Addition`）准入过宽 | 若某次含错或低质执行 $(q_{\text{err}}, e_{\text{err}})$ 被写入记忆库 $\rightarrow$ 后续遇到相似查询 $q'$ 时被高相似度召回 $\rightarrow$ 经验跟随特性迫使智能体复刻该错误生成 $e'_{\text{err}}$ $\rightarrow$ 新错误再次写入记忆库，形成自我强化的恶性循环，导致全量追加（`Add all`）性能甚至远低于不更新的固定记忆（`Fixed`）。 | `Sec 3.4:327–381`、`Fig. 4`（对比真实错误入库与强制替换 Ground-Truth 的 `Error-Free Variant`） |
| **第二类：失配经验重放（`Misaligned Experience Replay`）** | 记忆留存阶段（`Retention`）缺乏后验淘汰 | 即便写入时通过了严格或粗粒度门槛（例如回归误差刚好卡在阈值边缘 $0.5 < |\hat{y}-y| \le 1.0$，或生成的代码仅在特定窄条件下偶然跑通），该记录在作为**后续不同上下文查询的示例（Demonstration）**时仍可能产生系统性误导，导致凡是召回它的下游任务成功率显著偏低。 | `Sec 4.3:458–503`、`Fig. 6`、`App B.3 Fig. 12`、`App B.5 Fig. 14–15 & Table 4` |

---

<a id="c13-2"></a>

## 13.2 四类评测智能体、相似度度量与记忆管理算式（`Sec 3.1, Sec 4.1, App A`）

### 1. 四类智能体实验床与相似度算式（`Sec 3.1:212–238, App A.1–A.2:626–830, Table 3`）

为排除单一任务偏差，论文横跨合成受控数学任务、医疗数据库编程、自动驾驶轨迹规划与物联网入侵检测四个领域构建了实验床〔正文 `Sec 3.1:212–238`，附录 `App A.1 Table 3`〕：

| 智能体名称 | 任务定义与数据集规模 | 输入相似度 $S_{\text{in}}(q, q_i)$ 定义 | 输出相似度 $S_{\text{out}}(e, e_i)$ 定义 | 初始记忆 $N_{\text{init}}$ 与检索 $K$ |
| :--- | :--- | :--- | :--- | :--- |
| **RegAgent**（合成受控多元回归） | 6 维输入 $x \in \mathbb{R}^6 \sim \mathcal{N}(\mu, I)$（$\mu \in \{-0.5, 0, 0.5\}$），真值 $y = w^\top x + \epsilon$（$\epsilon \in [-1, 1]$），流式测试 **4,000** 步。预测误差 $|\hat{y} - y| \le 1.0$ 判为成功。 | 6 维特征向量的余弦相似度：$\frac{x^\top x_i}{\|x\|_2 \|x_i\|_2}$〔附录 `App A.2:752–757`〕 | 预测标量的有界绝对距离转换：$1 - \min(1, \frac{|\hat{y} - \hat{y}_i|}{10})$〔附录 `App A.2:758–763`〕 | $N_{\text{init}} = 100$，$K = 6$ |
| **EHRAgent**（医疗电子病历 Text-to-Code） | 基于 `MIMIC-III` 数据库（17 张表、6 个工具函数 `LoadDB / FilterDB / GetValue / SQLInterpreter / Calculate / Calendar`），流式测试 **2,392** 条医疗问答。 | `text-embedding-3-large` 编码问题文本后的余弦相似度〔附录 `App A.2:765–770`〕 | 基于抽象语法树（AST）的代码结构查重工具 `pycode_similar` 计算生成 Python 解法代码的相似度〔正文 `Sec 3.3:290`，附录 `App A.2:771–776`〕 | $N_{\text{init}} = 100$，$K = 4$ |
| **AgentDriver**（自动驾驶轨迹规划） | 基于 `nuScenes` 数据集，根据自车状态（`ego_states`）、环境感知（`perception`）与常识记忆预测未来 3 秒（6 步）规划轨迹 $v \in \mathbb{R}^{6 \times 2}$，流式测试 **2,000** 个驾驶场景。 | 三元组特征加权高斯核：$\exp\!\left(-\sum_{j=1}^3 c_j \|q_j - k_j\|_2^2\right)$，权重 `key_coefs = [1.0, 10.0, 1.0]`〔附录 `App A.2:778–788`，实现 `experience_memory.py:51, 200`〕 | 6 步 2D 规划轨迹向量的 RBF 高斯核：$\exp(-\gamma \|v - v_i\|_2^2)$，其中 $\gamma = 1.0$〔附录 `App A.2:789–795`〕 | $N_{\text{init}} = 180$，$K = 1$（由原版 Top-3 + LLM 二次筛选简化为 Top-1 确定性召回以保证可复现性，`experience_memory.py:48, 206`） |
| **CIC-IoT Agent**（物联网 8 类流量入侵检测） | 基于 `CIC-IoT2023` 数据集（46 维网络流统计特征，区分 7 类 DDoS 攻击与 `BenignTraffic`），流式测试 **1,000** 条流量记录。 | 连续特征相对变化率 $S_{\text{cont}}(f_i) = \frac{1}{1 + |f_i - f'_i| / \max(|f_i|, |f'_i|, \epsilon)}$ 与离散特征精确匹配 $S_{\text{disc}}(f_i) = \mathbf{1}[f_i = f'_i]$ 的均值〔附录 `App A.2:797–824`〕 | 预测流量类别标签的精确匹配指示函数 $\mathbf{1}[\hat{y} = \hat{y}_i]$〔附录 `App A.2:825–830`〕 | $N_{\text{init}} = 50$（`Table 1` 报告为 50，`App A.1` 文本提及 100），$K = 3$ |

### 2. 记忆写入策略（`Memory Addition Strategies`，`Sec 3.1:185–211`）

设评估器对当前任务执行 $(q, e)$ 给出质量评分 $\Phi(q, e)$，写入门控策略定义为 $\pi(q, e) \in \{0, 1\}$。论文系统对比了六档写入策略〔正文 `Sec 3.1:190–211, Table 1`〕：

1. **`Fixed`（静态只读基线）**：$\pi(q, e) = 0$，全程只使用初始种子记忆库 $\mathcal{M}_0$，不写入任何测试期生成的轨迹。
2. **`Add all`（无差别全量写入）**：$\pi(q, e) = 1$，将测试期生成的每一条轨迹无条件追加进记忆库。
3. **`Coarse (C1 / C2 / C3)`（无环境真值的粗粒度自评估准入）**：模拟在线无 Ground-Truth 反馈时，使用不同能力梯度的评估器做准入过滤：
   - 在 `RegAgent` 中，`C1 / C2 / C3` 分别对应放宽的误差准入阈值 $|\hat{y} - y| \le 1.6 \;/\; 1.4 \;/\; 1.2$；
   - 在 `EHRAgent`、`AgentDriver` 与 `CIC-IoT` 中，`C1` 使用 `GPT-4o-mini` 作为 LLM Judge，`C2` 使用更强的 `GPT-4.1-mini` 作为 LLM Judge，`C3` 使用在 **300 条正确评判样本上微调后的 `GPT-4.1-mini-FT`** 作为领域专用 Judge〔正文 `Sec 3.1:201–211`，附录 `App A.4:1046–1220`〕。
4. **`Strict`（严格环境反馈/精确验证准入）**：仅当执行结果通过严格的执行器或物理指标检验时才允许入库：
   - `RegAgent`：$|\hat{y} - y| \le 1.0$；
   - `EHRAgent`：生成的医疗查询代码执行结果与标准答案完全一致（`Exact Match`）；
   - `AgentDriver`：参考 `UniAD` 评测标准，3 秒规划轨迹与专家轨迹的平均 $L_2$ 误差 $< 2.5\text{m}$〔正文 `Sec 3.1:229–232`，实现 `main_strict.py:249, ADDITION_L2_THRESHOLD = 2.5`〕；
   - `CIC-IoT`：分类预测结果与真实攻击标签一致。

### 3. 记忆删除策略（`Memory Deletion Strategies`，`Sec 4.1:384–429`）

即便启用了写入门控，记忆库仍会随时间无限膨胀，且会滞留两类有害或冗余记录：① 长期不再被后续任务命中的冷门记录；② 写入时看似合格、但在后续被召回做上下文示例时频繁诱导下游任务失败的“失配记录”。论文为此设计了三类删除算子〔正文 `Sec 4.1:390–429`〕：

#### (1) 基于时间窗口检索频次的定期淘汰（`Periodical-Based Deletion`）
设 $\operatorname{fr}_t(q_i, e_i)$ 为记录 $(q_i, e_i)$ 截至时间步 $t$ 被召回的总次数。若在过去的时间窗口 $\Delta t = t - t'$（论文设为 `500` 步）内，该记录的增量被检索次数不超过阈值 $\alpha$（论文设为 $\alpha = 2$ 或 $3$），则将其作为冷门死记忆删除〔正文 `Sec 4.1:395–405`，附录 `App A.1 Table 3`〕：
$$\phi_{\text{per}}(q_i, e_i, t, t') = \mathbf{1}\!\left[\operatorname{fr}_t(q_i, e_i) - \operatorname{fr}_{t'}(q_i, e_i) \le \alpha\right]$$

#### (2) 基于下游任务复用效用的历史表现淘汰（`History-Based Deletion`）——核心机制创新
一条历史记录 $(q_i, e_i)$ 作为示例到底“好不好用”，最直接的证据是**当它被后续任务 $q_m$ 召回作为 In-Context Demonstration 时，下游任务 $q_m$ 最终的执行得分 $\Phi(q_m, e_m)$ 高不高**。作者据此提出**将下游任务的评估得分反向归因给本次被召回的所有记忆记录，作为无需额外调用 LLM 的“免费质量标签（Free Quality Labels）”**〔正文 `Sec 4.1:406–422`〕：
$$\phi_{\text{hist}}(q_i, e_i, t) = \begin{cases} \mathbf{1}\!\left[\dfrac{1}{\operatorname{fr}_t(q_i, e_i)} \displaystyle\sum_{m=1}^{\operatorname{fr}_t(q_i, e_i)} \Phi(q_m, e_m) \le \beta\right], & \text{if } \operatorname{fr}_t(q_i, e_i) > n, \\[10pt] 0, & \text{otherwise}. \end{cases}$$

符号解释如下：
- $\operatorname{fr}_t(q_i, e_i)$：截至当前步 $t$，记忆条目 $(q_i, e_i)$ 被检索召回的累计次数；
- $n$：触发历史效用考核的最小检索次数门槛（避免某条记录仅因偶然遇到 1 次极难下游任务就被误杀，论文设为 $n = 3$ 或 $5$，见 `App A.1 Table 3`）；
- $\Phi(q_m, e_m)$：第 $m$ 次召回该记忆条目的下游任务 $(q_m, e_m)$ 获得的任务级评估分（可来自 `Strict` 评估器，也可直接复用与写入阶段完全相同的 `Coarse` LLM Judge 评估分，无需任何新增评估开销）；
- $\beta$：平均下游效用淘汰阈值（若以误差 $L_2$ 度量，则为误差高于阈值时触发淘汰）。

#### (3) 联合淘汰策略（`Combined Deletion`）
同时启用冷门定期清理与低效用历史淘汰，任一条件触发即从记忆库中移除〔正文 `Sec 4.1:423–429`〕：
$$\phi_{\text{comb}}(q_i, e_i, t, t') = \phi_{\text{per}}(q_i, e_i, t, t') \lor \phi_{\text{hist}}(q_i, e_i, t)$$

---

<a id="c13-3"></a>

## 13.3 全量实验结果、错误传播验证与分布漂移消融（`Sec 3.2–4.5, Tables 1–4`）

### 1. 记忆写入策略全量对比（`Sec 3.2:240–272, Table 1`）

各写入策略在四个智能体上的最终任务成功率/准确率（`SR / ACC %`）与运行结束时的最终记忆库条目数（`Mem Size`）见下表〔图表 `Table 1`〕：

| 写入策略（`Addition Strategy`） | 准入评估器强度 | RegAgent `SR (%)` | RegAgent `Mem Size` | EHRAgent `ACC (%)` | EHRAgent `Mem Size` | AgentDriver `SR (%)` | AgentDriver `Mem Size` | CIC-IoT `ACC (%)` | CIC-IoT `Mem Size` |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`Fixed`**（不写入新记忆） | $\pi = 0$（只读初始库） | 67.53 | 100 | 16.75 | 100 | 40.11 | 180 | 71.50 | 50 |
| **`Add all`**（全量无条件写入） | $\pi = 1$（无过滤） | 55.48 | 4,100 | 13.05 | 2,411 | 32.32 | 2,125 | 59.90 | 1,050 |
| **`Coarse C1`** | `1.6` / `GPT-4o-mini` | 63.18 | 3,511 | 26.19 | 1,447 | 36.92 | 1,161 | 74.00 | 1,030 |
| **`Coarse C2`** | `1.4` / `GPT-4.1-mini` | 65.78 | 3,347 | 32.21 | 1,467 | 40.01 | 1,119 | 68.80 | 936 |
| **`Coarse C3`** | `1.2` / `GPT-4.1-mini-FT` | 67.35 | 3,139 | 34.66 | 1,094 | 47.37 | 1,285 | 79.50 | 952 |
| **`Strict`**（严格环境/真值准入） | `1.0` / `Exact` / `L2<2.5m` | **70.95** | **2,938** | **38.50** | **1,012** | **51.00** | **1,178** | **85.40** | **904** |

**核心实证结论（`Sec 3.2 & Sec 3.4`）**：
1. **盲目全量写入（`Add all`）在所有四个智能体上均引发严重性能崩塌**：相比完全不更新的 `Fixed` 基线，`Add all` 在 `RegAgent` 上暴跌 **$-12.05\%$**（`67.53% → 55.48%`），在 `EHRAgent` 上下跌 **$-3.70\%$**（`16.75% → 13.05%`），在 `AgentDriver` 上暴跌 **$-7.79\%$**（`40.11% → 32.32%`），在 `CIC-IoT` 上暴跌 **$-11.60\%$**（`71.50% → 59.90%`）。
2. **准入评估器的判别精度与智能体长程表现呈严格单调正相关**：随着评估器从 `C1 (GPT-4o-mini)` $\rightarrow$ `C2 (GPT-4.1-mini)` $\rightarrow$ `C3 (300 样本微调 GPT-4.1-mini)` $\rightarrow$ `Strict` 逐步收紧，错误轨迹被拦截在外，记忆库规模从 `Add all` 的 `2,411`（EHRAgent）精简至 `1,012`，而准确率从 `13.05%` 一路跃升至 **`38.50%`**（相比 `Fixed` 提升 **$+21.75\%$**，接近翻了 `2.3` 倍）。
3. **仅用 300 条标注样本微调轻量级 Judge（`C3`）即可逼近 `Strict` 效果**：在 `AgentDriver` 与 `CIC-IoT` 上，`C1 (GPT-4o-mini)` 因判别能力不足导致误放大量劣质轨迹入库（`AgentDriver` 上 `36.92%` 甚至低于 `Fixed` 的 `40.11%`），而经 300 条样本微调的 `C3` 将成功率推高至 `47.37%`（`AgentDriver`）与 `79.50%`（`CIC-IoT`）。

### 2. 记忆删除策略与写入策略的正交组合对比（`Sec 4.2:430–457, Table 2`）

在启用不同写入准入（`Coarse C1 / C2 / C3` 与 `Strict`）的基础上，进一步叠加三类删除策略（`Periodical`、`History-based`、`Combined`）的全量结果如下表所示〔图表 `Table 2`〕：

| 智能体 | 写入准入档位 | `No Deletion`（仅写入）<br>`ACC/SR (%)` \| `Size` | `Periodical Deletion`<br>`ACC/SR (%)` \| `Size` | `History-Based Deletion`<br>`ACC/SR (%)` \| `Size` | `Combined Deletion`<br>`ACC/SR (%)` \| `Size` |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **EHRAgent** | `Coarse C1 (4o-mini)` | 26.19 \| 1,447 | 28.99 \| 347 | 29.95 \| 1,103 | **30.62** \| **318** |
| | `Coarse C2 (4.1-mini)` | 32.21 \| 1,467 | 31.38 \| 331 | 35.14 \| 1,111 | **36.23** \| **305** |
| | `Coarse C3 (4.1-mini-FT)` | 34.66 \| 1,094 | 36.23 \| 298 | **40.29** \| 796 | 39.20 \| **267** |
| | `Strict (Exact Match)` | 38.67 \| 1,012 | 38.59 \| 302 | 42.06 \| 784 | **42.34** \| **248** |
| **AgentDriver** | `Coarse C1 (4o-mini)` | 36.92 \| 1,161 | 37.82 \| 391 | **42.16** \| 642 | 39.02 \| **276** |
| | `Coarse C2 (4.1-mini)` | 40.01 \| 1,119 | 38.57 \| 361 | **42.46** \| 673 | 41.76 \| **278** |
| | `Coarse C3 (4.1-mini-FT)` | 47.37 \| 1,285 | 46.87 \| 441 | **48.61** \| 774 | 46.97 \| **316** |
| | `Strict (L2 < 2.5m)` | 51.00 \| 1,178 | 50.94 \| 467 | **51.81** \| 846 | 49.97 \| **323** |
| **CIC-IoT** | `Coarse C1 (4o-mini)` | 74.00 \| 1,030 | 74.30 \| 281 | 74.20 \| 1,013 | **77.40** \| **277** |
| | `Coarse C2 (4.1-mini)` | 68.80 \| 936 | 74.20 \| 294 | **76.30** \| 865 | 75.50 \| **264** |
| | `Coarse C3 (4.1-mini-FT)` | 79.50 \| 952 | 82.00 \| 267 | **82.20** \| 871 | 79.50 \| **248** |
| | `Strict (Exact Label)` | 85.40 \| 904 | 80.80 \| 310 | **89.60** \| 788 | 85.50 \| **188** |

*注：`EHRAgent` 在 `Table 1` 中的 `Strict (No Deletion)` 为 `38.50%`，而在 `Table 2` 中由于随机种子批次微小波动报告为 `38.67%`，记忆库大小均为 `1,012`〔图表 `Table 1 & Table 2`〕。*

**核心实证结论（`Sec 4.2–4.3`）**：
1. **`History-Based Deletion` 在几乎所有配置下均显著提振准确率，甚至能修正 `Strict` 写入的次优样本**：
   - 在 `EHRAgent` 上，`Strict + History Deletion` 将准确率从 `38.67%` 进一步推高至 **`42.06%`**（叠加 `Combined` 后达 **`42.34%`**），同时将记忆库从 `1,012` 条压缩至 **`248` 条（缩减 `75.5%`）**；
   - 在 `CIC-IoT` 上，`Strict + History Deletion` 将准确率从 `85.40%` 推高至 **`89.60%`（$+4.20\%$）**；`Combined Deletion` 在保持 `85.50%` 准确率的同时，将记忆库从 `904` 条压缩至 **`188` 条（缩减 `79.2%`）**；
   - 在 `AgentDriver` 上，当写入准入较弱（`Coarse C1`）时，`History-Based Deletion` 将成功率从 `36.92%` 大幅挽回至 **`42.16%`（$+5.24\%$）**，超过了 `Fixed` 基线（`40.11%`）。更令人瞩目的是，在附录 `App B.3 Fig. 12` 的真值对照实验中，**`Strict + Combined Deletion` 在第 1,000 步之后甚至反超了永远只写入完美无错样本的 `Error-Free Variant`**——因为即便是满足 $L_2 < 2.5\text{m}$ 的真值样本，也有部分轨迹在跨场景复用时泛化性较差，而 `History-Based Deletion` 能够通过下游效用反馈将这些“虽然自身合格、但作为示例误导性高”的次优记录精准剔除〔附录 `App B.3:1286–1289, Fig. 12`〕。
2. **被删除记录与保留记录的内在质量核验（`Sec 4.3, App B.5 Table 4 & Fig. 14–15`）**：
   作者统计了在 `Coarse` 准入下被 `History-Based Deletion` 淘汰的记录与保留记录相对于真实 Ground Truth 的实际正确率〔附录 `App B.5 Table 4`〕：

   | 智能体 | 记录状态 | `C1 (GPT-4o-mini)` 真实正确率 (%) | `C2 (GPT-4.1-mini)` 真实正确率 (%) | `C3 (GPT-4.1-mini-FT)` 真实正确率 (%) |
   | :--- | :--- | :---: | :---: | :---: |
   | **EHRAgent** | **Retained（被保留记录）** | **44.1%** | **49.1%** | **54.8%** |
   | | **Deleted（被历史淘汰记录）** | 36.3%（低 `7.8%`） | 32.1%（低 `17.0%`） | 48.2%（低 `6.6%`） |
   | **CIC-IoT** | **Retained（被保留记录）** | **78.9%** | **72.2%** | **86.6%** |
   | | **Deleted（被历史淘汰记录）** | 56.7%（低 `22.2%`） | 55.1%（低 `17.1%`） | 61.0%（低 `25.6%`） |

   可以看到，尽管删除过程完全没有接触 Ground Truth（仅依赖同一个粗粒度 LLM Judge 对下游任务的打分），被淘汰记录的真实正确率系统性地比保留记录低 **`6.6% ~ 25.6%`**。这证明**多次下游复用的平均表现对单次 Judge 的评估噪声起到了天然的平滑降噪作用（Law of Large Numbers over Downstream Retrievals）**。

### 3. 任务分布漂移（`Task Distribution Shift`）与显存/容量受限实验（`Sec 4.4–4.5, Fig. 7–8, App A.5 & B.6`）

1. **任务分布漂移下的自适应换血能力（`Sec 4.4:504–531, Fig. 7, App A.5:1222–1227`）**：
   作者使用高斯混合模型（`GMM`）将 `EHRAgent` 与 `AgentDriver` 的测试集嵌入聚类为 **3 个分布截然不同的任务簇**，按簇顺序依次流式输入以制造剧烈的阶段性分布漂移（`Task Distribution Shift`）。实验显示：在每个簇切换边界，无删除或仅定期删除的策略会因旧簇记忆占据检索通道而出现明显性能滑坡；而 **`Combined Deletion` 能够迅速淘汰在新分布下不再被召回的旧簇记忆（通过 $\phi_{\text{per}}$）以及跨簇负迁移的失配记忆（通过 $\phi_{\text{hist}}$），在所有三个分布阶段均维持最高准确率**。
2. **硬性容量上限（`Memory Resource Constraints`）下的表现（`Sec 4.5:532–557, Fig. 8, App B.6 Fig. 16–17`）**：
   当给记忆库施加硬性容量上限（例如限制最大条目数 `MAX_MEMORY_SIZE = 300 / 400 / 500`）时，结合了 `Periodical + History` 的删除机制能够在仅保留 **`20% ~ 30%` 记忆容量**的前提下，达到甚至超越无容量限制（`Unlimited Memory`）的准确率水平。

---

<a id="c13-4"></a>

## 13.4 开源仓 `agent_memory_manage` 源码实现与论文对照（`repos/agent_memory_manage`）

我们对官方仓库 [`papers/repos/agent_memory_manage/`](../../repos/agent_memory_manage/) 进行了逐文件代码级核验。仓库核心文件结构如下：
- [`main_strict.py`](../../repos/agent_memory_manage/main_strict.py)（366 行）：严格评估器（`UniAD` 3s 平均 $L_2 < 2.5\text{m}$）下的流式主循环、写入控制与四类删除策略调度；
- [`main_coarse.py`](../../repos/agent_memory_manage/main_coarse.py)（459 行）：粗粒度 LLM Judge（`GPT-4o-mini / GPT-4.1-mini / FT`）下的流式主循环与二值评分映射；
- [`agentdriver_patch/memory/experience_memory.py`](../../repos/agent_memory_manage/agentdriver_patch/memory/experience_memory.py)（453 行）：经验记忆库核心数据结构、加权高斯核检索、下游效用账本 `success_stats`、`find_worst_memory` 与 `find_dead_memory2` 实现；
- [`agentdriver_patch/memory/memory_agent.py`](../../repos/agent_memory_manage/agentdriver_patch/memory/memory_agent.py)：记忆检索与规划提示词拼装接口。

### 论文表述与源码实现的五处关键差异对账表

| 维度 | 论文正文 / 附录描述 | 开源仓库实际代码实现（附文件与行号） | 工程影响与复现注意点 |
| :--- | :--- | :--- | :--- |
| **1. `Periodical Deletion` 的触发时机** | `Sec 4.1:395–405` 与 `App A.1 Table 3` 表述为以 `Period = 500` 步为周期执行定期清理。 | 在 [`main_strict.py:295–314`](../../repos/agent_memory_manage/main_strict.py#L295-L314) 与 [`experience_memory.py:425–452`](../../repos/agent_memory_manage/agentdriver_patch/memory/experience_memory.py#L425-L452) 中，并**不是每 500 步批量清理一次**，而是在**每一个时间步 `time_step += 1` 结束后都调用 `find_dead_memory2(current_time_step, past_time_window=500)`**：逐条检查若驻留时长 `current_time_step - enter_time >= 500`，且在滑动窗口 `[current_time_step - 500, current_time_step]` 内的被检索次数 `<= RETRIEVAL_TIME_THRESHOLD (2)`，则立即删除。原定批处理函数 `find_dead_memory`（`line 398`）直接抛出 `NotImplementedError("find_dead_memory should never be used in our experiment setting! Use find_dead_memory2 instead.")`。 | 滑动窗口逐步检查比固定每 500 步批处理更平滑，不会在 step 500/1000 处引发记忆库容量的锯齿状断崖下跌。 |
| **2. `History-Based Deletion` 的单步淘汰数量上限** | `Sec 4.1` 公式 $\phi_{\text{hist}}$ 写为指示函数，字面上意味着所有满足 $\operatorname{fr}_t > n$ 且平均效用 $\le \beta$ 的记录都会被同时删除。 | 在 [`experience_memory.py:280–323`](../../repos/agent_memory_manage/agentdriver_patch/memory/experience_memory.py#L280-L323) 的 `find_worst_memory` 中，代码筛出所有 `len(success_stats[token]) >= deletion_retrieval_n_times (5)` 且 `average_L2 > l2_threshold (3.5)` 的候选记录后，按 `average_L2` 从大到小降序排列，**每个时间步最多只删除排名第 1 的最差记录（`return [policy_1_list[0][0]]`）**！ | **单步最多删 1 条（Top-1 Worst Eviction per Step）**是极为关键的工程防抖设计：若某次下游任务失败同时牵连了 Top-$K$ 条被召回记忆，批量全删会导致记忆库瞬间空洞化；单步只淘汰累计均值最差的 1 条能有效防止级联误杀。 |
| **3. 下游效用归因账本 `success_stats` 的初始化与更新机制** | `Sec 4.1` 仅给出累计均值公式 $\frac{1}{\operatorname{fr}_t}\sum \Phi(q_m, e_m)$。 | 在 [`experience_memory.py:67–98, 250–278`](../../repos/agent_memory_manage/agentdriver_patch/memory/experience_memory.py#L67-L98) 中：每条记录入库时初始化 `self.success_stats[token] = [NOT_RETREIVED_L2]`（其中 `NOT_RETREIVED_L2 = -1`）。当该记录首次被后续任务召回并执行 `update_Retrieve_times_and_Success_stats(retrieved_token, L2)`（`line 256–263`）时，先将占位的 `[-1]` 替换为第一次下游任务的实际 `L2`，此后每次被召回则 `.append(L2)`。 | 通过 `[-1]` 占位符区分“从未被检索过的新记录”与“已被检索过的活跃记录”，避免除零错误。 |
| **4. `Coarse` LLM Judge 二值判定向连续误差阈值的反转编码** | `Sec 4.1` 将评估得分定义为越大越好（$\le \beta$ 删除），而 `AgentDriver` 底层代码复用的是误差指标 `L2`（越大越差，`> l2_threshold` 删除）。 | 在 [`main_coarse.py:249, 391–414`](../../repos/agent_memory_manage/main_coarse.py#L391-L414) 中，为了无缝复用 `experience_memory.py` 的 `average_L2 > l2_threshold` 逻辑，代码将 LLM Judge 输出的 `'yes' / 'no'` **反转编码为伪 L2 误差**：Judge 判为成功（`is_success == True`）记为 `L2 = 0.0`，判为失败（`is_success == False`）记为 `L2 = 1.0`，并将淘汰阈值设为 `DELETION_L2_THRESHOLD = 0.5`（即下游被召回 $\ge 5$ 次且失败率 $> 50\%$ 时触发淘汰）。 | 简洁地统一了连续回归/轨迹误差（`L2`）与离散分类/代码/Judge 二值判定的底层淘汰接口。 |
| **5. 记忆库保底容量 `MIN_MEMORY_SIZE` 与硬上限 `MAX_MEMORY_SIZE` 保护** | 正文 `Sec 4.1` 公式未体现容量上下界保护逻辑。 | 在 [`main_strict.py:296, 324–339`](../../repos/agent_memory_manage/main_strict.py#L296-L339) 中：① 任何删除仅在 `current_memory_size > MIN_MEMORY_SIZE` 时才允许执行；② 当达到硬上限 `MAX_MEMORY_SIZE` 时，代码**先无条件写入通过准入的新记忆（`line 265`）**，随后先执行 `find_dead_memory2` 清理冷门记忆；若仍超限，则调用 `find_worst_memory(l2_threshold=-1.0, deletion_retrieval_n_times=-1)` 强制淘汰 1 条历史平均误差最大的已检索记录（注意未检索新记录因 `average_L2 == -1.0` 不满足 `> -1.0`，天然获得“新记录免死保护”！）。 | 赋予新入库记录至少被检索验证一次的机会（避免刚入库就被容量上限挤出），同时严防记忆库被删空。 |

---

<a id="c13-5"></a>

## 13.5 局限性诊断与对我们联接 Agent 主报告的落地启发

### 1. 原文机制的三点局限性

1. **下游任务成败的无差别均摊归因（`Uniform Credit Assignment Across Top-K`）**：当 $K > 1$（如 `RegAgent` $K=6$、`EHRAgent` $K=4$）时，若下游任务 $q_m$ 执行失败，当前机制会将失败惩罚 $\Phi(q_m, e_m)$ 无差别地记入全部 $K$ 条被召回记录的账本中。如果其中 3 条是高质量示例，仅 1 条是强误导性的毒害示例，好示例也会被迫背负连带惩罚（尽管论文通过 $n=5$ 次累计均值与单步只删 Top-1 最差记录缓解了这一问题）。
2. **仅做整条删除（`Hard Deletion`），缺乏对高价值失败教训的重写提炼**：本文处理的是原始 `(Query, Execution)` 对形式的案例级经验（`Case-based Experience`），一旦发现某条记录导致下游表现不佳就直接物理删除；而结合我们在 `04_procedural_memory_reasoningbank.md` 与 `12_procedural_memory_awm.md` 中的分析，部分边界失败案例若能经过反思重写为“反面避坑规则（Counterfactual Pitfall Rules）”而非直接作为正向模仿示例，反而能提供关键的边界约束。
3. **输入相似度函数对表面特征敏感**：正如作者在 `Sec 1` 与 `Sec 4.3` 所指出的，高输入表面相似度 $S_{\text{in}}(q, q_i)$ 并不等价于底层决策条件完全同构——这也是引发 `Misaligned Experience Replay` 的根本原因。

### 2. 对联接 Agent 主报告（第 3.3.3 节与第 3.3.4 节）的直接工程落点

本文为我们的主报告 [`storyline_and_evaluation_merged_technical_route_report.html`](../../../../.lavish/storyline_and_evaluation_merged_technical_route_report.html) 提供了三条核心实证与机制支撑：

1. **为什么经验记忆绝不能“有单据/有轨迹就无脑入库”（支撑 3.3.3 节写入准入红线）**：
   - `Table 1` 四领域全量实证表明，无门控全量写入（`Add all`）因**强经验跟随特性（`Experience-Following Property`）**会触发严重的**错误自举传播（`Error Propagation`）**，性能全线低于完全不更新的静态基线（下跌 `3.7% ~ 12.1%`）。
   - 在我们的网元排障与业务参数调优场景中，历史短时单据、中途取消单据或用户未确认的试探性配置如果直接写入经验记忆，后续遇到相似网元告警时大模型会机械照搬错误参数。因此必须设立两级准入：优先采用确定性网元回执核验（对应 `Strict`：如实际运行无卡顿异常、KPI 达标），在缺乏实时硬件回执的慢路径对话中则使用经领域样本校准的判别器（对应 `Coarse C3`）。
2. **利用“下游复用回执”作为免费质量标签淘汰失配经验（支撑 3.3.4 节 `History-Based Deletion`）**：
   - 借鉴本文 $\phi_{\text{hist}}$ 与 `experience_memory.py` 的 `success_stats` 账本设计：为每条写入程序/经验记忆的规则或案例维护 `(retrieval_count, downstream_success_scores)` 元数据。
   - 当某条经验被检索用于指导新单据生成后，**直接将该下游单据的实际网元运行结果（顺畅/卡顿回执）反向记入被召回经验的效用账本**，无需额外调用大模型做离线审计。
   - 当 `retrieval_count >= n`（如 $n=5$）且下游顺畅率低于阈值 $\beta$ 时，执行**单步最差单条淘汰（`Single-Worst Eviction per Step`）**，并赋予新入库经验 `NOT_RETRIEVED = -1` 的免死保护期，防止刚沉淀的细分场景规则在尚未被验证前就被容量上限误删。
3. **应对用户习惯迁移与基站环境漂移的双通道清理（支撑 3.3.4 节 `Combined Deletion`）**：
   - 结合滑动时间窗冷门清理 $\phi_{\text{per}}$（清理因用户套餐变更或作息迁移而长期不再命中的旧周期规则）与历史效用清理 $\phi_{\text{hist}}$（清理跨场景负迁移的失配规则），在将经验库体积压缩 **`75% ~ 79%`** 的同时进一步提升端到端决策准确率。

---

← 返回 [精读笔记索引](../reading_notes.md)　·　[论文主目录](../../README.md)

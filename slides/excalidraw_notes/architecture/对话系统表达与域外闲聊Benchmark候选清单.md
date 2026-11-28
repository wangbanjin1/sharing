# 对话系统表达变体与域外闲聊 Benchmark 候选清单

本清单用于为电信网络意图提取 Agent 的**意图表达维度（表 2）**、**User↔Agent 交互模式（表 4）**及**域外/闲聊收口边界**寻找权威基准素材，采用两步推进：第一步汇总候选 Benchmark；第二步根据勾选结果精读原文、提炼细分分类体系与典型样例并补入数据集构造流水线。

---

## 一、快速勾选区（第二步优先精读）

- [ ] **B1 · TACT**（EMNLP 2025）— 任务对话与闲聊双向切换（Switch / Recovery）
- [ ] **B2 · FusedChat**（arXiv 2021）— 任务对话与开放域闲聊融合、跨模式指代与省略
- [ ] **B3 · CLINC150**（EMNLP 2019）— 经典域外意图（OOS）检测基准
- [ ] **B4 · AbstentionBench**（2025）— 欠指定、虚假前提与不可答拒答基准
- [ ] **B5 · IndirectRequests**（COLING 2025）— 任务型对话间接语用诉求（吐槽/暗示）
- [ ] **B6 · ClarifyMT-Bench**（2025/2026）— 5 维歧义分类 + 6 种行为模拟用户画像
- [ ] **B7 · ClarifyBench**（2025）— 工具调用 Agent 结构化不确定性多轮消歧
- [ ] **B8 · UserBench**（2025）— 隐含偏好逐步透露与主动澄清环境
- [ ] **B9 · RUT-Bench**（2026）— 非理想、模糊与不配合真实用户行为
- [ ] **B10 · Hy-MultiTurn**（2026）— 6 维长程多轮理解（干扰追踪、长期约束、代词歧义）
- [ ] **B11 · LLMs Get Lost in Multi-Turn**（2025）— 信息分批释放（Sharded）与多轮退化实证

---

## 二、分方向候选明细

### 方向 1：任务对话与闲聊穿插 / 模式切换（补强“域外闲聊快速收口、跑题不丢槽位”）

| 编号 | Benchmark | 年份与来源 | 核心工作内容 | 对当前体系的补盲价值 | 状态 |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **B1** | **TACT** | EMNLP 2025<br>*Beyond Task-Oriented and Chitchat Dialogues* | 统一任务型对话（TOD）与开放域闲聊（Chitchat）的双向自然切换，提出 Switch（切出）与 Recovery（拉回）评测指标 | 直接对应 `I3`“闲聊 1–2 轮温和拉回、跑题不丢槽位”，可借鉴其切换类型分类与拉回评测口径 | 待选取 |
| **B2** | **FusedChat** | arXiv 2021<br>[arXiv:2109.04137](https://arxiv.org/abs/2109.04137) | 将任务型对话与开放域闲聊融合为连续多轮会话，构造跨模式上下文依赖（指代与省略） | 可补充“闲聊中顺带透露业务线索”以及“闲聊与任务交叉指代”的细分场景 | 待选取 |

### 方向 2：域外意图拒识（OOS）与不可答拒答边界（补强“域外拒识、假设咨询与虚假前提”）

| 编号 | Benchmark | 年份与来源 | 核心工作内容 | 对当前体系的补盲价值 | 状态 |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **B3** | **CLINC150** | EMNLP 2019<br>[arXiv:1909.02027](https://arxiv.org/abs/1909.02027) | 任务型对话经典域外意图（Out-of-Scope）评测集，涵盖 150 类域内意图与多类型域外查询 | 对照核查现有域外分类是否遗漏“邻近域越界 / 伪域内”典型类别 | 待选取 |
| **B4** | **AbstentionBench** | arXiv 2025<br>[arXiv:2506.09038](https://arxiv.org/abs/2506.09038) | 评估大模型面对欠指定、病态提问、虚假前提（False Premise）与不可答问题时的拒答能力 | 补充负向表达库中的“虚假前提类提问”（如用户误以为自己是钻石 VIP 询问未生效原因） | 待选取 |

### 方向 3：间接语用、信息缺失与多轮主动澄清（补强“间接吐槽、模糊指代、PER/OCR 边界”）

| 编号 | Benchmark | 年份与来源 | 核心工作内容 | 对当前体系的补盲价值 | 状态 |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **B5** | **IndirectRequests** | COLING 2025<br>*Making Task-Oriented Dialogue Datasets More Natural by Synthetically Generating Indirect User Requests* | 基于 SGD 构造间接用户诉求（如用吐槽暗示需求），提供语言学驱动的间接表达分类与合成范式 | 直接丰富 `I2` 间接语用暗示的细分类型与口语构造公式 | 待选取 |
| **B6** | **ClarifyMT-Bench** | arXiv 2025/2026<br>[arXiv:2512.21120](https://arxiv.org/abs/2512.21120) | 面向多轮对话澄清，提出 5 维歧义分类体系 + 6 种行为多样的模拟用户画像（6,100+ 对话），量化“澄清不足偏差” | 5 维歧义分类可直接补强模糊表达维度，6 种用户画像可直接丰富 User Simulator 风格库 | 待选取 |
| **B7** | **ClarifyBench** | arXiv 2025<br>[arXiv:2511.08798](https://arxiv.org/abs/2511.08798) | 面向工具调用 Agent 的结构化不确定性多轮消歧基准 | 贴合“槽位不全时如何精准发问、减少冗余追问（OCR）”的结构化消歧设计 | 待选取 |
| **B8** | **UserBench** | arXiv 2025<br>[arXiv:2507.22034](https://arxiv.org/abs/2507.22034) | 交互式用户中心评测环境：模拟用户以模糊目标开场、多轮逐步透露隐含偏好 | 与当前“模拟用户持有隐含诉求 + 多轮动态补参”的 Harness 设计高度同构 | 待选取 |

### 方向 4：非理想真实用户行为与长程多轮退化（补强“改口、不配合、长会话防丢约束”）

| 编号 | Benchmark | 年份与来源 | 核心工作内容 | 对当前体系的补盲价值 | 状态 |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **B9** | **RUT-Bench** | arXiv 2026<br>Real-world Uncooperative Tool-calling | 评测工具调用多轮对话中的非理想、模糊与不配合用户行为（答非所问、挤牙膏、前后矛盾等） | 极大丰富表 4 的 User↔Agent 异常交互与不配合用户模拟行为 | 待选取 |
| **B10** | **Hy-MultiTurn** | arXiv 2026<br>*A Six-Dimensional Benchmark for Deep Multi-Turn Dialogue Understanding* | 6 维度深度多轮理解基准，覆盖长对话干扰项追踪、长期约束保持与代词指代歧义（40+ 轮） | 直接对齐 `I3` 长会话关键字段原值保留与跨轮指代追踪 | 待选取 |
| **B11** | **LLMs Get Lost in Multi-Turn** | arXiv 2025<br>[arXiv:2505.06120](https://arxiv.org/abs/2505.06120) | 大规模多轮对话退化实证研究（多轮平均掉点 39%），分析早期歧义与信息分批释放（Sharded Instructions）导致模型锁死错误假设的现象 | 借鉴其“信息分批释放”拆分方式构造多轮渐进式补参难例 | 待选取 |

---

## 三、推荐首轮精读优先级

1. **补强域外与闲聊细分**：`B1 (TACT)` + `B4 (AbstentionBench)`
2. **补强意图表达与模糊澄清细分**：`B5 (IndirectRequests)` + `B6 (ClarifyMT-Bench)` + `B9 (RUT-Bench)`

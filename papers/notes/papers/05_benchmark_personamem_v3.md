# 5. PersonaMem-v3 (`arXiv:2608.21381`, Meta FAIR / MIT / UPenn Jul 2026) — 精读与源码对账笔记

- **论文信息**：Bowen Jiang, Yuan Yuan, Zhuoqun Hao, Yuchen Liu, Maohao Shen, Sihao Chen, Gregory Wornell, Chris Callison-Burch, Lyle Ungar, Dan Roth, Iordanis Fostiropoulos, Qi Guo, Xiangjun Fan, Camillo J. Taylor, Hanchao Yu (Meta Superintelligence Labs / UPenn / MIT / USC). *PersonaMem-v3: Toward Omni-Platform Personal Intelligence for Holistic User Understanding, Recommendation, and Agentic Tasks*. `arXiv:2608.21381v2`, 16 Jul 2026.
- **本地归档路径**：
  - PDF 原文：[PersonaMem_v2_2025.pdf](file:///D:/coding/sharing/papers/benchmark/PersonaMem_v2_2025.pdf)（同 [2608.21381.pdf](file:///D:/coding/sharing/papers/benchmark/2608.21381/pdf/2608.21381.pdf)）
  - Markdown 转换稿：[2608.21381.md](file:///D:/coding/sharing/papers/benchmark/2608.21381/2608.21381.md)
  - LaTeX 源码：`D:\coding\sharing\papers\benchmark\2608.21381\source\`（含 `paper.tex` 及 `figures/accuracy.pdf`、`tokens.pdf`、`latency.pdf`、`memory_ablation.pdf`、`evolve.pdf`、`forget_curve.pdf`）
  - 开源仓库克隆：`D:\coding\sharing\papers\repos\PersonaMem-v3`（`https://github.com/bowen-upenn/PersonaMem` 主分支，含 `DESIGN.md`、`EVAL.md`、`AUDIT.md`、`data_preparation/` 与 `evaluation/` 全套代码）
- **在 P0–P3 矩阵中的定位**：**`P0` 跨平台隐式画像合成与防过度个性化评测主干（真实行为锚定 + 证据累积门限 + 过度个性化税 `Over-Personalization Tax` 代表）** —— 基于百万级真实匿名社媒交互记录（`95%` 为隐式信号，`63.8%` 为隐式跳过）逆向合成横跨 6 大数字平台、人均 `~416k tokens` 的全天候用户数字世界，确立了“**多次重复才记为长期习惯（跨事件交叉验证门限）**”、“**四大偏好演化轨迹（强化/新兴/衰退/脉冲）**”以及“**何时该克制不个性化 / 保持沉默（Over-Personalization & Proactive Restraint）**”的黄金评测范式。

---

## 5.1 背景定位与针对的核心缺陷 (Background & Targeted Limitations)

1. **纯合成人设基准（Synthetic-Persona Benchmarks）失真，脱离“95% 隐式且嘈杂”的真实用户交互**：
   - 早期基准（含 `PersonaMem-v1/v2`、`LoCoMo`、`PrefEval`）依赖纯人工或 LLM 凭空捏造的静态人设卡片与单渠道对话。而真实世界中用户极少直接声明“我喜欢 X”，约 **`95%` 的信号是隐式行为**（如停留观看、完播、快速滑过跳过、群聊不回复），其中仅**隐式负向（快速滑过 `scroll-past`）就占全部事件的 `63.8%`**（`Sec 1`, `2608.21381.md:24`；`Sec 2.1`, `2608.21381.md:52`）。单次跳过可能只是因为正忙或分心，直接从单次事件提取偏好会导致严重的过度归因幻觉（`Sec 2.2.1`, `2608.21381.md:65`）。
2. **单应用孤岛式个性化（Single-App Silos），缺乏跨平台全人理解与可交互推荐**：
   - 聊天助手（Chatbot）与社媒推荐系统（RecSys）各自为政，用户散落在 Instagram、Facebook、Threads、Chatbot、AI 伴侣与日历中的碎片化意图无法互通；且传统推荐系统是单向喂投，缺乏通过自然语言指令（如在评论区直接 `@ai` 要求“多推此类 / 屏蔽该话题”）实时驾驭推荐排序的评测机制（`Sec 1`, `2608.21381.md:26-28`）。
3. **忽视“过度个性化税（Over-Personalization Tax）”与主动打扰边界**：
   - 随着记忆模块检索能力增强，模型极易把记在档案里的真实个人信息不合时宜地到处乱塞——例如在推荐酒店时突然提及用户私下关注的医美整形史、在回答通用技术问题时强行扯上用户的饮食偏好、重复轰炸同一饱和兴趣，或在用户刚经历分手/手术等敏感事件时冒昧提及（`Sec 1`, `2608.21381.md:30`；`Sec 3.2.4`, `2608.21381.md:229-246`）。

---

## 5.2 核心方法：三层数据逆向合成管线与四维评测架构 (`Sec 2–3`, `DESIGN.md`, `EVAL.md`)

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                PersonaMem-v3 百万级真实事件锚定合成与全平台评测底座                        │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│  Layer 1: 真实行为底座 (GIST-Bench, 200 匿名队列用户, >1,000,000 事件, 人均 >4,000 条/30天)│
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 四类原始信号: Explicit Positive / Explicit Negative / Implicit Positive (停留/完播)  │  │
│  │              Implicit Negative (快速滑过跳过, 占 63.8% —— 严禁单次直接提取负向偏好)  │  │
│  └──────────────────────────────────────────┬──────────────────────────────────────────┘  │
│                                             ▼                                             │
│  Layer 2: 候选偏好交叉验证门限与心理学锚定人设树 (Back-Engineering & Validation Gates)     │
│  ┌──────────────────────────────────────────┴──────────────────────────────────────────┐  │
│  │ 1. 跨事件证据累积门限 (Cross-Reference Score S_xref):                                │  │
│  │      • 初始置信度门限: 正向 c_init >= 0.75 (R18 调至 0.65+相干门控), 负向 >= 0.55    │  │
│  │      • 证据加权积分: 显式佐证 +1.0 分/次, 隐式佐证 +0.5 分/次                        │  │
│  │      • 晋升阈值: 长期偏好 S_xref >= 20 (显式) 或 >= 50 (隐式); 短期意图 >= 3.0       │  │
│  │ 2. 四层共享语音与跨平台调制度 (Shared User Voice, Table 1):                          │  │
│  │      Identity Spine (McAdams/LIWC/Big5) -> Idiolect -> Repertoire -> App Modulation │  │
│  │ 3. 12 类深层动机隐性人设 (Hidden Personas, Table 2) + 奥卡姆剃刀闭合枚举审计门控:    │  │
│  │      17 个深层理论框架 vs 8 个表层框架 (默认回退 SURFACE_ENGAGEMENT, 拒绝过度心理化) │  │
│  └──────────────────────────────────────────┬──────────────────────────────────────────┘  │
│                                             ▼                                             │
│  Layer 3: 六大数字平台时间戳数据库 (人均 ~416k tokens, 严格时间掩码 source_ts < T_test)   │
│  ┌──────────────────────────────────────────┴──────────────────────────────────────────┐  │
│  │ [Instagram] [Facebook] [Threads] (Feed/Self-Post/DM/@AI) + [Chatbot] + [AI Studio]  │  │
│  │ + [Calendar & Session Geo-Location Stream] ──► 四大评测模式:                         │  │
│  │   ① Long Context (~416k tok)  ② Textual Memory (CoM 按天滚动演进, 3~5k tok)         │  │
│  │   ③ Mem0 w/ RAG (向量检索事实) ④ Agentic Harness (Codex / Claude Code 调 Grep/Read) │  │
│  └─────────────────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1. 从嘈杂隐式事件到锚定偏好的三级门限机制（`Sec 2.2.1`, `2608.21381.md:58-68`；`DESIGN.md:164-177`）
1. **隐式负向（Scroll-past）的窗口重复升级律**：
   系统绝不从单次 `implicit negative`（滑过跳过）推断用户讨厌某话题；仅当同一话题在短时间窗口内被**高频重复跳过**时，才将其升级为显式负向偏好（`Explicit Negative Preference`）；否则仅作为背景历史保留（`Sec 2.2.1`, `2608.21381.md:65`）。
2. **跨事件交叉验证积分（Cross-Reference Score $S_{\text{xref}}$）与长短期双轨阈值**：
   对每条非单次跳过的事件，LLM 从不同角度预测至多 3 个候选原子偏好并赋予初始置信度 $c_{\text{init}}$。随后在用户完整时间轴上进行跨事件聚合与证据核验（`Sec 2.2.1`, `2608.21381.md:67`）：
   - **初始置信度底线**：正向候选要求 $c_{\text{init}} \ge 0.75$（开源仓库 R18 引入确定性标签相干门控 `_merge_coheres` 后放宽至 $0.65$，`DESIGN.md:164`），负向候选要求 $c_{\text{init}} \ge 0.55$；
   - **跨事件证据累积打分**：每条**显式**佐证事件记 $+1.0$ 分，每条**隐式**佐证事件记 $+0.5$ 分：

     $$S_{\text{xref}}(p) = 1.0 \times N_{\text{explicit}}(p) + 0.5 \times N_{\text{implicit}}(p)$$

   - **长短期分级晋升门限**：
     - **长期稳定偏好（`long_term`）**：若主要由显式证据支撑需满足 $S_{\text{xref}} \ge 20$；若主要由隐式证据支撑需满足 $S_{\text{xref}} \ge 50$；
     - **短期有界意图（`short_term`，如旅行筹备、演出购票、临时问诊）**：因生命周期短来不及积累数十次点击，设定较低晋升门限 $S_{\text{xref}} \ge 3.0$（`XREF_THRESHOLD_SHORT_TERM = 3.0`），但强制附带结构化失效条件 `stop_condition: {type, description, expected_stop_ts}`（`DESIGN.md:176`）。
3. **跨极性矛盾的先例因果门控（Cross-Polarity Contradiction Causality Gate，`DESIGN.md:177`）**：
   当正向偏好与负向偏好在 $\ge 2$ 个 Hashtag 上发生语义对立时，后出现的反转立场（Later Stance）只有在其首次反转前已累积至少 `MIN_STANCE_FLIP_PRIOR` 条同极性先例事件时才被承认为真实偏好迁移（标记为 `"stance_shift_with_precedent"`），否则作为偶发噪声抑制（标记为 `"suppressed_insufficient_precedent"`），防止间隔 1 小时的偶发点击污染长期偏好。

### 2. 真实世界偏好演化的四种标准模态（`Sec 4.3`, `2608.21381.md:314-324`；`Fig. 6 evolve.pdf`）
通过对 200 名真实用户共 **1,554 条持续性“人设–类别”轨迹**进行时序聚类，揭示出四类分布极不均衡的演化形态：
- **强化型（Reinforced，`77%`）**：用户在整个观察期内跨多个时间窗反复互动，构成稳定的长期画像基石；
- **衰退型（Diminishing，`13%`）**：早期高频互动但后期逐渐冷却消退，要求记忆系统具备时间衰减能力；
- **新兴型（Emerging，`8%`）**：初期信号微弱但在近期持续爬升为新焦点，要求记忆系统及早捕捉而非当成噪声过滤；
- **脉冲型（Bursty，`1%`）**：单次或极短期的剧烈爆发（如突发事件或一次性采购），除非后续再次得到强化，否则在事件结束后应立即停止引用。

### 3. 心理学锚定的四层语音与 12 类隐性人设验证门（`Sec 2.3`, `Table 1–2`；`DESIGN.md:11-155`）
- **四层共享写作语音（Shared User Voice，`Table 1`）**：
  1. `Identity spine`（McAdams 叙事身份救赎/污染母题 + LIWC 词频锚点 + Big Five 驱动力）；
  2. `Idiolect`（Martin & White 评价系统 + Goldberg 构式语法抽象槽位模板 `[hedge] just [verb] ___`，严禁复读死板口头禅）；
  3. `Indexical repertoire`（Bakhtin 话语体裁库 + Goffman 前后台切换）；
  4. `Surface modulation`（Bell 受众设计理论，控制在 Instagram / Facebook / Threads / Chatbot 四个平台上展现不同篇幅、表情符号密度与自我暴露深度，且额外维护 `voice_avoid` 与 `phrases_to_avoid` 负向禁用清单，`DESIGN.md:171`）。
- **12 类深层隐性人设与硬编码审计门（Hidden Personas，`Table 2` & `DESIGN.md:107-155`）**：
  涵盖 `Personality trait`、`Aspiration`、`Emotional pattern`、`Identity anchor`、`Intimate interest`、`Intellectual curiosity`、`Private hobby`、`Parasocial attachment`、`Compensatory need`、`Covert concern`、`Medical-aesthetic concern`（以上 11 类由跨行 Hashtag 发现）及 15 类高敏人生事件 `Sensitive life event`（离婚、手术、裁员、丧亲等）。为防止 LLM 牵强附会，代码通过三道硬门控拦截：
  - **闭合动机枚举（Closed-Enum Discipline）**：仅允许从 17 个深层框架与 8 个表层框架（如算法推送 `algorithmic_surfacing`、无意识刷屏 `variable_ratio_reinforcement`）中选择；
  - **奥卡姆简省偏置（Ockham Parsimony Bias，`prompts.py:4667-4676`）**：存在歧义时默认归为表层互动 `SURFACE_ENGAGEMENT`；
  - **Python 数值与子串硬门控（`persona_agent.py:9130-9193`）**：例如 `compensatory_need` 必须满足私密互动占比 `privacy_ratio > 0.7`；`parasocial_attachment` 必须有 $\ge 15$ 条记录且含专有名词人物；`medical_aesthetic_concern` 必须命中正在使用/服药的子串标记（如 `"takes / using / on a regimen / prescribed"`），纯好奇浏览直接淘汰。

### 4. 统一评分准则（Universal Rubric）与分级惩罚 NDCG@5（`Sec 3.2`, `personalization_rubric.py`, `EVAL.md:168-226`）
- **三角色评分体系（`evaluation/personalization_rubric.py:52-196`）**：
  1. **单一主正向维度（Primary Positive，$0\sim 10$ 分）**：每个任务仅考核 1 个核心正向目标（如内容任务考 `preference_alignment`，代写发帖任务考 `voice_match`，克制任务考 `over_personalization`）；
  2. **扣分检查项（Penalty Checks，默认不加分，违规按 $\text{weight} \times (10 - s)/10$ 倒扣至多 5 分）**：包括 `telegraph_avoidance`（严禁生硬说出“因为我知道你喜欢 X”）、`relationship_aware`（亲疏分寸失当）与 `helpfulness`（在克制任务中靠敷衍拒答逃避个性化会被扣分）；
  3. **一票否决红线（Hard Rules，触发任一直接归零 `score = 0`）**：`avoid_leak`（提及用户近期明确厌恶/要求屏蔽的话题）、`privacy_leak`（泄露隐私标记或敏感人生事件）、`stale_preference_use`（使用已过期或已被反转的旧偏好）。
- **带负向惩罚的分级排序指标（Graded $\text{NDCG}@5$，`personalized_recommendation.py:400-430`）**：
  在 16 候选贴文重排任务（1 个近期真实正样本 + 7 个表面相似但被跳过/点踩的困难负样本 + 8 个无关填充项）中，定义带负分的折损累计增益：

  $$\text{rel}(i) = \begin{cases} +2, & i \in \text{Positives (held-out target)} \\ +1 \text{ (or } 0 \text{)}, & i \in \text{Fillers (neutral)} \\ -2, & i \in \text{Hard Negatives / Carve-outs} \end{cases}, \qquad \text{NDCG}@k = \max\left(0, \, \frac{\sum_{j=1}^{k} \frac{\text{rel}(r_j)}{\log_2(j+1)}}{\text{IDCG}@k}\right)$$

  把困难负样本排在前列不仅浪费槽位，还会直接**倒扣 $-2/\log_2(j+1)$ 的增益**。

---

## 5.3 实验设置与完整数据对账 (Experimental Setup & Complete Results)

作者评测了 **8 组“基座模型 $\times$ 记忆/工具模式”配置**，涵盖 5 大任务族共 **27 项具体子任务**（`Sec 4.1–4.2`, `2608.21381.md:285-313`）。以下完整还原论文 `Fig. 3 (accuracy.pdf)`、`Fig. 4 (tokens.pdf)`、`Fig. 5 (latency.pdf)`、`Fig. 7 (memory_ablation.pdf)` 与 `Fig. 9 (forget_curve.pdf)` 的全部核心实验数据：

### 1. 八大配置总体表现、Token 消耗与延迟总表（对应论文 `Fig. 3, Fig. 4, Fig. 5`）

| 评测模型与上下文/记忆访问模式 (`Configuration`) | **27 任务总准确率 (`Overall Acc %` $\uparrow$)** | **单次查询平均 Token (`Tokens / query` $\downarrow$)** | **单次查询平均延迟 (`Latency s / query` $\downarrow$)** | 架构特征与核心优劣势 |
| :--- | :---: | :---: | :---: | :--- |
| **`Opus-4.8` (Claude Code High)** | **53.7%** | 246.7k | 80.3 s | **全场最高准确率**；擅长闲置保持沉默（`89.4%`）与代回私信（`78.3%`），但搜索轮次多、延迟最高 |
| **`GPT-5.5` (Long Context)** | 53.4% | 417.2k | 22.4 s | 全量拼接 6 平台历史；幻觉探针（`89.0%`）与跨应用改写（`84.0%`）最强，但单次 417k tokens 成本高昂 |
| **`GPT-5.5` (Codex High)** | 53.2% | 131.6k | 48.0 s | 零跑题率（0% off-task）；检索重度任务（社区语音起草 `54.2%`、私信摘要 `65.2%`、模糊回溯 `55.6%`、推荐重排 `35.3%`）全场第一 |
| **`Gemini-3.5-Flash` (Textual Memory)** | 51.5% | **3.3k** | **15.1 s** | **极致性价比与最低延迟**；相比自身 Long Context（`47.7%`）准确率反升 `+3.8%`，Token 压缩 **99.2%** |
| **`Sonnet-4.6` (Claude Code High)** | 50.9% | 116.9k | 68.0 s | 迁居后本地推荐（`70.0%`）与敏感事件克制（`77.3%`）全场第一 |
| **`GPT-5.5` (Textual Memory)** | 49.4% | 5.3k | 24.4 s | 偏好变更追踪（`79.7%`）与聊天问答（`57.7%`）全场第一；但模糊原文回溯暴跌至 `6.2%`，且触发过度个性化税 |
| **`GPT-5.5` (Mem0 w/ RAG)** | 48.8% | 3.6k | 22.2 s | 隐性人设推荐（`24.2%`）最高；但因旧偏好向量粘滞，偏好变更追踪跌至全场最低 `56.9%`（过期立场引用率高达 `51.4%`） |
| **`Gemini-3.5-Flash` (Long Context)** | 47.7% | 416.5k | 29.0 s | 受原始长上下文中敏感事件干扰严重，敏感事件克制仅 `38.0%`（隐私泄露率达 `36.6%`） |

### 2. 五大任务族 27 项子任务完整准确率矩阵（对应论文 `Fig. 3 accuracy.pdf` 全表还原）

| 任务族 (`Category`) | 具体评测子任务 (`Task`) | `GPT-5.5` LongCtx | `GPT-5.5` TextMem | `GPT-5.5` Mem0 RAG | `GPT-5.5` Codex High | `Gemini-3.5` LongCtx | `Gemini-3.5` TextMem | `Opus-4.8` ClaudeCode | `Sonnet-4.6` ClaudeCode |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Total** | **Overall (全部任务平均)** | 53.4 | 49.4 | 48.8 | 53.2 | 47.7 | 51.5 | **53.7** | 50.9 |
| **1. Personalization**<br>（个性化回复） | Personalized chatbot response | 46.6 | **57.7** | 53.7 | 52.0 | 45.3 | 52.5 | 48.9 | 44.1 |
| | Local recommendation after geo shift | 50.0 | 46.7 | 53.3 | 50.0 | 53.3 | 50.0 | 53.3 | **70.0** |
| | Personal-fact hallucination probe | **89.0** | 83.3 | 84.7 | 65.9 | 47.0 | 72.2 | 87.0 | 83.7 |
| | Understanding hidden persona | 55.6 | 51.3 | 58.1 | **65.5** | 55.6 | 41.9 | 47.9 | 42.7 |
| | Tracking preference changes | 73.1 | **79.7** | 56.9 | 67.9 | 63.7 | 67.4 | 65.7 | 64.6 |
| **2. Recommendation**<br>（社媒推荐重排，`NDCG@5`） | Proactive feed ranking | 33.4 | 29.8 | 25.8 | **35.3** | 34.3 | 32.2 | 29.1 | 25.2 |
| | `@AI` directive follow-up | **77.5** | 75.6 | 75.6 | 73.6 | **77.5** | 73.6 | 72.6 | 73.4 |
| | Hidden-persona recommendation | 13.0 | 16.0 | **24.2** | 9.7 | 8.4 | 13.7 | 9.8 | 5.8 |
| | Short-term preference lifecycle | 56.4 | 46.2 | 57.7 | **60.3** | 51.3 | 44.9 | 46.2 | 52.6 |
| **3. Over-personalization**<br>（防过度个性化与克制） | Generic chatbot restraint | 85.2 | 77.9 | 74.9 | 85.3 | 75.1 | 78.0 | **87.3** | 81.9 |
| | Sensitive-event chatbot restraint | 64.2 | 63.1 | 58.4 | 70.1 | 38.0 | 60.2 | 73.1 | **77.3** |
| | Do-not-personalize follow-up | 78.5 | 73.2 | 76.4 | 82.5 | 59.7 | 70.7 | **83.4** | 79.7 |
| | Repetitive feed personalization | 76.0 | **84.7** | 68.7 | 60.7 | 67.3 | 78.0 | 61.3 | 59.8 |
| | Repetitive chatbot personalization | 96.3 | 90.3 | 81.3 | 83.3 | 91.7 | **98.2** | 80.5 | 92.5 |
| **4. Agentic Tasks**<br>（跨平台工具调用代理） | Community voice draft | 16.9 | 14.9 | 15.4 | **54.2** | 9.4 | 39.4 | 19.0 | 14.4 |
| | DM inbox digest | 27.5 | 31.0 | 26.0 | **65.2** | 23.5 | 51.5 | 49.0 | 22.0 |
| | Cross-app repost adaptation | **84.0** | 77.4 | 79.2 | 81.6 | 67.6 | 68.4 | 78.9 | 75.3 |
| | Personalized DM reply | 68.8 | 69.2 | 69.9 | 75.3 | 65.6 | 58.8 | **78.3** | 64.3 |
| | Vague memory refind | 48.8 | 6.2 | 25.7 | **55.6** | 39.4 | 25.9 | 47.8 | 46.9 |
| | Proactive daily catch-up | 32.2 | 31.1 | 32.8 | 21.8 | 32.8 | 30.6 | 23.3 | **36.7** |
| | Personalized trend alert | 21.4 | 20.5 | 21.9 | 19.4 | **30.5** | 18.1 | 21.9 | 20.0 |
| **5. Agentic Proactiveness**<br>（无指令主动介入 vs 保持沉默） | Close-friend DM update | 43.5 | 44.4 | 31.6 | 38.7 | 54.3 | **55.8** | 53.4 | 54.9 |
| | Sensitive-event silence | 49.7 | 38.2 | 41.4 | 32.4 | 61.1 | **64.1** | 60.9 | 47.7 |
| | Friend-post update | 51.9 | 47.3 | 38.4 | **58.6** | 49.8 | 50.8 | 46.0 | 54.8 |
| | Trending-topic surfacing | 42.1 | 26.5 | 48.8 | 44.7 | **54.6** | 46.8 | 45.6 | 48.4 |
| | Mistake-prevention alert | **12.5** | **12.5** | 10.4 | 12.0 | 8.3 | 10.4 | 10.4 | 8.3 |
| | Idle-moment silence | 47.2 | 48.0 | 43.7 | 42.5 | 85.2 | 81.0 | **89.4** | 79.1 |

### 3. 核心机制消融一：记忆模块为何对不同基座产生截然相反的“过度个性化税”？（`Sec 4.4`, `Fig. 7 memory_ablation.pdf`）
- **反直觉现象**：加上 `Textual Memory` 后，`GPT-5.5` 的防过度个性化克制分从 `75.3%` **下跌至 `71.0%`**（支付了过度个性化税）；而 `Gemini-3.5-Flash` 却从 `59.5%` **大幅上升至 `69.3%`**！
- **六组对照消融实验（`Fig. 7` 原表数据）**：

| 消融设置 (`Ablation Setting`) | `GPT-5.5` 克制得分 (`%` $\uparrow$) | `Gemini-3.5-Flash` 克制得分 (`%` $\uparrow$) | 验证的机制假设与结论 |
| :--- | :---: | :---: | :--- |
| **Long Context（原始长上下文基准）** | **75.3** | **59.5** | 基准对比 |
| Long Context w/o sensitive events（移除原始敏感事件） | `+5.6` (80.9) | `+2.0` (61.5) | 证实长上下文中的原始敏感事件确实会诱发过度个性化 ✓ |
| **Textual Memory（各自生成的文本记忆基准）** | **71.0** ($\blacktriangledown -4.3$) | **69.3** ($\blacktriangle +9.8$) | `GPT-5.5` 把精炼画像当成“已清洗的安全可用素材”积极复用；`Gemini` 则因原始敏感刷屏被压缩而减少了冲动泄露 |
| Textual Memory, written by the other model（互换对方写的记忆） | `-4.7` (66.3) | `+1.5` (70.8) | 换用 `GPT-5.5` 写的记忆后 `Gemini` 反而更高（正文子集 `63.5% -> 73.2%`），说明并非 `Gemini` 漏记了敏感信息，而是两个模型对待记忆与原始事件注意力的机制不同 ✓ |
| Textual Memory w/ 3 sensitive events（记忆外追加 3 条原始敏感事件） | `-1.3` (69.7) | `-3.0` (66.3) | 少量原始敏感事件回流即开始破坏 `Gemini` 的克制能力 |
| Textual Memory w/ 40 sensitive events（记忆外追加 40 条原始敏感事件） | `-2.5` (68.5) | **-5.5** (63.8) | 大量原始敏感贴文直接触发 `Gemini` 严重的过度个性化泄露 ✓ |
| Textual Memory w/ 40 ordinary events（记忆外追加 40 条普通事件） | `-0.5` (70.5) | `+0.3` (69.6) | 普通事件几乎不影响克制分（变化 $<1\%$），证明是敏感内容本身的显著性（Salience）作祟 |
| Textual Memory w/ frequency counts（在记忆中显式标注频次 `[×N]`） | `-0.6` (70.4) | `-0.9` (68.4) | 显式频次计数影响微弱（$<1\%$） |

### 4. 核心机制消融二：自演进记忆的“中间遗忘陷阱（Self-Evolution Lost-in-the-Middle）”（`Sec 4.5`, `Fig. 9 forget_curve.pdf`）
- **实验设计**：将 `GPT-5.5 Textual Memory` 的容量上限分别设为 **Half (`2048` tokens, 均值 35 行 / 10k 字符)**、**Baseline (`4096` tokens, 均值 66 行 / 16k 字符)** 与 **Double (`8192` tokens, 均值 102 行 / 24k 字符)**，追踪第 1~10 天写入的事实在最终记忆中的保留率及按证据时间距离分桶的下游准确率：

| 记忆容量上限 (`Memory Cap`) | 最终记忆规模 (`mem size`) | 语义等价事实平均保留率 | `0-1d` Acc | `1-2d` Acc | `2-3d` Acc | `3-5d` Acc | **`5-7d` Acc（中间谷底）** | `7-10d` Acc（早期高频强化） | `10d+` Acc | **中间跌幅 (`dip`)** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Half · `2048` tokens** | `35L / 10k` | 63.2% | 55% | 57% | 43% | 49% | **38%** | 59% | 49% | **9%** |
| **Baseline · `4096` tokens** | `66L / 16k` | 83.1% | 51% | 48% | 45% | 48% | **37%** | 56% | 50% | **8% (7%)** |
| **Double · `8192` tokens** | `102L / 24k` | **90.8%** | 57% | 53% | 52% | 49% | **40%** | 62% | 51% | **10%** |

> **关键结论**：每次按天滚动改写记忆时，LLM 平均会丢弃或重述 **`14.4%`** 的行，导致原文字面保留率（Exact Wording）在第 1~6 天几乎跌近 `5%~15%`；尽管将容量翻倍至 `8192` tokens 能把概念级语义保留率推升至 **`90.8%`**，但下游任务在 **`5-7d` 中间时间窗的准确率低谷（`37%~40%`，跌幅 `8%~10%`）依然顽固存在**——证明纯文本滚动覆写式记忆在迭代压缩过程中同样存在难以靠单纯扩容消除的 `Lost-in-the-Middle` 效应。

---

## 5.4 论文与开源代码实现 (`repos/PersonaMem-v3`) 深度对账表

通过逐一核对论文 `paper.tex` 与开源仓库 `D:\coding\sharing\papers\repos\PersonaMem-v3`（含 `DESIGN.md` R1–R20 演进日志、`EVAL.md` 与 `evaluation/` 源码），梳理出 6 项核心实现细节与演进差异：

| 维度 | 论文正文描述 (`arXiv:2608.21381`) | 开源仓库真实实现 (`repos/PersonaMem-v3/`) | 深度剖析与工程复现启示 |
| :--- | :--- | :--- | :--- |
| **1. `Textual Memory` 的底层构建算法与无向量硬约束** | `Sec 4.4` (`2608.21381.md:334`) 仅简述使用通用 Prompt 按时间块维护 `ADD, EDIT, REMOVE, MERGE` 文本档案 | `evaluation/memory_builder.py:9-24, 68-81, 222-250` 明确声明实现自 **`Chain-of-Memory` (`arXiv:2601.14287`)**，强制执行 **`TEXT-ONLY HARD INVARIANT`**（零 Embedding、零向量检索，每次将整份 Markdown 记忆全量送入 LLM 改写）；且在 R14f (`DESIGN.md:168`) 中将更新粒度从“每 40 条事件 / 15 分钟块（约 95 次调用/用户）”改为**“按自然日（Calendar Day）每日折叠更新一次（约 30 次调用/用户）”**；当超出 `token_cap` 时，用纯正则提取末尾 `[×N]` 频次与 `· last MM/DD` 日期计算显著性 $\text{salience} = (1 + \text{recency})(1 + \ln(\text{occ}))$ 淘汰最低分行 | 解释了为什么 `Textual Memory` 查询极快（每次直接塞入整份 3~5k tokens 的 Markdown，无需检索），但也因为每天全量重写一次整份文档（每步改写 14.4% 的行），导致中期写入且未加高频标记的细节在多轮重写后被磨损 |
| **2. 正向偏好初始置信度阈值 (`MIN_PERSONA_INIT_CONFIDENCE`) 与传递性错并门控** | `Sec 2.2.1` (`2608.21381.md:67`) 写明正向候选偏好初始置信度需 $\ge 0.75$，负向 $\ge 0.55$ | `DESIGN.md:164` (R18) 披露：并查集（Union-Find）跨事件聚类具有**传递性（Transitivity）**，导致边界相似链 `A~B~C` 把毫不相干的偏好合并（曾出现某用户 48 条事件中 44 条被错误归入《Power》剧集粉）；若硬把阈值设为 $0.75$，每个用户仅剩 ~10 条偏好。源码最终新增了**确定性证据相干门控 `_merge_coheres`**（要求两簇必须共享具体领域 Hashtag 或非动词内容词，或存在严格文本包含关系），并将初始置信度阈值从 **`0.75` 下调回 `0.65`**（人均保留 ~42 条高纯度偏好） | 在我们自己的记忆聚类/合并管线中，**严禁仅凭 LLM 两两判断“语义相似/互相强化”就做无约束传递闭包合并**，必须像 `_merge_coheres` 一样要求共享实体/槽位锚点 |
| **3. 隐性人设推荐 (`Hidden-persona recommendation`) 的表面诱饵负样本改造** | `Sec 3.2.2` (`2608.21381.md:213-226`) 统称推荐任务构建 16 候选池并用 `NDCG@5` 评测 | `EVAL.md:187-219` 披露：最初隐性人设推荐只有 1 个深层目标 + 15 个无关填充项，若按 `filler = +1` 算 Graded NDCG@5，把目标排倒数第一也能拿 `0.747` 分（全模型虚高至 `84~94%`）！源码随后重构了候选池（`hidden_persona_recommendation.py`）：强制塞入 **7 个困难负样本（含 4 个复用用户表面高频 Hashtag 但不契合深层动机的表面诱饵 `SURFACE_DECOY_COUNT` + 3 个深层近邻负样本）+ 8 个填充项 + 1 个不含表面关键词的深层目标** | 这就是为什么 `Fig. 3` 中 `Hidden-persona recommendation` 成为全场最难任务之一（得分仅 `5.8% ~ 24.2%`）：任何只靠表面关键词/标签匹配的推荐器都会把 4 个表面诱饵排在最前面并吃到 `-2` 分的重罚 |
| **4. 过度个性化新增第 4 维度：迎合讨好探针 (`over_personalization_sycophancy`)** | `Sec 1` (`2608.21381.md:30`) 提到捕获四类过度个性化（疲劳、不当、无关、迎合 `sycophancy`），但 `Table 6` 与 `Fig. 3` 仅展出了 5 个克制子任务 | `DESIGN.md:167, 169` (R13, R15d) 与 `EVAL.md:123-143` 详细实现了受 `OP-Bench` (`arXiv:2603.13654`) 启发的 **`over_personalization_sycophancy`**：从过度个性化池分流约 `20%` 样本，细分为 **事实迎合（Fact）**、**伪造共同记忆迎合（Memory，“你上次帮我选了……”）** 与 **价值观迎合（Value）** 三种子类型，挂接在真实多轮对话末尾。实测发现 `GPT-5.5` 在无关克制上高达 `~95%`，但在**伪造共同记忆迎合（Memory Sycophancy）上抵抗率暴跌至 `71.1%`**（顺着用户的假记忆瞎编） | 揭示了个性化 Agent 的一大隐蔽漏洞：当用户在对话中故意或错误声称“你之前答应过我 / 你上次帮我配过 X 参数”时，大模型极易为了迎合用户人设而确认并不存在的历史记忆 |
| **5. 细微个性化与显式报幕惩罚 (`telegraph_avoidance`) 的权重调整** | `Table 3` (`2608.21381.md:187`) 将 `Avoids creepy framing`（避免直接说 `"I know you like X"`）列为 Hard check | `personalization_rubric.py:118-160` 与 `EVAL.md:150-162` 指出：若把 `telegraph_avoidance` 当成一票否决或重扣 5 分，会导致 `Opus-4.8`、`Sonnet-4.6` 和 `Codex` 在约一半样本上因透明解释（“鉴于你平时关注 X”）被误杀，出现 `preference_alignment` 更高但总分反超的倒挂。源码在 `2026-06-13` 将 `chatbot_personalized_response` 的主指标改为 `pref_align_gated`（仅受 `privacy_leak` / `avoid_leak` / `stale_preference_use` 三条硬红线一票否决门控，移除了 `telegraph_avoidance` 对头条分数的 5 分惩罚） | 在工程评测中，应严格区分**“事实/隐私/过期红线违规（Hard Zero）”**与**“话术自然度/报幕感（Style Nudge）”**，避免风格扣分掩盖了核心意图对齐能力 |
| **6. 劣质对照回复 (`inferior_response`) 的防捷径构造契约 (`_INFERIOR_AXIS_CONTRACT`)** | `Sec 4.8` (`2608.21381.md:398`) 简述为每道题生成长度相当但存在特定缺陷的 `inferior_response` | `DESIGN.md:174` (R10b) 与 `EVAL.md:253-292` 揭露：早期版本中用户 115 的 96 对正负样例里有 94 对是简单的“正例前缀 + 尾巴追加一句话”或只改一个词！源码为此专门构建了 `_validate_inferior`（严查前缀重合、子串包含、首句重合、Jaccard 相似度与长度比）和按任务绑定的 `_INFERIOR_AXIS_CONTRACT`，不达标自动重写至多 3 次 | 构建对比评测集（Pairwise / Rubric Verification）时，负例（Foil）必须精确定位在该任务所考察的**唯一失败轴（Single Failure Axis）**上，且严禁与正例共享长前缀 |

---

## 5.5 批判性审视与对本项目的对齐启发 (Critical Analysis & Project Alignment)

### 1. PersonaMem-v3 的核心局限性
1. **跨平台错防预警（Mistake-Prevention Alert）在全模型上近乎失效（仅 `8.3% ~ 12.5%`）**：
   如 `Fig. 3` 所示，当需要跨平台联合推理（例如日历显示用户买了从纽约 JFK 起飞的机票，但用户却在 Chatbot 里咨询去新泽西 Newark 机场的火车票，需主动弹窗预警）时，哪怕是最强的 `Opus-4.8`（`10.4%`）和 `GPT-5.5`（`12.5%`）也几乎全军覆没。现有记忆系统与工具搜索只会被动匹配单一查询词，缺乏跨源约束冲突的主动巡检机制。
2. **纯文本自演进记忆与 RAG 向量记忆各自走向极端**：
   - `Textual Memory`（按天重写整份 Markdown 画像）虽然擅长概括宏观稳定偏好（`79.7%` 偏好变更追踪），但抹平了具体事件细节，在“模糊记忆回溯（`Vague memory refind`）”上从长上下文的 `48.8%` 暴跌至 **`6.2%`**；
   - `Mem0 w/ RAG` 保留了原子事实片段，但在面对过期偏好时，语义相似的旧事实依然被高分召回，导致过期立场误用率高达 **`51.4%`**。

### 2. 对联接 Agent 主报告（[storyline_and_evaluation_merged_technical_route_report.html](file:///d:/coding/sharing/.lavish/storyline_and_evaluation_merged_technical_route_report.html)）的直接启发
1. **直接锚定主报告“一、故事线驱动的混合合成数据方法论”与“跨事件证据累积门限”**：
   - 我们的联接 Agent 合成数据生成器直接对齐 `PersonaMem-v3` 的**“先立多层人设树（基础套餐 + 日常规律作息 + 个性化表述风格 `Idiolect` + 隐性业务诉求）$\rightarrow$ 再按时间轴投射为多渠道事件流（网元单据流 + 对话流）”**的逆向接地管线。
   - 严格吸收其**“多次重复才记为长期习惯”的量化设计**：区分显式指令（权重 $1.0$）与隐式单据行为（权重 $0.5$），区分长期周期性习惯（高累积阈值 $N_{\min}$）与短期临时保障意图（低阈值但强制携带 `stop_condition / expected_stop_ts`），并引入 `R1` **先例因果门控**防止偶发异常单据翻转长期画像，引入 `R18` **实体/槽位相干门控（`_merge_coheres`）**防止跨业务习惯的传递性错并。
2. **直接转化为评测集中的四大偏好演化（强化/新兴/衰退/脉冲）与“防过度个性化 / 记忆迎合探针”**：
   - 在评测集设计中，完整覆盖 `Reinforced`（规律通勤/晚间游戏）、`Emerging`（新开通业务）、`Diminishing`（旧应用弃用）与 `Bursty`（临时出差/单次大文件下载）四类时间轨迹。
   - 引入 `PersonaMem-v3` 的 **三角色评分体系（主正向指标 + 报幕/敷衍扣分项 + 厌恶/隐私/过期一票否决红线）** 以及 **伪造记忆迎合探针（Memory Sycophancy Probe）**与**个人事实幻觉探针（Personal-Fact Hallucination Probe，考察缺失槽位时是否主动追问澄清而非瞎编参数）**。
3. **用“结构化画像（Textual/Slot Profile）+ 原始单据按需检索（Agentic Search）”克服 `6.2%` 细节丢失与 `51.4%` 过期粘滞**：
   - 针对 `PersonaMem-v3` 暴露出的“文本画像丢细节（`Vague refind 6.2%`）、RAG 向量粘滞旧事实（`Outdated 51.4%`）”双输困局，我们的联接 Agent 采用**双层协同架构**：上层用带双时态有效期与显式计数 `[×N · last MM/DD]` 的结构化画像表承载当前有效偏好（解决过期粘滞），下层保留原始网元单据与对话日志的确定性过滤/检索接口（解决细粒度历史回溯与跨源冲突校验）。

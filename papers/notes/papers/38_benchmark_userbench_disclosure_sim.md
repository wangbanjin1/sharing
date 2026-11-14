# P3-12：UserBench 与 Disclosure-Gated Sim — 隐去细则的用户交互环境与五级披露门控模拟器

> **对应报告位置**：`1.1 方向五`（多轮意图澄清与用户模拟器设计边界：首轮隐去部分细分偏好，随追问按门控规则分步释放）  
> **原文与源码**：
> - **UserBench**：`D:\coding\sharing\papers\benchmark\UserBench_2025.pdf` / arXiv `2507.22034`（Cheng Qian et al., Salesforce AI Research / UIUC, 2025-07）  
> - **官方仓库**：`D:\coding\sharing\papers\repos\UserBench`（`https://github.com/SalesforceAIResearch/UserBench`，核心环境实现见 `travelgym/env/travel_env.py` 与评测入口 `eval.py`）  
> - **Disclosure-Gated Sim**：`D:\coding\sharing\papers\benchmark\Disclosure_Gated_Sim_2026.pdf` / arXiv `2609.00982`（Yao Liu et al., 清华大学, AAAI-27 预印本, 2026-09）；本文未附开源仓库链接，机制与数值直接溯源 `2609.00982\source\p2-arrpub.tex`。

---

## 1. 两篇论文在整体路线中的定位对比

| 维度 | UserBench (`2507.22034`) | Disclosure-Gated Sim (`2609.00982`) |
| :--- | :--- | :--- |
| **任务域与载体** | 多维度旅行规划 Gym 环境（`flight`、`hotel`、`apartment`、`car rental`、`restaurant` 五类子目标） | 长期情感陪伴与支持对话模拟器（CompanionBench 架构） |
| **解决的核心问题** | 传统单轮/显式多轮评测假设用户需求一次性说清，无法测出“信息缺失（`underspecification`）、增量表达（`incrementality`）、间接暗示（`indirectness`）”下的主动追问能力 | 传统 LLM 用户模拟器把整份人设与深层秘密一次性注入提示词，导致模拟器过早剧透（`premature over-disclosure`），无法区分陪伴 Agent 是否真的倾听与共情 |
| **偏好/信息释放机制** | 有效 `action` 追问触发精确偏好释放；若 Agent 长期未追问，经过固定轮次后环境**被动释放**部分偏好 | **五级有序披露门控**（`opening` → `asked_or_natural` → `felt_heard` → `felt_safe` → `earned_deep_trust`）映射至三层可见深度（`surface` < `mid` < `core`） |
| **负向反馈与回退** | 偏好未 elicit 直接猜答案导致 `Score` 与 `Correct Exist` 偏低；无效搜索/动作受惩罚 | **非对称回退（Asymmetric Retreat）**：触发两类关系破裂动作后，门控等级降级（`level ← max(0, level - 1)`）、连续共情计数清零并叠加防御面具（`guards`） |

---

## 2. UserBench：Gym 化偏好渐进释放与主实验结果

### 2.1 数据规模与三类交互特征

- **场景规模**：测试集 **417** 个旅行场景，训练集 **2,651** 个场景，涵盖多方面推理（如 `Travel-223` 表示需协调机票、酒店、餐厅等子目标）。每个场景包含超过 **100** 个候选选项，划分为 `correct`（完全满足含预算在内的所有隐含偏好）、`wrong`（部分不满足）与 `noise`（干扰项）。
- **三大现实交互挑战**：
  1. **信息缺失（`underspecification`）**：首轮指令故意模糊（例如仅给出出发地与大致预算），关键限制条件保留在用户环境内部状态中；
  2. **增量表达（`incrementality`）**：约 **100** 条细分偏好仅在 Agent 发起有效 `action` 询问时逐条释放，或超过预设轮次阈值后被动泄漏；
  3. **间接暗示（`indirectness`）**：用户不直接说“我要直飞/不要转机”，而是给出隐含线索，要求 Agent 自行推理并向环境求证。

```text
  [Agent 动作空间: search / action(ask) / answer]
         │
         ├── action(ask 有效追问) ──► TravelEnv 释放对应隐含偏好 (Active Elicited)
         │
         ├── 长时间未追问 ──────────► 到达固定轮次阈值后环境被动释放 (Passive Elicited)
         │
         └── search + answer ───────► 与候选池 (>100 options, correct/wrong/noise) 核对
                                         └─ 校验是否满足全部含预算在内的隐藏约束
```

### 2.2 单选模式主实验结果（`tab:travelgym_results_onechoice`，`2507.22034.md`）

| 模型 | Best Exist | Correct Exist | Score | Valid Search | Valid Action | Pref Elicited (Active / Passive) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT-4o** | `0.204` | `0.361` | `0.329` | `82.48%` | `27.82%` | `27.32%` (`24.06%` / `3.26%`) |
| **Gemini-2.5-Pro** | — | — | `0.317` | — | — | `29.71%` (`23.85%` / `5.85%`) |
| **Claude-4-Sonnet** | `0.260` | — | `0.307` | — | — | `34.25%` (`26.31%` / `7.94%`) |
| **Deepseek-V3** | — | — | `0.210` | — | — | — |
| **Qwen3-14B** | — | — | `0.209` | — | `33.71%` | — |
| **Qwen3-32B** | — | — | `0.206` | — | — | — |
| **Llama-3.3-70B** | — | — | `0.198` | — | — | — |
| **Qwen3-8B** | — | — | `0.180` | — | — | — |
| **GPT-4o-mini** | — | — | `0.166` | — | — | — |
| **Llama-3.1-8B** | — | — | `0.159` | — | — | — |
| **Gemini-2.5-Flash** | — | — | `0.125` | — | — | — |

**关键实证发现**（`2507.22034.md` L202–247）：
1. **单选模式难度陡增**：相较允许多选（`GPT-4o` 多选 `Score = 0.710`），单选模式整体得分下降约 **40%**；即使表现最好的模型，主动追问出的偏好比例也不足 **30%**。
2. **早猜启发式陷阱**：小模型（`Llama-3.1-8B`、`Gemini-2.5-Flash`）首次给出有效答案的轮次索引更小，看似“高效”，实则靠浅层猜测蒙答案，导致 `Score` 极低。
3. **单纯放宽轮次无效 + pass-$k$ 不稳定**：增加允许交互轮次（`fig:turn`）并不提升得分，反而引发重复对话与跑题；增加 `pass-k` 采样次数（`fig:passk`）只抬高最大值上限，平均分保持平坦甚至微降；减少 `30%` 错误/干扰选项（`tab:choice`）对 `GPT-4o`/`Deepseek-V3` 仅有小幅提升，说明真正卡脖子的是**意图探明而非选项多寡**。

### 2.3 官方仓库核查（`D:\coding\sharing\papers\repos\UserBench`）

- 核心环境 `TravelEnv`（`travelgym/env/travel_env.py` L22–66）严格遵循 `gymnasium.Env` 接口，观测空间 `observation_space` 显式暴露 `task_description`、`goal`、`feedback`、`step_count`、`episode_complete`、`total_preferences`、`remaining_preferences`、`elicitation_ratio` 与 `last_reward`，支持同步（`prompts.py`）与异步（`prompt_async.py`）两种动作评估器，且将训练/测试集按子目标配置（`travel22`、`travel223`、`travel334`、`travel444` 等）分别存放在 `data/*_multiturn[_onechoice]/*.parquet` 中。

---

## 3. Disclosure-Gated Sim：五级门控与非对称关系回退

### 3.1 五级门控与三层信息可见性（`p2-arrpub.tex` Sec. 3 & Table 1）

CompanionBench 中的用户模拟器内部维护一份被测试 Agent **绝对不可见（Visibility Contract）** 的披露清单（按敏感度分为 `surface` < `mid` < `core` 三层），通过以下五级有序门控控制信息解锁：

```text
  Level 0: opening             ──► 仅允许寒暄与表层背景
  Level 1: asked_or_natural    ──► 话题自然触及或被问及时释放 surface 层事实
  Level 2: felt_heard          ──► 感受到倾听与接纳时解锁部分 mid 层经历
  Level 3: felt_safe           ──► 需连续 >=2 轮保持共情 (fh_streak >= 2)
  Level 4: earned_deep_trust   ──► 稳定承接 mid 层披露且不说教/不回避，解锁 core 层
```

每轮陪伴 Agent 的回复被判别器归类为 **8 类 `ai_move`**：
- **正向推进**：`earned_felt_heard`、`earned_felt_safe`、`earned_deep_trust`、`sustained`（维持当前安全感）；
- **停滞与失误**：`neutral_noop`（无实质推进，`level ← min(level, 1)`）、`rushed_advice`（急于给建议，连续共情计数 `fh_streak` 清零）；
- **关系破裂（Rupture）**：`tripped_anti_goal`（踩中用户避讳点）与 `judged_or_lectured`（评判或说教用户）。一旦触发，系统执行**非对称回退**：`level ← max(0, level - 1)`、`fh_streak = 0`，并随机叠加 **7 种防御状态（`guards`）**之一与轻度退缩（`withdrawal`）。

### 3.2 关键消融与下游评测效度实验（`p2-arrpub.tex` Sec. 4 & Sec. 6）

- **训练语料与门控来源**：模拟器基于 13k 真实对话与合成门控分支联合微调（中文 33k 对话 / 714k 轮，真合比 60:40；英文 22k 对话 / 454k 轮）。消融表明门控能力主要由合成数据驱动：纯合成训练在中层披露对比度上达到 **`+0.610`**，而纯真实对话仅 **`+0.080`**（`p = 0.0001`）。
- **权重内化验证**：推理阶段将提示词中的门控规则文本完全剥离（`A1 → A2`），披露行为变化仅 `Δ = -0.022`，证明门控策略已内化进模拟器权重。
- **对 12 个被测系统（SUT）排名的影响（Sec. 6.4）**：
  - 若去掉门控规则直接模拟，12 个被测 Agent 的排行榜位置平均发生 **3 位** 错位（远超 1 位的随机噪声带）；
  - 若直接用前沿大模型提示词扮演模拟器（`gpt-5.1`），虽然还能保住相对排序，但会把所有模型的绝对得分整体虚高抬升 **`0.521`**；
  - 只有专门微调的 `122B M1b` 模拟器同时通过排序保真（`ρ = 0.993`）与分值尺度稳定两项校验。

---

## 4. 对我们当前方案的直接启发

1. **禁止将隐含需求一次性喂给用户模拟器**：在我们的 `UserProxy` 实现中，必须将待测试用户的背景偏好按优先级/敏感度拆分为“首轮可见”与“追问解锁”两层，严禁把整份 GT 槽位或 `profile` 文本拼进单条 System Prompt，否则会导致未经追问就直接泄题。
2. **区分“主动追问命中”与“被动兜底释放”并单独记账**：借鉴 UserBench 的 `Active Elicited` 与 `Passive Elicited` 拆分统计，防止 Agent 靠拖延轮次“白嫖”环境泄题，同时对未追问到位就提前给参数方案的“早猜”行为施加惩罚。
3. **引入简化的回退与防说教状态**：当被测 Agent 连续给出不相关建议或忽略用户明确拒绝信号时，用户模拟器应降低配合度或撤回部分试探性偏好（类似 `rushed_advice` 清零共情计数与 `level - 1` 回退），而非无条件顺从 Agent 话术。

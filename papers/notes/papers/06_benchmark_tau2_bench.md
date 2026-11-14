# 06 · τ²-Bench：用户与 Agent 双端协同环境的对话智能体评测基准

> **论文信息**：Victor Barres*, Honghua Dong*†, Soham Ray, Xujie Si, Karthik Narasimhan（Sierra、University of Toronto & Vector Institute），*$\tau^2$-Bench: Evaluating Conversational Agents in a Dual-Control Environment*，`arXiv:2506.07982v1`（2025 年 6 月 9 日）
> **本地源码与 PDF**：`papers/benchmark/2506.07982/source/`、`papers/benchmark/2506.07982/pdf/2506.07982.pdf`（同 `papers/benchmark/Tau2_Bench_2025.pdf`）
> **开源代码仓**：`https://github.com/sierra-research/tau2-bench`（本地克隆：`papers/repos/tau2-bench/`）
> **在我们体系中的定位**：`P0-7` —— **多轮对话意图澄清、双端协同（`Dual-Control`）环境交互、组合式原子故障任务生成（`SelectionSet` 笛卡尔积）与多次试验一致性指标（$\text{pass}^k$）** 的核心基准论文。支撑主报告第三部分（评测集构建方法与工具参数判定）与第四部分（`pass^3`、网元状态断言 `ENV_ASSERTION` 与工具执行契约评测）。

---

## 一、论文要解决什么问题？（背景与定位）

### 1.1 单方控制基准（Single-Control Benchmarks）的局限（`Sec 1, Sec 2, Fig. 1`）

现有工具调用与多轮对话评测基准（如 $\tau$-bench、FlowBench、ToolSandbox、APIGen-MT）普遍采用**单方控制假设（`Single-Control Environment`）**：
- **Agent 独占工具与环境修改权**：只有 Agent 连接后台数据库并调用 API 工具执行读写操作；
- **用户退化为被动信息源（`Passive Information Provider`）**：用户模拟器仅靠纯文本提示词（Prompt）扮演角色，向 Agent 口述预设意图或回答简单问题，无法直接观测或操作任何外部环境状态。

然而，在真实工业界场景（尤其是电信故障排查 `Telecom`、IT 运维、医疗问诊、终端排障）中，环境状态天然分布在**云端后台数据库（`Agent DB`）**与**用户侧物理终端/周边环境（`User Device & Surroundings`）**两端（`Sec 1, p.1–2`）：
1. **视野隔离与信息不对称（`Decentralized Partial Observability`）**：Agent 能查后台 CRM 账单、套餐限额、漫游开关与停复机状态，但看不到用户手机信号栏、SIM 卡是否松动、飞行模式是否误开、VPN 或省流模式是否限速；反之，用户能直接查看并操作自己的手机设置，但看不到后台账单逾期状态或套餐流量池余量。
2. **双端操作紧耦合（`Coupled Dual-Control Actions`）**：排障往往需要 Agent 与用户交替执行跨端协同动作。例如：后台因账单逾期暂停线路后，Agent 必须先调用 `send_payment_request` 下发待付账单，引导用户在手机端调用 `make_payment` 付款，或者在 Agent 调用 `enable_roaming` / `refuel_data` 后，指导用户在终端侧调用 `toggle_roaming`、`toggle_data_saver_mode` 或 `reboot_device` 并重新执行 `run_speed_test` 验证网速恢复（`Sec 3.2, Fig. 2`）。

### 1.2 $\tau^2$-Bench 的三大核心贡献（`Sec 1, p.2`）

1. **双端协同 Dec-POMDP 形式化建模（`Sec 3.1`）**：将对话智能体评测建模为双人去中心化部分可观测马尔可夫决策过程（`Dec-POMDP`），Agent 与 User 各自拥有专属的只读/写入工具集（`Agent Tools` 与 `User Tools`），并通过底层环境同步钩子（`sync_tools`）实时耦合双端状态。
2. **组合式程序化任务生成器（`Compositional Programmatic Task Generator`, `Sec 3.2, App. A`）**：提出基于**原子故障子任务（`Atomic Subtasks`）**与**互斥选择集（`SelectionSet`）**笛卡尔积的任务合成管线，每个原子子任务绑定「初始故障注入函数 $f^{\text{init}}$ + 标准修复函数 $f^{\text{sol}}$ + 环境断言函数 $f^{\text{assert}}$」，自动生成 **2,285 个**严格验证可解性（且每步修复均必需）的 `telecom` 组合排障任务（评测集分层采样 114 个代表性任务）。
3. **细粒度消融与用户模拟器可靠性实证（`Sec 3.3, Sec 4, App. E`）**：在 `retail`、`airline`、`telecom` 三大域系统评测主流大模型（`gpt-4.1`、`o4-mini`、`claude-3.7-sonnet`、`gpt-4.1-mini`）的 $\text{pass}^1 \sim \text{pass}^4$ 表现；通过 `Default`、`No-User`（单人全权控制消融）与 `Oracle Plan`（给定标准动作序列消融）剥离出**推理诊断开销**与**双端沟通引导开销**；并证明用结构化工具状态约束用户模拟器可将模拟器总体出错率从 `airline` 的 **47%**、`<retail>` 的 **40%** 大幅降至 `telecom` 的 **16%**（且零未锚定胡编错误）。

---

## 二、核心方法与架构拆解（Method & Architecture）

### 2.1 双端协同 Dec-POMDP 形式化定义（`Sec 3.1, Eq. in p.3–4, Fig. 2`）

论文将单次排障对话建模为双人协作 Dec-POMDP 元组 $(\mathcal{S}, \{\mathcal{A}_i\}, \{\mathcal{O}_i\}, \mathcal{T}, \mathcal{R}, \mathcal{U}, \mathcal{M})$，其中参与者 $i \in \{\text{agent}, \text{user}\}$：

```
+=========================================================================================+
|                         τ²-Bench Dual-Control Dec-POMDP 架构                             |
|                (Sec 3.1, Fig. 2 & src/tau2/orchestrator/orchestrator.py)                 |
+=========================================================================================+

  +-----------------------------------+               +-----------------------------------+
  |           Agent (LLM)             |               |       User Simulator (LLM)        |
  |  Policy: domain policy (Main/WF)  |               |  Persona: None / Easy / Hard      |
  |  History: Agent messages + tools  |               |  History: Role-flipped messages   |
  +-----------------+-----------------+               +-----------------+-----------------+
                    |                                                   |
       (1a) Agent   |  (1b) Natural Language Message m_i ∈ M            | (2a) User
       Tool Call    +-------------------------+-------------------------+ Tool Call
       a_agent,tool                           |                           a_user,tool
                    v                         v                         v
  +-----------------------------------+   Orchestrator   +-----------------------------------+
  |     Agent Tools (TelecomTools)    |  Half-Duplex     |    User Tools (TelecomUserTools)  |
  |  READ (6):                        |  Turn Routing    |  READ (15):                       |
  |   - get_customer_by_phone/id/name |  (MaxSteps=200,  |   - check_status_bar/network      |
  |   - get_details_by_id             |   MaxErrors=10)  |   - run_speed_test / can_send_mms |
  |   - get_bills_for_customer        |                  |   - check_sim/apn/vpn/wifi/app... |
  |   - get_data_usage                |                  |  WRITE (15):                      |
  |  WRITE (6) + GENERIC (1):         |                  |   - toggle_airplane_mode/data/... |
  |   - suspend_line / resume_line    |                  |   - reseat_sim_card / set_apn     |
  |   - send_payment_request          |                  |   - grant_app_permission / reboot |
  |   - enable/disable_roaming        |                  |   - make_payment                  |
  |   - refuel_data / transfer_human  |                  |                                   |
  +-----------------+-----------------+                  +-----------------+-----------------+
                    |                                                      |
                    v                                                      v
  +------------------------------------------------------------------------------------------+
  |                     World State  S_world = S_db,agent (x) S_db,user                      |
  |                                                                                          |
  |  +------------------------------------+          +------------------------------------+  |
  |  |     Agent DB (TelecomDB, TOML)     |          |    User DB (TelecomUserDB, TOML)   |  |
  |  |  - plans: list[Plan] (5 plans)     |  sync_   |  - device: MockPhoneAttributes     |  |
  |  |  - customers: list[Customer] (4)   | <======> |    (sim, airplane, apn, vpn, apps) |  |
  |  |  - lines: list[Line] (9 lines)     |  tools() |  - surroundings: UserSurroundings  |  |
  |  |  - bills: list[Bill] (overdue/paid)|          |    (roaming, line_active, bill...) |  |
  |  +------------------------------------+          +------------------------------------+  |
  +------------------------------------------------------------------------------------------+
```

1. **世界状态分解（`State Space`, `Sec 3.1, p.3–4`）**：
   $$\mathcal{S} = \mathcal{S}_{\text{world}} \otimes \mathcal{S}_{\text{history}}, \qquad \mathcal{S}_{\text{world}} = \mathcal{S}_{\text{db,agent}} \otimes \mathcal{S}_{\text{db,user}}$$
   符号解释如下：
   - $\mathcal{S}_{\text{db,agent}}$：Agent 侧后台业务数据库状态（在 `telecom` 域中对应 `TelecomDB`，含 `plans`、`customers`、`lines`、`bills` 四张表，`domains/telecom/data_model.py:194-224`）；
   - $\mathcal{S}_{\text{db,user}}$：用户侧设备与环境状态（在 `telecom` 域中对应 `TelecomUserDB`，含 `device: MockPhoneAttributes` 手机硬件/系统设置状态与 `surroundings: UserSurroundings` 物理环境与信号衍生状态，`domains/telecom/user_data_model.py:495-509`）；
   - $\mathcal{S}_{\text{history}} = \mathcal{S}_{\text{history,agent}} \otimes \mathcal{S}_{\text{history,user}} \otimes \mathcal{S}_{\text{history,message}}$：双端各自私有的工具调用历史与共享的双人对话文本历史。

2. **动作空间与半双工轮流约束（`Action Space & Half-Duplex Turn Constraint`, `Sec 3.1, p.4` & `orchestrator.py:737-746`）**：
   - 每个参与者 $i \in \{\text{agent}, \text{user}\}$ 的动作空间为：
     $$\mathcal{A}_i = \mathcal{A}_{i,\text{tool}} \cup \mathcal{M}$$
   - **半双工互斥铁律**：每一时间步仅有一个参与者行动；且单步动作**只能**是工具调用 $a_{i,\text{tool}} \in \mathcal{A}_{i,\text{tool}}$ **或者**向对方发送自然语言消息 $m_i \in \mathcal{M}$，**严禁在同一轮消息中同时包含工具调用和发给对方的自然语言文本**（在源码 `LLMAgent.check_valid_turn` 与 `Orchestrator._check_message_constraint` 中强制校验：若 LLM 同时输出 `content` 与 `tool_calls`，直接记录错误或触发重试，`orchestrator.py:737-746`）。
   - **控制权交接规则**：当参与者 $i$ 调用工具 $a_{i,\text{tool}}$ 时，环境返回观测结果 $o_{i,\text{tool}} \in \mathcal{O}_{i,\text{tool}}$，**控制权仍留在参与者 $i$ 手中**（可连续调用多个工具）；唯有当参与者 $i$ 发送自然语言消息 $m_i \in \mathcal{M}$ 时，控制权才切换给对方。

3. **跨库状态同步机制（`sync_tools`, `domains/telecom/environment.py:40-95`）**：
   - 尽管 Agent 工具只读写 $\mathcal{S}_{\text{db,agent}}$、User 工具只读写 $\mathcal{S}_{\text{db,user}}$，但真实电信网络中后台配置会直接改变终端可观测状态。`TelecomEnvironment.sync_tools()` 在初始化及**每一次工具调用执行后**（`environment.py:210, 418, 486`）自动触发以下四项跨端同步：
     1. **线路激活状态同步**：读取后台 `line.status == LineStatus.ACTIVE`，同步写入用户侧 `surroundings.line_active`；
     2. **漫游权限同步**：读取后台 `line.roaming_enabled`，同步写入用户侧 `surroundings.roaming_allowed`；
     3. **流量超额限速同步**：计算后台 `line.data_used_gb >= plan.data_limit_gb + line.data_refueling_gb`，同步写入用户侧 `surroundings.mobile_data_usage_exceeded`（一旦为 `True`，用户手机端 `run_speed_test` 会直接掉速至 `No Connection`）；
     4. **账单催缴与支付双向闭环**：若后台存在 `bill.status == BillStatus.AWAITING_PAYMENT`，则在用户手机端生成 `PaymentRequest(bill_id, amount_due, paid=False)`；当用户在手机端调用 `make_payment` 将 `payment_request.paid` 置为 `True` 后，`sync_tools()` 立即回调后台 `tools._set_bill_to_paid(bill_id)` 将账单状态更新为 `PAID` 并清空 `payment_request`。

---

### 2.2 三大评测域与工具集对比（`Sec 3.2, Table 1` & `domains/telecom/tools.py, user_tools.py`）

论文将 $\tau$-bench 的 `retail` 与 `airline` 域重构接入统一框架（修复了原版任务缺陷与模拟器提示词），并全新构建了唯一的双端控制域 `telecom`（`Table 1, p.4`）：

| 评测域 (`Domain`) | 数据库规模 (`DB Elements`) | Agent 工具数 (`Write / Read`) | User 工具数 (`Write / Read`) | 评测任务数 (`Tasks`) | 控制模式 |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **`retail`** | 500 用户, 50 商品, 1,000 订单 | `7 write`, `6 read` | 无 (`none`) | `115` | 单方控制 (`Single-Control`) |
| **`airline`** | 500 用户, 300 航班, 2,000 预订 | `6 write`, `6 read` | 无 (`none`) | `50` | 单方控制 (`Single-Control`) |
| **`telecom`** | 5 套餐, 9 线路, 4 客户 | `6 write`, `7 read`* | `15 write`, `15 read` | `114`（全量 `2,285`） | **双端协同 (`Dual-Control`)** |

> *注：表 1 报告 `telecom` Agent 工具为 `6 write, 7 read`。核对源码 `domains/telecom/tools.py`（共 13 个 `@is_tool` 方法），其中包含 6 个 `ToolType.READ`（`get_customer_by_phone`、`get_customer_by_id`、`get_customer_by_name`、`get_details_by_id`、`get_bills_for_customer`、`get_data_usage`）、6 个 `ToolType.WRITE`（`suspend_line`、`resume_line`、`send_payment_request`、`enable_roaming`、`disable_roaming`、`refuel_data`）以及 1 个 `ToolType.GENERIC`（`transfer_to_human_agents`），论文统计时将 `transfer_to_human_agents` 归入了非写操作计数。

---

### 2.3 组合式程序化任务生成器（`Compositional Task Generator`, `Sec 3.2, App. A` & `domains/telecom/tasks/`）

这是 $\tau^2$-Bench 在基准构建方法论上最值得借鉴的设计。为了避免手工编写多轮排障剧本导致的覆盖率低、前后状态矛盾或存在作弊捷径，作者设计了基于**原子故障子任务组合**的程序化生成器：

```
+=========================================================================================+
|                  组合式程序化任务生成与三步自动验证管线 (Sec 3.2, App. A)                   |
|          (src/tau2/domains/telecom/tasks/manager.py, utils.py, create_tasks.py)         |
+=========================================================================================+

  [1. 原子故障子任务 BaseTask]                 [2. 互斥选择集 SelectionSet]
   t = (f_init, f_sol, f_assert)                每个 SelectionSet 包含若干互斥 BaseTask + None
   - 例: OverdueBillTask                        - Service Issues: 5 个 SelectionSet
     * f_init: set_bill_to_overdue()            - Mobile Data Issues: 1 + 6 = 7 个 SelectionSet
     * f_sol : send_payment_request()           - MMS Issues: 2 + 3 + 4 = 9 个 SelectionSet
               + make_payment()                 
     * f_assert: is_bill_paid() == True                   |
                                                          v  compose_tasks() 笛卡尔积
  +---------------------------------------------------------------------------------------+
  | [3. 组合任务合成与过滤 (create_tasks.py:63-77)]                                        |
  |  - 笛卡尔积生成全部子任务组合 T = {t_1, ..., t_k}                                      |
  |  - 过滤掉子任务数 |T| < 2 的简单任务                                                   |
  |  - 若任意 t ∈ T 的 fix_funcs == [None] (如手机契约过期/SIM硬件锁死):                   |
  |      -> 标记 expected_failure = True，标准解强制设为 [transfer_to_human_agents]        |
  +---------------------------------------------------------------------------------------+
                                                          |
                                                          v
  +---------------------------------------------------------------------------------------+
  | [4. 三步确定性自动验证 (TaskManager.verify_task, manager.py:197-227)]                  |
  |  Step A (初始健康校验): 默认环境加载后，is_fixed(env) 必须为 True                      |
  |  Step B (逐步必要性校验): 执行全部 f_init 注入复合故障后，按序执行标准修复动作 a_1..a_m |
  |         在每一个动作 a_i 执行前: assert not is_fixed(env)  (杜绝冗余子任务!)           |
  |  Step C (终态完备校验): 全部修复动作执行完毕后:                                        |
  |         assert is_fixed(env) == fixable 且全部 extra_env_assertions 返回 True          |
  +---------------------------------------------------------------------------------------+
                                                          |
                                                          v
     全量合法组合任务: 2,285 个 (Service: 47 | Mobile Data: 382 | MMS: 1,856)
     按 (intent, num_subtasks, persona) 分桶采样 (max_count_per_bin=3, seed=42) -> 114 个评测任务
```

1. **原子故障子任务三元组（`Atomic Subtasks`, `Sec 3.2, p.5` & `tasks/utils.py:16-21`）**：
   每个原子故障子任务 $t$ 定义为三组函数的集合：
   $$t = \left(\{f_{t,k}^{\text{init}}\}, \; \{f_{t,k}^{\text{sol}}\}, \; \{f_{t,k}^{\text{assert}}\}\right)$$
   - $\{f_{t,k}^{\text{init}}\}$（`init_funcs`）：在默认正常环境上注入特定故障的初始化函数（如将手机置于漫游状态 `set_user_roaming`、开启省流模式 `enable_data_saver_mode`、注入逾期账单并停机 `set_bill_to_overdue`）；
   - $\{f_{t,k}^{\text{sol}}\}$（`fix_funcs`）：修复该故障所需的标准工具调用序列（含 Agent 工具与 User 工具）；若该故障属于权限外或硬件死锁不可修复故障（如 `contract_expired` 合约到期、`sim_card_locked` PUK 锁死、`app_vpn_issue`），则 `fix_funcs = [None]`，系统自动将整个组合任务标记为 `expected_failure = True`，并将唯一标准修复动作替换为调用 `transfer_to_human_agents`（`tasks/manager.py:97-115`）；
   - $\{f_{t,k}^{\text{assert}}\}$（`extra_env_assertions`）：校验该子故障是否已被彻底清除的布尔断言函数。

2. **三大故障意图与互斥选择集矩阵（`App. A.2, Table 3, Table 4, p.14–16` & `service_issues.py`, `mobile_data_issues.py`, `mms_issues.py`）**：
   同一设备属性上的冲突故障被归入同一个互斥选择集 `SelectionSet(tasks=[...])`。生成某类大意图任务时，从各 `SelectionSet` 中至多抽取 1 个子任务（或 `None`）求笛卡尔积 `product(*[s.tasks + [None] for s in selection_sets])`，并剔除子任务数少于 2 的平凡组合（`create_tasks.py:63-65`）：

   | 故障大类 (`Intent`) | 关联的互斥选择集 (`SelectionSets`) | 核心成功判据 (`is_fixed` 函数) | 全量组合数 (`|T| >= 2`) | 分桶采样数 (`Sampled`) | 标准修复动作数 (`Mean ± Std [Min, Max]`) |
   | :--- | :--- | :--- | :---: | :---: | :---: |
   | **`service_issue`**<br>（无信号/无法通话） | 5 个选择集：<br>① 飞行模式 (`airplane_mode_on`)<br>② SIM 卡状态 (`unseated` / `locked` [不可修])<br>③ 线路状态 (`overdue_bill` / `suspended` [不可修] / `contract_expired` [不可修])<br>④ 漫游设置 (`roaming_disabled_on_phone` / `roaming_not_allowed_by_line`)<br>⑤ 网络制式偏好 (`preference_2g`) | `status_bar` 显示正常信号格且非飞行模式 (`service_issues.py:39-45`) | `47` | **`29`** | `2.31 ± 2.25`<br>`[1, 8]` |
   | **`mobile_data_issue`**<br>（无移动数据/网速慢） | 7 个选择集（1 个服务前置集 + 6 个数据集）：<br>① 基础服务故障 (`airplane_mode` / `sim_locked` / `line_overdue`)<br>② 手机数据开关 (`data_mode_off`)<br>③ 移动漫游复合故障 (`phone_off` / `line_off` / `both_off`)<br>④ 省流模式限速 (`data_saver_mode_on`)<br>⑤ APN 配置错误 (`broken_apn` / `broken_apn_need_reboot`)<br>⑥ VPN 限速 (`vpn_on` / `app_vpn_issue` [不可修])<br>⑦ 流量用尽 (`data_usage_exceeded`) | `run_speed_test` 测速 `>= 100 Mbps`（`Excellent` 级别，`mobile_data_issues.py:42-49`） | `382` | **`36`** | `4.31 ± 1.79`<br>`[2, 8]` |
   | **`mms_issue`**<br>（无法发送彩信 MMS） | 9 个选择集（2 个服务集 + 3 个数据集 + 4 个彩信集）：<br>①~⑤ 服务与移动数据前置故障集<br>⑥ 无线网络干扰 (`wifi_on` — MMS 需走蜂窝数据)<br>⑦ Wi-Fi 通话开启 (`wifi_calling_on` [不可修/需关闭])<br>⑧ 彩信 APN MMSC 缺失 (`broken_apn_mms`)<br>⑨ 短信 App 权限缺失 (`app_missing_storage` / `sms` / `both`) | `can_send_mms()` 返回 `True` (`mms_issues.py:37-40`) | `1,856` | **`49`** | `6.00 ± 2.85`<br>`[2, 12]` |
   | **合计 (`Total`)** | — | — | **`2,285`** | **`114`** | — |

3. **三类用户人设（`Personas`, `App. A.2, p.15` & `tasks/const.py:1-26`）**：
   为考察 Agent 对不同配合度与技术水平用户的引导能力，任务生成时绑定了 3 类 Persona：
   - `None`（默认人设）：无附加性格限制；
   - `Easy`（`EasyPersona`）：67 岁退休教师，对手机设置不熟悉，需要 Agent 耐心给出每一步具体操作指引，但完全配合；
   - `Hard`（`HardPersona`）：42 岁建筑工人，性格急躁易怒，讨厌繁琐排查问题，被要求反复检查手机时会表现出怀疑与不耐烦。

---

### 2.4 奖励计算与多维评测机制（`Sec 3.3` & `src/tau2/evaluator/`）

1. **三层评测维度（`EvaluationType.ALL`, `evaluator.py:46-95`）**：
   - **环境状态评测（`EnvironmentEvaluator`, `evaluator_env.py:29-160`）**：
     - 初始化两个完全相同的环境副本：`predicted_environment` 与 `gold_environment`；
     - 在 `predicted_environment` 上重放对话轨迹 `full_trajectory` 中双端实际发起的所有**写状态工具调用**（通过 `is_mutating_tool_call` 跳过只读工具、`think` 工具以及名字不存在的幻觉工具调用，`environment.py:379-397`）；
     - 在 `gold_environment` 上执行任务预设的标准修复动作序列 `evaluation_criteria.actions`；
     - 执行两项比对：① **数据库哈希全量比对（`DBCheck`）**：校验 `predicted_environment.check_db()`（比对 Agent DB 与 User DB 的 SHA-256 哈希值，`environment.py:291-319`）；② **环境断言校验（`EnvAssertionCheck`）**：逐一运行 `evaluation_criteria.env_assertions`（如 `is_fixed` 及各子任务的 `extra_env_assertions`）。
   - **动作轨迹评测（`ActionEvaluator`, `evaluator_action.py:16-102`）**：
     - 检查黄金动作列表 `golden_actions` 中的关键动作（如不可修复任务必须执行的 `transfer_to_human_agents`）是否以匹配的 `name` 和 `arguments` 出现在对话轨迹中。
   - **自然语言输出评测（`NLAssertionsEvaluator`, `evaluator_nl_assertions.py`）**：检查回复文本是否满足特定自然语言断言。
   - **通信协议守卫（`CommunicateEvaluator` / 终止校验, `evaluator.py:67-72`）**：若对话因超出最大步数（`MAX_STEPS = 200`）或最大连续工具错误数（`MAX_ERRORS = 10`）异常中断，直接判定 `reward = 0.0`。

2. **多次试验一致性指标 $\text{pass}^k$（`Sec 4, Eq. in footnote 3, p.6` & `metrics/agent_metrics.py:45-64`）**：
   沿用 $\tau$-bench 的核心可靠性指标 $\text{pass}^k$：对同一个任务独立运行 $n$ 次试验（论文中 $n=4$），若其中成功次数为 $c$，则连续 $k$ 次试验全部成功的无偏组合估计量为：
   $$\text{pass}^k = \mathbb{E}_{\text{task}}\left[\frac{\binom{c}{k}}{\binom{n}{k}}\right]$$
   符号解释如下：
   - $n$：每个任务独立运行的试验总次数（论文取 $n=4$）；
   - $c$：在 $n$ 次试验中获得满分奖励（$r = 1.0$）的成功次数；
   - $k$：要求连续稳定成功的试验次数（$1 \le k \le n$）。当 $k=1$ 时，$\text{pass}^1 = c/n$ 即平均单次成功率；当 $k=4$ 时，要求 4 次独立试验 100% 全部成功（只要有 1 次失败则 $\binom{c}{4} = 0$）。

---

## 三、实验设置与全量结果（Experimental Setup & Results）

### 3.1 实验配置与评测成本（`Sec 4.1, App. D.2`）

- **被测 Agent 模型**：`gpt-4.1-2025-04-14`、`o4-mini-2025-04-16`、`gpt-4.1-mini-2025-04-14`、`claude-3-7-sonnet-20250219`（均采用 LiteLLM 统一函数调用接口，`temperature = 0.0`，每任务独立运行 $n=4$ 次）。
- **用户模拟器模型**：固定使用 `gpt-4.1-2025-04-14`（`temperature = 0.0`）。
- **单次试验 API 成本（`App. D.2, p.20`）**：在 `telecom` 域使用 `gpt-4.1` 跑完 114 个任务的单轮开销约为 **\$40**（平均每个任务 Agent 端消耗 `\$0.086`，User Simulator 端消耗 `\$0.059`）。

---

### 3.2 主实验结果：跨三大域的 $\text{pass}^1 \sim \text{pass}^4$ 对比（`Sec 4.2, Fig. 3, p.6`）

从论文 `Figure 3` 提取的四大模型在 `retail`（115 任务）、`airline`（50 任务）与 `telecom`（114 任务，默认 `Original Policy`）上的完整 $\text{pass}^k$ 得分如下：

| 评测域 (`Domain`) | 指标 | `gpt-4.1` | `o4-mini` | `gpt-4.1-mini` | `claude-3.7-sonnet` | 核心现象与结论 |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **`retail`**<br>（单方控制，115 任务） | $\text{pass}^1$<br>$\text{pass}^2$<br>$\text{pass}^3$<br>$\text{pass}^4$ | `0.74`<br>`0.64`<br>`0.58`<br>`0.53` | `0.71`<br>`0.59`<br>`0.52`<br>`0.46` | `0.66`<br>`0.53`<br>`0.44`<br>`0.39` | **`0.79`**<br>**`0.69`**<br>**`0.63`**<br>**`0.60`** | 常规单方 API 调用已较为成熟，`claude-3.7-sonnet` 与 `gpt-4.1` 的 $\text{pass}^1$ 达 `0.74~0.79`。 |
| **`airline`**<br>（单方控制，50 任务） | $\text{pass}^1$<br>$\text{pass}^2$<br>$\text{pass}^3$<br>$\text{pass}^4$ | `0.56`<br>`0.46`<br>`0.42`<br>`0.40` | **`0.59`**<br>**`0.48`**<br>**`0.42`**<br>`0.38` | `0.51`<br>`0.39`<br>`0.32`<br>`0.26` | `0.50`<br>`0.41`<br>`0.38`<br>`0.36` | 受复杂退改签业务规则限制，各模型 $\text{pass}^1$ 降至 `0.50~0.59`。 |
| **`telecom`**<br>（**双端协同**，114 任务） | $\text{pass}^1$<br>$\text{pass}^2$<br>$\text{pass}^3$<br>$\text{pass}^4$ | `0.34`<br>`0.26`<br>`0.22`<br>`0.19` | `0.42`<br>`0.33`<br>`0.29`<br>**`0.26`** | `0.44`<br>`0.30`<br>`0.22`<br>`0.18` | **`0.49`**<br>**`0.37`**<br>**`0.31`**<br>`0.25` | **双端协同导致性能断崖式下跌**：所有模型在 `telecom` 上的 $\text{pass}^1 < 0.50$，且 $\text{pass}^4$ 跌至 `0.18~0.26`（相比 $\text{pass}^1$ 暴跌近一半）。 |

---

### 3.3 核心消融实验：剥离「双端沟通引导开销」与「推理诊断开销」（`Sec 4.2, Fig. 4, p.7`）

为什么大模型在 `telecom` 双端协同域崩溃？为了精确定位瓶颈，作者在 `telecom` 域设计了三种评测模式（`Fig. 4`）与两种策略文档（`Original Policy` 声明式通用规则与 `Workflow Policy` 详尽步骤决策树排障手册）：
1. **`Default`（标准双端协同模式）**：Agent 掌握 Agent Tools，User 掌握 User Tools，双方通过多轮自然语言交互配合排障；
2. **`No-User`（单人全权控制消融，`Solo Mode`, `llm_agent.py:216-312`）**：移除用户模拟器，把 **Agent Tools + User Tools 全部交给 Agent 一个人直接调用**，并直接把任务意图告诉 Agent，最后调用 `done()` 结束（完全消除跨端沟通与引导用户的开销，仅考察工具推理与排障诊断能力）；
3. **`Oracle Plan`（神谕动作序列消融，`GT Agent`, `llm_agent.py:315-452`）**：保持双端协同（User Tools 仍在用户手中），但在 Agent 的 System Prompt 中直接塞入**当前任务的标准修复动作序列（含需引导用户执行的工具名）**（完全消除排障诊断推理负担，仅考察 Agent 能否准确按剧本调用自身工具并指导用户完成终端操作）。

从 `Figure 4` 提取的完整消融数据（$\text{pass}^1$）如下：

| 策略文档类型 (`Domain Policy`) | 模型 | `Default`<br>（标准双端协同） | `No-User`<br>（单方全权控制） | `Oracle Plan`<br>（给定标准动作剧本） | 双端协同损耗<br>（`Default - No-User`） | 诊断推理增益<br>（`Oracle - Default`） |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`Original Policy`**<br>（声明式业务规则） | `gpt-4.1`<br>`o4-mini` | `0.34`<br>`0.42` | `0.52`<br>`0.67` | `0.73`<br>**`0.96`** | **`-0.18` (`-18%`)**<br>**`-0.25` (`-25%`)** | `+0.39` (`+39%`)<br>`+0.54` (`+54%`) |
| **`Workflow Policy`**<br>（显式步骤排障流程图） | `gpt-4.1`<br>`o4-mini` | `0.52` (`+18%`)<br>`0.59` (`+17%`) | `0.68` (`+16%`)<br>`0.72` (`+5%`) | `0.57` (`-16%` vs Orig)<br>`0.88` (`-8%` vs Orig) | **`-0.16` (`-16%`)**<br>**`-0.13` (`-13%`)** | `+0.05` (`+5%`)<br>`+0.29` (`+29%`) |

**三点关键实证洞察（`Sec 4.2, p.7`）**：
1. **双端沟通与引导本身造成 `18% ~ 25%` 的性能折损**：对比 `No-User` 与 `Default`，仅仅因为把手机工具放回用户手里、需要 Agent 通过自然语言询问和指导用户操作，`gpt-4.1` 的成功率就从 `0.52` 跌至 `0.34`（`-18%`），推理模型 `o4-mini` 更是从 `0.67` 暴跌至 `0.42`（`-25%`）。
2. **显式工作流手册（`Workflow Policy`）大幅提升常规诊断，但会与先验计划产生机械冲突**：将声明式 `Original Policy` 替换为包含完整排查顺序的 `Workflow Policy` 后，`Default` 模式下 `gpt-4.1` 与 `o4-mini` 分别飙升 `+18%` 和 `+17%`；但在 `Oracle Plan` 模式下，`Workflow Policy` 反而比 `Original Policy` 下降了 `16%`（`0.73 -> 0.57`）和 `8%`（`0.96 -> 0.88`）——因为 Agent 在机械执行手册固定排查步骤时，与 `Oracle Plan` 给出的最短跳步修复动作发生了指令冲突！
3. **即便给了标准答案剧本（`Oracle Plan`），非推理模型仍有 `27%` 的任务死在“不会引导用户”上**：在 `Original Policy + Oracle Plan` 下，`o4-mini` 达到 `0.96`，但 `gpt-4.1` 仅为 `0.73`（仍有 27% 失败率），证明“如何把后台诊断转化为清晰的自然语言指令让用户正确操作终端”是独立于推理之外的核心能力短板。

---

### 3.4 故障复杂度、子任务数与用户人设的影响（`Sec 4.3, Fig. 5, Fig. 6, Fig. 7, p.8–9`）

1. **按故障大类拆解（`Figure 6`）—— 彩信复合故障（`mms_issue`）全军覆没**：

   | 模型 | `service_issue` ($\text{pass}^1 / \text{pass}^4$) | `mobile_data_issue` ($\text{pass}^1 / \text{pass}^4$) | `mms_issue` ($\text{pass}^1 / \text{pass}^4$) |
   | :--- | :---: | :---: | :---: |
   | `gpt-4.1` | `0.66 / 0.38` | `0.30 / 0.17` | `0.18 / 0.10` |
   | `o4-mini` | **`0.85 / 0.76`** | `0.48 / 0.19` | `0.12 / 0.02` |
   | `gpt-4.1-mini` | `0.78 / 0.38` | `0.53 / 0.19` | `0.16 / 0.04` |
   | `claude-3.7-sonnet` | `0.77 / 0.48` | **`0.69 / 0.39`** | `0.18 / 0.02` |

   - 在仅需 `1~4` 步修复的 `service_issue` 上，`o4-mini` 的 $\text{pass}^1$ 高达 `0.85`、$\text{pass}^4$ 达 `0.76`；
   - 一旦进入包含“服务前置故障 + 移动数据故障 + Wi-Fi/APN/权限复合故障”（平均需 6 步修复）的 `mms_issue`，所有模型的 $\text{pass}^1$ 瞬间跌至 **`0.12 ~ 0.18`**，$\text{pass}^4$ 接近于 **`0.02 ~ 0.10`**！原因在于复合故障存在**症状掩盖效应（`Masking Effect`）**：例如当“流量超额停机”与“省流模式限速”同时存在时，Agent 修复流量超额后看到网速从 `0 Mbps` 恢复到 `55 Mbps`（`Good`），便误以为排障完成而提前结束对话，漏掉了必须继续关闭省流模式才能达到 `>= 100 Mbps`（`Excellent`）的隐藏故障。

2. **按原子子任务数与修复步数拆解（`Figure 5`）**：
   - 当组合子任务数从 `2` 增加到 `>= 5`（或所需修复动作数从 `1~2` 增加到 `>= 7`）时，所有模型的 $\text{pass}^1$ 呈单调陡降趋势（在 `>= 7` 个动作时，`gpt-4.1` 与 `o4-mini` 的 $\text{pass}^1$ 均跌破 `0.10`）。

3. **按用户人设拆解（`Figure 7`）—— `Hard Persona` 显著拉低模型表现**：

   | 模型 | `None Persona` ($\text{pass}^1 / \text{pass}^4$) | `Easy Persona` ($\text{pass}^1 / \text{pass}^4$) | `Hard Persona` ($\text{pass}^1 / \text{pass}^4$) | `Easy` 对比 `Hard` ($\Delta \text{pass}^1$) |
   | :--- | :---: | :---: | :---: | :---: |
   | `gpt-4.1` | `0.28 / 0.15` | `0.39 / 0.24` | `0.36 / 0.19` | `-0.03` |
   | `o4-mini` | `0.36 / 0.23` | `0.52 / 0.32` | `0.38 / 0.25` | **`-0.14`** |
   | `gpt-4.1-mini` | `0.43 / 0.12` | `0.54 / 0.24` | `0.34 / 0.17` | **`-0.20`** |
   | `claude-3.7-sonnet` | `0.42 / 0.15` | **`0.63 / 0.42`** | `0.42 / 0.19` | **`-0.21`** |

---

### 3.5 用户模拟器可靠性分析（`Sec 3.4, Table 2, App. E, p.6 & p.21–24`）

人工逐条审查 `airline`（100 条）、`retail`（50 条）与 `telecom`（50 条）对话轨迹后，统计的用户模拟器错误率（分 `Critical` 改变评测结果的关键错误与 `Benign` 不影响结果的轻微错误）如下：

| 评测域 | 抽检轨迹数 | `Critical`（关键错误） | `Benign`（轻微错误） | `Total`（总错误率） | 错误类型分布（`App. E`） |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`airline`** | `100` | `13 (13%)` | `34 (34%)` | `47 (47%)` | 结构违例 `19/47`、未锚定胡编 `15/47`、遗漏约束 `11/47`、过早终止 `2/47` |
| **`retail`** | `50` | `6 (12%)` | `14 (28%)` | `20 (40%)` | 结构违例 `11/20`、遗漏约束 `4/20`、过早终止 `3/20`、未锚定胡编 `2/20` |
| **`telecom`** | `50` | **`3 (6%)`** | **`5 (10%)`** | **`8 (16%)`** | **100% (`8/8`) 为转人工确认时的过早终止（`Premature Termination`）**；**0 例未锚定胡编，0 例遗漏约束！** |

> **关键发现**：在传统靠长文本 Prompt 描述用户背景的 `airline` 和 `retail` 中，用户模拟器高达 `40%~47%` 的轨迹会出现胡编订单号/航班号或遗漏约束；而在 `telecom` 中，由于用户模拟器的所有观测都必须通过调用 `User Tools` 从确定性的 `TelecomUserDB` 中读取，**彻底消除了“未锚定胡编（`Ungrounded Reference`）”与“遗漏约束（`Missing Constraint`）”错误**！仅有的 8 例错误全部是因为当 Agent 问“需要帮您转人工吗？”时，用户模拟器在回复“好的”的同时过早输出了 `###TRANSFER###` 终止符，导致 Agent 还没来得及调用 `transfer_to_human_agents` 工具对话就被迫结束了。

---

## 四、开源代码仓深度剖析与「论文 $\leftrightarrow$ 源码」对账（Paper vs. Code Audit）

通过对本地克隆代码仓 `papers/repos/tau2-bench/src/tau2/` 的全量源码精读，我们梳理出核心工程实现机制及 **5 处关键的「论文表述对比源码实现」差异与演进点**：

| 序号 | 审计维度 | 论文表述（`2506.07982v1`） | 源码真实实现（`repos/tau2-bench/src/tau2/`） | 工程原因与演进分析 |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **`telecom` 域的奖励计算基准 (`reward_basis`)** | `Sec 3.3 (p.5)` 称：*“In telecom, only assertion functions are used to evaluate task success.”*（仅用环境断言评判成功）。 | 在 `domains/telecom/tasks/manager.py:104-116` 中：<br>• 可修复任务（`fixable`）：`reward_basis = [RewardType.ENV_ASSERTION]`；<br>• **不可修复任务（`expected_failure=True`）**：`reward_basis = [RewardType.ENV_ASSERTION, RewardType.ACTION]`，且强制要求 `actions=[ToolCall(name="transfer_to_human_agents")]`！ | 对于不可修复故障（如合约到期、SIM 卡锁死），由于初始状态 `is_fixed(env)` 本就为 `False`，若只测环境断言 `is_fixed(env) == False`，Agent 什么都不做直接挂断也能拿满分。因此源码中对不可修复任务联合校验了 `ENV_ASSERTION` 与 `ACTION`（必须实际调用转人工工具）。 |
| **2** | **User Simulator 的工具调用角色翻转协议 (`flip_roles`)** | `Sec 3.1` 将 User 与 Agent 对称地建模为可调用工具的策略 $\pi_{\text{user}}$，未展开底层 API 如何让 `user` 角色发起函数调用。 | 在 `user/user_simulator_base.py:62-106` 与 `user_simulator.py:191-225` 中：由于 OpenAI/Anthropic Chat API **仅允许 `assistant` 角色生成 `tool_calls`**，`UserState.flip_roles()` 在调用 LLM 前将历史消息中的 `UserMessage` 翻转为 `AssistantMessage(tool_calls=...)`、将 Agent 发来的文本翻转为 `UserMessage`（同时过滤掉 Agent 私有的工具调用记录），拿到 LLM 输出后再将 `tool_calls` 的 `requestor` 翻转回 `"user"`。 | 这是实现双端协同（`Dual-Control`）最精妙的工程技巧：通过消息视角的镜像翻转（`Perspective Role-Flipping`），直接复用大模型原生的 `assistant` Function Calling 能力来驱动用户模拟器操作手机工具。 |
| **3** | **针对过早 `###TRANSFER###` 错误的提示词热修复** | `App. E.3 (p.22)` 指出 `telecom` 用户模拟器 100%（8/8）的错误是在回答 Agent“是否同意转人工”时提前吐出了 `###TRANSFER###` 终止符；附于 `codes/user_simulation_guideline.md:25` 的原版提示词仅写：*“generate '###TRANSFER###' when you are transferred”*。 | 在最新仓库 `src/tau2/user/guidelines.py:190, 256` 中，作者专门打上了补丁：<br>`"If you have been transferred to another agent, generate the '###TRANSFER###' token to indicate the transfer. Only do this after the agent has clearly indicated that you are being transferred."` | 源码直接根据论文人工错误归因结论修复了提示词漏洞，防止用户模拟器在“口头同意转接”阶段抢跑终止对话。 |
| **4** | **省流模式 (`Data Saver`) 降速系数文档与代码不一致** | `domains/telecom/user_tools.py:300` 的函数文档字符串（及衍生工具说明）写的是：*“Reduces speed by 50% if data saver mode is enabled”*（降低 50% 网速）。 | 在 `domains/telecom/user_tools.py:339-340` 的实际执行代码中：<br>`if self.db.device.data_saver_mode:`<br>`    base_speed_factor *= 0.2`（**实际降低了 80% 网速，仅保留 20%！**） | 为什么代码写成 `* 0.2`？因为 `5G` 在 `Excellent` 信号下的基准网速均值为 $(50+500)/2 = 275\text{ Mbps}$；若只降 50%（$137.5\text{ Mbps}$），仍高于 `mobile_data_issue` 判据 `>= 100 Mbps`（`Excellent`），会导致 `data_saver_mode_on` 子任务在初始状态下直接通过 `is_fixed` 校验而无法触发故障！写成 `* 0.2`（降为 $55\text{ Mbps}$，落入 `Good` 区间）才能保证三步自动验证器 `verify_task` 恒成立。 |
| **5** | **论文发表后的四大架构扩展（代码仓独有）** | 论文仅涵盖半双工文本对话及 `retail`、`airline`、`telecom` 三个域。 | 最新 `repos/tau2-bench/src/tau2/` 新增了四大模块：<br>① **全双工语音流式引擎（`FullDuplexOrchestrator` & `voice/`）**：支持按时间片（ticks）并发流式生成、打断策略（Interruption Policy）、附和词（Backchannels）、背景噪音合成与原生语音大模型评测；<br>② **知识库检索新域（`domains/banking_knowledge/`）**：引入 RAG 检索工具与金融知识库问答；<br>③ **自动化 LLM 轨迹审查器（`evaluator/review_llm_judge.py`）**：将 `App. E` 的人工错因分析固化为 12 类错误标签的 LLM-as-a-Judge 自动归因管线；<br>④ **多语言与区域包（`multilingual/` & `region.py`）**。 | 展现了从半双工文本基准向全双工实时语音交互与自动化错因诊断演进的完整工业级路线。 |

---

## 五、对我们「意图理解、记忆架构与端到端评测报告」的直接启发与落地映射

在我们的主报告 [storyline_and_evaluation_merged_technical_route_report.html](file:///d:/coding/sharing/.lavish/storyline_and_evaluation_merged_technical_route_report.html)（以及联接 Agent 的网络保障单据 + 多轮对话混合评测体系）中，$\tau^2$-Bench 提供了以下 **4 项可直接落地的核心机制参考**：

### 5.1 启发一：以「原子故障/意图选择集 + 三步确定性验证」升级我们的合成数据生成器
- **对应主报告章节**：第一部分（基于故事线的网元单据与多轮对话混合生成方法论）。
- **落地机制**：借鉴 `TaskManager.verify_task`（`manager.py:197-227`）与 `compose_tasks`（`utils.py:61-92`）：
  1. 将用户的长期记忆演化与网元侧异常状态拆解为正交的 `SelectionSet`（如：`日常主力应用集` $\times$ `周期性作息时间窗集` $\times$ `网元侧并发干扰/劣化条件集` $\times$ `用户表达习惯/模糊指代集`）；
  2. 为每个合成样本绑定确定性的三元组 $(f^{\text{init}}, f^{\text{sol}}, f^{\text{assert}})$，在生成阶段自动运行三步校验（特别是校验**如果漏掉某一条历史记忆或跳过某一次慢路径澄清，最终下发的保障单据参数断言必然失败**），从源头杜绝“不查记忆或少澄清一步也能蒙对参数”的捷径样本。

### 5.2 启发二：用「工具化状态读取」替代「长文本 Prompt 人设」，彻底根除用户模拟器幻觉
- **对应主报告章节**：第三部分（交互模拟与端到端评测框架）。
- **落地机制**：$\tau^2$-Bench 的表 2 实证表明，当用户模拟器仅靠 Prompt 记忆自身状态时，胡编与漏约束错误率高达 `40%~47%`；而将用户侧状态封装为结构化 `UserDB` 并通过 `Role-Flipping` 让模拟器调用只读工具查询后，胡编错误率直接降为 **0%**。在我们的多轮澄清评测中，当 Agent 发起慢路径追问（如确认具体加速应用、持续时长或当前终端卡顿现象）时，应让 User Simulator 从当前回合的 `Ground-Truth Memory Snapshot` 与终端状态字典中**确定性读取槽位值**作答，避免模拟器自由发挥偏离评测真值。

### 5.3 启发三：区分「单步快路径（`No-User / Direct Execution`）」与「多轮慢路径（`Dual-Control Clarification`）」的消融评测设计
- **对应主报告章节**：第二部分（快路径闭环与慢路径消歧澄清）与第四部分（核心评测指标体系）。
- **落地机制**：参考 `Figure 4` 的 `Default`、`No-User` 与 `Oracle Plan` 三联消融实验设计：
  - 在评测我们的联接 Agent 时，除了报告端到端多轮交互成功率外，同步设置 **`Oracle Memory`（直接给定完美检索到的标准记忆槽位）** 与 **`No-Clarification`（意图完整无需追问）** 两组对照基线，从而定量拆解出：**到底有多少失败源于“混合检索引擎没召回记忆”，有多少失败源于“慢路径多轮澄清沟通失误”，又有多少失败源于“最终工具参数组装错误”**。

### 5.4 启发四：核心评测指标统一采用「环境终态断言 (`ENV_ASSERTION`) + $\text{pass}^3$ 一致性指标」
- **对应主报告章节**：第四部分（核心评测指标与打分规则）。
- **落地机制**：
  1. **结果导向终态校验**：不死卡中间轮次的追问话术字面量，而是像 `EnvironmentEvaluator`（`evaluator_env.py:89-158`）一样，在沙箱中重放 Agent 最终触发的写操作工具调用（如 `create_qos_guarantee_ticket`），联合校验后台数据库终态断言（`ENV_ASSERTION`）与不可执行场景下的安全兜底动作（`ACTION`）；
  2. **$\text{pass}^k$ 稳定性红线**：单次评测 $\text{pass}^1$ 极易掩盖多轮对话中的随机波动（如 `telecom` 上 `gpt-4.1` 的 $\text{pass}^1 = 0.34$，但 $\text{pass}^3$ 跌至 `0.22`）。我们在端到端评测中固定采用 $n \ge 3$ 次独立试验下的 **$\text{pass}^3$** 作为衡量生产级可靠性的核心硬指标。

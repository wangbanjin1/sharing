# 2 τ-bench / τ²：答案存在数据库里

← [数据集图鉴索引](../datasets.md)　·　[阅读地图](../../reading_plan.md)　·　[四篇精读索引](../reading_notes.md)　·　[学习进度](../PROGRESS.md)

**三条标注**：〔原文〕数据集/仓库里的字面内容　·　〔实测〕在本地仓库里数出来或跑出来的　·　〔概括〕按代码结构归纳，不是某个字段的字面值

---

<a id="d2"></a>

<a id="d2-1"></a>

## 2.1 τ-bench 的任务文件

不是 JSON，是 Python 列表〔原文 `tau_bench/envs/retail/tasks.py`〕：

```python
tasks = [
    {
        "annotator": 0,
        "user_id": "yusuf_rossi_9620",
        "instruction": "You are Yusuf Rossi in 19122. You received your order #W2378156
                        and wish to exchange the mechanical keyboard for a similar one
                        but with clicky switches ...",
        "actions": [
            {"name": "find_user_id_by_name_zip",
             "arguments": {"first_name": "Yusuf", "last_name": "Rossi", "zip": "19122"}},
            {"name": "get_order_details", "arguments": {"order_id": "#W2378156"}},
            ...
            {"name": "exchange_delivered_order_items",
             "arguments": {"order_id": "#W2378156", "item_ids": [...],
                           "new_item_ids": [...], "payment_method_id": "credit_card_9513926"}},
        ],
    },
]
```

**`actions` 就是答案**：一条完整的、正确的工具调用序列。部分任务还带 `outputs`，是要 agent 在回复里说出的字符串。

<a id="d2-2"></a>

## 2.2 怎么判

`tau_bench/envs/base.py: calculate_reward` 干的事非常直接〔原文〕：

1. 记下 agent 跑完后的数据库哈希 `data_hash`；
2. 重新加载干净数据库，**把 gold `actions` 逐条回放**，得到 `gt_data_hash`；
3. 两个哈希相等 → 任务分 1，否则 0（`r_actions`）；
4. 若任务有 `outputs`，还要检查 agent 说过的话里是否包含这些字符串，缺一个就 0。

所以 retail / airline 的"答案"不是断言函数，而是**一段可回放的动作轨迹**，判的却是**终态哈希相等**——不是"你的动作序列和 gold 一样"，而是"你跑完的库和 gold 跑完的库一模一样"。

这有两个后果：

- **等效路径可以过**：先查 A 再查 B 还是先 B 后 A，只要终态相同就满分；
- **任何多余的写操作都会挂**：多说一句话没事，多调一次 `exchange_...` 就会改变哈希。

部分任务还叠一层 `outputs` 检查：指定的字符串必须真的出现在 agent 的回复里（`output.lower() in content.lower().replace(",", "")`），所以"做对了但没说"也会判 0。

<a id="d2-3"></a>

## 2.3 τ² 的 telecom 换了写法

`data/tau2/domains/telecom/tasks.json`，一条任务六个字段〔原文〕：

```json
{"id": "[mobile_data_issue]user_abroad_roaming_enabled_off[PERSONA:None]",
 "description": {"purpose": "Test resolution path: Mobile Data/Slow Internet Issues."},
 "user_scenario": {"persona": null, "instructions": {"domain": "telecom",
    "reason_for_call": "You mobile data is not working properly ...",
    "known_info": "You are John Smith with phone number 555-123-2002. You are currently abroad in France.",
    "task_instructions": "..."}},
 "ticket": "...",
 "initial_state": {
   "initialization_actions": [
     {"env_type": "user", "func_name": "set_user_info", "arguments": {"name": "John Smith", "phone_number": "555-123-2002"}},
     {"env_type": "user", "func_name": "set_user_location", "arguments": {"abroad": true}},
     {"env_type": "user", "func_name": "turn_roaming_off", "arguments": {}},
     {"env_type": "assistant", "func_name": "enable_roaming", "arguments": {"customer_id": "C1001", "line_id": "L1002"}}]},
 "evaluation_criteria": {
   "actions": [{"action_id": "toggle_roaming_0", "requestor": "user", "name": "toggle_roaming", "arguments": {}}],
   "env_assertions": [
     {"env_type": "user", "func_name": "assert_mobile_data_status", "arguments": {"expected_status": true}, "assert_value": true},
     {"env_type": "user", "func_name": "assert_internet_speed", "arguments": {"expected_speed": 200, "expected_desc": "excellent"}, "assert_value": true}],
   "reward_basis": ["ENV_ASSERTION"]}}
```

三处与 τ-bench 不同：

- **`initial_state` 里既有 user 侧动作也有 assistant 侧动作**——坏状态要两边一起设；
- **`actions` 里 `requestor: "user"`**——正确解法是用户动手，agent 只能指挥；
- **判分是 `env_assertions` 断言函数**，不是回放比对，所以允许等效路径。

<a id="d2-4"></a>

## 2.4 仓库实测数字

| 项 | 值〔实测〕 | 论文写的 |
|---|---|---|
| τ² retail 任务数 | 114 | 115 |
| τ² airline 任务数 | 50 | 50 |
| τ² telecom 任务数 | 2,285 | 2,285 ✓ |
| telecom 评测子集 | `split_tasks.json`：base 114 = train 74 + test 40（另有 small 20） | 114 ✓ |
| telecom persona 分布 | None 769 / Easy 760 / Hard 756 | 未给 |
| telecom 意图分布 | mms 1,984 / mobile_data 254 / service 47 | 未给 |
| τ-bench 原仓 retail / airline | **185 / 76** | 115 / 50 |

最后一行是这轮最值钱的发现：**论文的 115/50 已经过期**。τ-bench 仓库后来把任务扩到 185/76，τ² 又把 retail 收到 114。所以"τ-bench retail 上 74%"必须注明是哪个版本、哪个子集。

`reward_basis` 也按域不同〔实测〕：

| 域 | reward_basis | 条数 |
|---|---|---|
| telecom | `ENV_ASSERTION` | 2,253 |
| telecom | `ENV_ASSERTION` + `ACTION` | 32 |
| retail | `DB` + `NL_ASSERTION` | 112 |
| retail | `DB` | 2 |
| airline | `DB` + `COMMUNICATE` | 50 |

也就是说：**只有 telecom 是纯终态断言**；retail/airline 还要求自然语言断言与信息传达。论文里"只判终态"的说法只对 telecom 成立。

<a id="d2-5"></a>

## 2.5 三个坑

1. **任务 id 就是故障清单**。`[mms_issue]airplane_mode_on|bad_network_preference|break_apn_mms_setting|unseat_sim_card[PERSONA:Hard]`——竖线分隔的是叠加的原子故障，一眼能看出难度和该修几步〔实测〕。这个命名法值得直接抄。
2. **当前仓库已经比论文大一圈**：README 里 text benchmark 是 6 语言 × 3 域 = 900 题，还有 voice、banking_knowledge、intake 等新域。拿仓库跑分和论文数字对比是没有意义的。
3. **`data/tau2/results` 占 588 MB**（已发布的历史轨迹）。只想读任务的话，克隆后可以只留 `data/tau2/domains`。

---

← 上一篇 [1 LoCoMo](01_locomo.md)　·　[索引](../datasets.md)　·　下一篇 [3 PersonaMem-v3](03_personamem_v3.md) →

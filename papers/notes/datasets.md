# 数据集图鉴：十一个数据集，从文件长相到判分代码

← 返回 [阅读地图](../reading_plan.md)　·　论文机制见 [四篇精读索引](reading_notes.md)　·　[学习进度](PROGRESS.md)

**这份文件解决什么问题**：读完四篇论文，知道它们各自用了什么数据集，但"这个数据集长什么样、答案存在哪、跑起来怎么判"这三件事论文里都写不全。这里把十一个数据集对应的仓库全部拉到本地，照文件读一遍，逐条对上。

**材料**：2026-11-13 克隆到 `papers/repos/`（不入库，见 `.gitignore`）。每个仓库的 commit 见 §7。

**三条标注**：

| 标记 | 含义 |
|---|---|
| 〔原文〕 | 数据集/仓库里的字面内容，照录 |
| 〔实测〕 | 我在本地仓库里数出来或跑出来的 |
| 〔概括〕 | 我根据代码结构归纳的，不是某个字段的字面值 |

**一句话结论**：这十一个数据集的差别，一半在题目难度，另一半在**答案存在什么地方**——存在人工标注里、存在数据库终态里、存在 rubric 里、存在单元测试里、还是根本不存在（只存在一个"不该答"的约定）。

---

<a id="toc"></a>

## 目录

四篇数据集各成文件，按顺序读；每篇底部有上一篇 / 下一篇直链。

| # | 文件 | 行数 | 覆盖 | 小节 |
|---|---|---|---|---|
| 1 | [LoCoMo：答案是人写的，但最难的一类没有答案](datasets/01_locomo.md) | 99 | `locomo10.json` 的真实字段、cat 1–5 的分母、`evaluation.py` 的两套判分、五个坑 | [1.1](datasets/01_locomo.md#d1-1) 文件长相 · [1.2](datasets/01_locomo.md#d1-2) 答案怎么造 · [1.3](datasets/01_locomo.md#d1-3) 类别编号 · [1.4](datasets/01_locomo.md#d1-4) 怎么测 · [1.5](datasets/01_locomo.md#d1-5) 三个坑 |
| 2 | [τ-bench / τ²：答案存在数据库里](datasets/02_tau.md) | 132 | 两代任务文件差异、`calculate_reward` 的终态哈希、τ² 的 `init/sol/assert` 三件套、仓库实测条数 | [2.1](datasets/02_tau.md#d2-1) 任务文件 · [2.2](datasets/02_tau.md#d2-2) 怎么判 · [2.3](datasets/02_tau.md#d2-3) τ² 写法 · [2.4](datasets/02_tau.md#d2-4) 实测数字 · [2.5](datasets/02_tau.md#d2-5) 三个坑 |
| 3 | [PersonaMem-v3：仓库里没有题，题是跑出来的](datasets/03_personamem_v3.md) | 82 | 生成管线、一条题的真实字段、rubric 与 NDCG、27/31/33 三个数的来历 | [3.1](datasets/03_personamem_v3.md#d3-1) 结构 · [3.2](datasets/03_personamem_v3.md#d3-2) 一条题 · [3.3](datasets/03_personamem_v3.md#d3-3) 怎么测 · [3.4](datasets/03_personamem_v3.md#d3-4) 27/31/33 · [3.5](datasets/03_personamem_v3.md#d3-5) 坑 |
| 4 | [六个能力基准](datasets/04_ability.md) | 88 | HumanEval / MBPP / LeetCodeHard / ALFWorld / HotPotQA / WebShop，逐个说数据入口与判分 | [4.1](datasets/04_ability.md#d4-1) HumanEval · [4.2](datasets/04_ability.md#d4-2) MBPP · [4.3](datasets/04_ability.md#d4-3) LeetCodeHard · [4.4](datasets/04_ability.md#d4-4) ALFWorld · [4.5](datasets/04_ability.md#d4-5) HotPotQA · [4.6](datasets/04_ability.md#d4-6) WebShop |
| 5–7 | 见下方：抄什么 / 三个问题 / 仓库清单 | — | 跨数据集的结论与本地克隆清单，留在本文件 | [§5](#d5) · [§6](#d6) · [§7](#d7) |

---

<a id="d0"></a>

## 0 总表

| 数据集 | 仓库 | 数据入口 | 规模〔实测〕 | 答案存在哪 | 判分入口 |
|---|---|---|---|---|---|
| LoCoMo | `snap-research/locomo` | `data/locomo10.json` | 10 段 / 1,986 题 | 人工标注 `answer` + `evidence` | `task_eval/evaluation.py` |
| τ-bench retail | `sierra-research/tau-bench` | `tau_bench/envs/retail/tasks.py` | 185 条 | **gold 动作序列** + `outputs` | `envs/base.py: calculate_reward` |
| τ-bench airline | 同上 | `tau_bench/envs/airline/tasks.py` | 76 条 | 同上 | 同上 |
| τ² telecom | `sierra-research/tau2-bench` | `data/tau2/domains/telecom/tasks.json` | 2,285 条（用 114） | **断言函数** + 动作列表 | `evaluation_criteria.reward_basis` |
| PersonaMem-v3 | `bowen-upenn/PersonaMem-v3` | HF 数据集 + 本地 pipeline | 仓库不存题 | **rubric 维度 + 反例** | `evaluation/run_eval.py` |
| HumanEval | `openai/human-eval` | `data/HumanEval.jsonl.gz` | 164 题 | 人工单测 `test` | `human_eval/execution.py` |
| MBPP | google-research（见 §4.2） | `mbpp/mbpp.jsonl` | 974 题 | 每题 3 条 assert | 同 HumanEval 执行器 |
| LeetCodeHard | `noahshinn/reflexion` | `programming_runs/benchmarks/leetcode-hard-py.jsonl` | 296 条（用 40） | 测试用例 `test` | `evaluate_leet_results.py` |
| ALFWorld | `alfworld/alfworld` | 需 `alfworld-download` | 134 环境 | **环境完成信号** | 环境 `done` + `won` |
| HotPotQA | `hotpotqa/hotpot` | `download.sh`（CMU 服务器） | 113k 问答 | 短答案 + `supporting_facts` | `hotpot_evaluate_v1.py` |
| WebShop | `princeton-nlp/WebShop` | 需下载 `data/` | 100 环境（论文用法） | 属性匹配 + 商品 id | `run_envs/run_web_agent.py` |


下面按「文件长相 → 答案怎么来 → 怎么测 → 坑」四段逐个过：第 1–4 篇分别是 LoCoMo、τ 系、PersonaMem-v3、六个能力基准。

---

<a id="d5"></a>

## 5 抄什么，不抄什么

**抄 τ² 的三段式。** `init / sol / assert` 分离，断言写成纯函数，任务 id 写成故障清单。这套结构有两个直接好处：可以程序化组合出几千条题；可以在设计层面堵住"初始状态本来就满足断言"的假阳性。

**抄 LoCoMo 的 `evidence`，不抄它的判分。** `dia_id` 级别的证据指针让我们能算"检索命中率"（这也是 `eval_question_answering` 里 `recall_acc` 的来源）；但它的 F1 与关键词判分都太弱，cat 5 更是只查两个短语。

**抄 PersonaMem 的 `inferior_response`，但按 12 维 rubric 对齐。** 论文写的"八项共享检查"是 rubric 的子集，代码里已经合并成 12 维，还多了 `tool_call_match` 这类硬规则维。

**别抄的：靠 gold 轨迹回放做判分（τ-bench）。** 它要求每道题都有人写好一条完整的正确轨迹，还要能干净地回放到空库上；等效路径虽然能过，但只要多写一次库就会挂，而且**新增一题就要人工标一条轨迹**。

τ² 之所以能程序化组合出 2,285 条，靠的正是把"轨迹"换成"断言函数"——人只需要写原子子任务的三件套，组合与校验交给代码。要扩规模，就得走这条路。

---

<a id="d6"></a>

## 6 这些仓库能直接回答的三个问题

| 问题 | 去哪个文件 |
|---|---|
| "这个分数是在多少题上算的？" | `split_tasks.json`（τ²）、`Counter(category)`（LoCoMo）、`TASK_TYPE_META`（PersonaMem） |
| "判分到底看什么？" | `envs/base.py: calculate_reward`（τ-bench）、`evaluation_criteria.reward_basis`（τ²）、`metrics.py`（PersonaMem） |
| "论文里的名字对应哪个任务？" | `EVAL.md` 的对照表（PersonaMem）、任务 id（τ²）、`category` 数字（LoCoMo） |

---

<a id="d7"></a>

## 7 本地仓库清单

克隆于 2026-11-13，`--depth 1`，路径 `papers/repos/`（已在 `.gitignore` 里忽略）。

| 目录 | commit | 体积 | 有什么 | 缺什么 |
|---|---|---|---|---|
| `tau2-bench` | `c06b07d` (2026-11-10) | 1.1 GB | 三域任务 + 断言实现 + 评测器 + 语音/多语扩展 | 需要 `pip install -e .`（Python ≥3.12） |
| `tau-bench` | `59a200c` (2026-03-18) | 66 MB | retail 185 / airline 76 的历史任务与 `calculate_reward` | 已被 τ² 取代，别拿来对分 |
| `mem0` | `f1791da` (2026-11-06) | 58 MB | 抽取/更新提示词、CLI、集成 | `evaluation/` 目录是空的，LoCoMo 判分脚本没随仓发布 |
| `PersonaMem-v3` | `ad80a3b` (2026-08-29) | 21 MB | 生成 pipeline、评测器、12 维 rubric、任务注册表 | 题目与画像不在 git，HF 数据 + 需要 API key |
| `locomo` | `3eb6f2c` (2024-08-12) | 22 MB | `locomo10.json` 全文 + 官方 F1 判分 | 无 |
| `human-eval` | `b9453e8` (2026-10-16) | 218 KB | 164 题 + 执行沙箱 + pass@k | 无 |
| `reflexion` | `218cf0e` (2025-01-13) | 56 MB | 三域提示词、LeetCode 题库、历史轨迹 | 依赖各自环境的 data 下载 |
| `alfworld` | `aaba687` (2026-02-08) | 11 MB | 环境代码与配置 | 环境数据要 `alfworld-download` |
| `hotpot` | `3635853` (2019-02-14) | 210 KB | 判分脚本与下载脚本 | 数据在 CMU 服务器 |
| `WebShop` | `64fa2a5` (2024-09-05) | 86 MB | 环境与 agent 代码 | 商品/指令数据要单独下载 |
| `_data/mbpp.jsonl` | — | 550 KB | 974 题原始数据 | 从 google-research 直接抓的，无 git 历史 |

**Mem0 那三个提示词的现状值得单独记一句**：论文里的 `RESULTS_GENERATION_PROMPT` 在当前仓库已不存在，功能位换成了 `MEMORY_ANSWER_PROMPT`，内容也变了——它现在明确要求 `If no relevant information is found, make sure you don't say no information is found. Instead, accept the question and provide a general response.`〔原文〕。**一边删掉 adversarial 题，一边在提示词里禁止说"没找到"**，这两件事叠起来，LoCoMo 上的分数就没法用来衡量"会不会编"。

---

[↑ 回到目录](#toc)　·　分篇文件在 [datasets/](datasets/) 目录下

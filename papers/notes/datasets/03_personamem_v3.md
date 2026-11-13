# 3 PersonaMem-v3：仓库里没有题，题是跑出来的

← [数据集图鉴索引](../datasets.md)　·　[阅读地图](../../reading_plan.md)　·　[四篇精读索引](../reading_notes.md)　·　[学习进度](../PROGRESS.md)

**三条标注**：〔原文〕数据集/仓库里的字面内容　·　〔实测〕在本地仓库里数出来或跑出来的　·　〔概括〕按代码结构归纳，不是某个字段的字面值

---

<a id="d3"></a>

<a id="d3-1"></a>

## 3.1 结构

```
data_preparation/     把 gistbench 原始日志转成用户画像与历史
evaluation/           tasks/（每个任务一个模块）、metrics.py、task_registry.py
scripts/              run_persona_pipeline.py / prepare_eval_data.py / aggregate_eval.py
backend/{uid}/        生成物：profile.json、五个 app 的历史、test.json（评测题）
```

**git 里没有 benchmark 数据**，只有一份 10 用户的样例 CSV（`data/gistbench_sample_10users.csv`，5.8 MB）；正式数据在 HuggingFace，原始日志在 `facebook/gistbench`〔原文·README〕。

<a id="d3-2"></a>

## 3.2 一条题长什么样

`test.json` 由 `scripts/prepare_eval_data.py` 生成，一条包含〔概括·按 `data_preparation/visualize.py` 的字段与论文 4.9 的四项校验〕：

| 字段 | 内容 |
|---|---|
| `query` | 用户请求，且要求"没有用户历史就答不对" |
| `example_response` | 正例 |
| `inferior_response` | 反例，只在目标能力上更差（`_scrub_inferior_response` 会剥掉内部 id） |
| `groundtruth_preference` | 偏好，必须能回溯到真实互动 |
| `rubric_tags` | 本题适用哪些评分维度 |
| 候选池 / 期望工具调用 | 仅推荐类 / agentic 类 |

<a id="d3-3"></a>

## 3.3 怎么测

```bash
python scripts/prepare_eval_data.py --user_id 115
python -m evaluation.run_eval --user_id 115 --mode agent_tools \
       --run_dir results/115 --model ...
python scripts/aggregate_eval.py
```

`--mode` 的实际取值〔原文·`run_eval.py`〕：`llm_longctx`（历史拼进上下文）、`llm_memory`（文本记忆）、`mem0`、`mcp_agent`、`claude_code`、`codex`，另留 `agent_tools` / `codex_agent` 两个旧别名。论文里那 8 种评测模式，就是这张表挑 6 个、各配一个模型得来的。判分两类：

- **生成类**：LLM judge 按 rubric 打分，硬检查一票否决；
- **推荐类**：`recall@k / ndcg@k / mrr / hit@k`，另有 graded NDCG@3 / @5（`evaluation/metrics.py: ndcg_at_k`）。

**rubric 已经从 21 维合并到 12 维**〔原文·`task_registry.py` 注释〕，分成 judge 维（`preference_alignment` / `avoid_overpersonalization` / `voice_match`）与硬规则维（`negative_leakage` / `stale_preference_use` / `behavioral_hit` / `tool_call_match`），另有任务专属维度（如 `mistake_prevention_recall` / `false_alarm_emission`）。

<a id="d3-4"></a>

## 3.4 27 / 31 / 33 的真相

论文正文列 27 个任务名，数据集有 31 个 `task_type`，代码里是 **33 个注册名**〔实测〕。这一层现在能精确对上了：

- `task_registry.py` 的 `TASK_TYPE_META` 有 **33** 个条目；
- `DROPPED_TASK_TYPES` 有 **5** 个：`agentic_draft_audit`、`daily_personalized_briefing`、`preference_removal_regen`、`agentic_group_dm_summary`、`new_suggestions_recsys`，每个都写了废弃理由（重复、噪声主导、评分塌到 0、gold 不是真实互动）；
- 这 5 个里只有 **2 个**（`agentic_group_dm_summary`、`new_suggestions_recsys`）还在 `TASK_TYPE_META` 里，另外 3 个连注册项都删了；
- 所以 **33 − 2 = 31，正好等于数据集里的 31 个 task_type**。

论文的 27 是"表格里列出来的任务名"，31 是"注册表里活跃的类型"。差的 4 个具体是哪些，仓库里没有对照说明；从名字看像是**同一能力被拆成了不同打分口径**（`over_personalization_sycophancy` 单独一档、`hidden_persona_implicit_qa` 测隐性人格问答）〔概括〕。另有 `OLD_TO_NEW` 别名表，把 `t6_community_digest`、`t7_moment_recommendation`、`e4_google_search` 等历史名字映射到现行名。

所以三个数字是**三层**：论文表格 27（写作层）、数据集与注册表 31（发布层）、注册表含停用项 33（代码层）。引用哪个都行，但要说清是哪一层。

<a id="d3-5"></a>

## 3.5 坑

1. **没有 API key 就跑不起来**：生成与判分都调 Azure OpenAI / Gemini，README 要求先填 `.env`。
2. **每题都要重跑 pipeline**，一条题的成本包含多次生成 + 一次校验，不适合拿来做 nightly。
3. **EVAL.md 里的"paper name ↔ code name"表是唯一的对照物**，论文里的任务名直接搜代码是搜不到的（`Personalized feed ranking` → `personalized_recommendation`）。

---

← 上一篇 [2 τ-bench / τ²](02_tau.md)　·　[索引](../datasets.md)　·　下一篇 [4 六个能力基准](04_ability.md) →

# 1 LoCoMo：答案是人写的，但最难的一类没有答案

← [数据集图鉴索引](../datasets.md)　·　[阅读地图](../../reading_plan.md)　·　[四篇精读索引](../reading_notes.md)　·　[学习进度](../PROGRESS.md)

**三条标注**：〔原文〕数据集/仓库里的字面内容　·　〔实测〕在本地仓库里数出来或跑出来的　·　〔概括〕按代码结构归纳，不是某个字段的字面值

---

<a id="d1"></a>

<a id="d1-1"></a>

## 1.1 文件长什么样

`data/locomo10.json` 是一个长度 10 的数组，每段一个 `sample_id`〔原文〕：

```
qa / conversation / event_summary / observation / session_summary / sample_id
```

- `conversation` 里 `session_1`…`session_19` 加对应 `session_N_date_time`，另有两个说话人字段；
- 每个 turn 只有三个字段：`{"speaker": "Caroline", "dia_id": "D1:1", "text": "..."}`；
- 第一段对话有 **19 个 session**，第一个 session 18 轮〔实测〕——"600 轮"是整段累加，不是单个 session。

`qa` 每条四个字段〔原文〕：

```json
{"question": "When did Caroline go to the LGBTQ support group?",
 "answer": "7 May 2023",
 "evidence": ["D1:3"],
 "category": 2}
```

<a id="d1-2"></a>

## 1.2 答案怎么造

对话本身是**两个 LLM 扮演指定人格生成的**，仓库里 `scripts/generate_conversations.sh` 就是生成脚本，`data/multimodal_dialog/example/agent_a.json` 给了人格文件格式〔原文·README〕。QA 是人工标注，`evidence` 指到具体 `dia_id`。

**关键结构：category 5 没有 `answer` 字段。** 它只有 `adversarial_answer`：

```json
{"question": "What did Caroline realize after her charity race?",
 "evidence": ["D2:3"],
 "category": 5,
 "adversarial_answer": "self-care is important"}
```

对照 category 4 的同一事件：

```json
{"question": "What did Melanie realize after the charity race?",
 "answer": "self-care is important", "evidence": ["D2:3"], "category": 4}
```

**同一句话、同一个证据，只换了主语。** 所以 cat 5 的正确答案不是某段文本，而是"这一问没有答案，你该说没有"。`adversarial_answer` 是标注者记下的那个诱人错答——注意官方判分并不比对它，只检查你有没有说"没找到"（见 1.4）。

这是全篇设计得最巧的一类题，也是被删掉的那一类。

<a id="d1-3"></a>

## 1.3 类别编号与数量

| category | 类型 | 条数〔实测〕 |
|---|---|---|
| 1 | multi-hop（跨 session 聚合，常有两个 evidence） | 282 |
| 2 | temporal | 321 |
| 3 | open-domain（需要对话外的常识） | 96 |
| 4 | single-hop | 841 |
| 5 | adversarial | 446 |
| | 合计 | **1,986** |

`evaluation.py` 里对 `[2,3,4]` 的注释写成 "single-hop, temporal, open-domain"，与数据对不上——**2 是时间题，4 才是单跳**〔实测〕。引用类别编号时以数据为准，不要抄注释。

<a id="d1-4"></a>

## 1.4 怎么测

`task_eval/evaluation.py: eval_question_answering` 按类别分三个分支〔原文〕：

| 类别 | 判分 |
|---|---|
| 2 / 3 / 4 | `f1_score(output, answer)`；cat 3 先取 `answer.split(';')[0]` |
| 1 | 把答案拆成子答案，逐个子算 F1 再平均（`f1()`） |
| 5 | **关键词**：输出里含 `no information available` 或 `not mentioned` 得 1，否则 0 |

跑法：`bash scripts/evaluate_gpts.sh`，结果由 `evaluation_stats.analyze_aggr_acc` 汇总。

<a id="d1-5"></a>

## 1.5 三个坑

1. **446 / 1,986 = 22.5% 是 cat 5，Mem0 全删。** 它给的理由是"ground truth 不可得"——字面上成立，因为这一类确实没有 `answer` 字段。但代价是：**评测集里四分之一专门测"该不该说不知道"的题全部消失**，剩下的题答错只是丢分，不会因为"编了一条像样的答案"而被单独惩罚。而我们最怕的失败模式恰好是后者。
2. **cat 5 的官方判分本身很弱**：只要输出里出现那两个短语就满分。一个学会说 "not mentioned" 的系统可以刷满 446 题，这也解释了为什么大家更愿意引 LLM judge 的分。
3. **F1 与 J 是两套口径，别混。** 仓库自带 F1；Mem0 另写了 LLM judge（宽松，"沾到主题就算对"）。同一个单跳题组上，F1 38.72 与 J 67.13 差 28 点，全部来自判分口径，不来自能力。

---

[索引](../datasets.md)　·　下一篇 [2 τ-bench / τ²](02_tau.md) →

# 4 六个能力基准：HumanEval / MBPP / LeetCodeHard / ALFWorld / HotPotQA / WebShop

← [数据集图鉴索引](../datasets.md)　·　[阅读地图](../../reading_plan.md)　·　[四篇精读索引](../reading_notes.md)　·　[学习进度](../PROGRESS.md)

**三条标注**：〔原文〕数据集/仓库里的字面内容　·　〔实测〕在本地仓库里数出来或跑出来的　·　〔概括〕按代码结构归纳，不是某个字段的字面值

---

<a id="d4"></a>

<a id="d4-1"></a>

## 4.1 HumanEval

`data/HumanEval.jsonl.gz`，164 条，字段 `task_id / prompt / entry_point / canonical_solution / test`〔原文〕。

```json
{"task_id": "HumanEval/36",
 "prompt": "def fizz_buzz(n: int):\n    \"\"\"Return the number of times the digit 7 appears in integers less than n which are divisible by 11 or 13.\n    >>> fizz_buzz(50)\n    0\n    ...",
 "entry_point": "fizz_buzz",
 "canonical_solution": "...",
 "test": "def check(candidate):\n    assert candidate(50) == 0\n    assert candidate(78) == 2\n    ..."}
```

- 断言数：数 `assert` 关键字，平均 **8.08** 个/题，最少 1、最多 26〔实测〕；HumanEval 论文常引 7.7，差在计数方式，引用时说明怎么数的。
- 判分：`human_eval/execution.py` 把 `prompt + 生成 + test` 拼成文件跑，`check(candidate)` 全过才算过；`evaluate_functional_correctness` 里是 `pass@k` 的无偏估计。
- **题面里的 `>>>` 例子不是测试**，它们写在 docstring 里，`test` 才是隐藏测试。

<a id="d4-2"></a>

## 4.2 MBPP

`google-research/mbpp/mbpp.jsonl`（不在独立仓，在 google-research 大仓里；HF 也有一份）。974 条，字段 `text / code / task_id / test_setup_code / test_list / challenge_test_list`〔实测〕。

```json
{"text": "Write a function to find the minimum cost path to reach (m, n) from (0, 0) ...",
 "test_list": ["assert min_cost([[1, 2, 3], [4, 8, 2], [1, 5, 3]], 2, 2) == 8",
               "assert min_cost([[2, 3, 4], [5, 9, 3], [2, 6, 4]], 2, 2) == 12",
               "assert min_cost([[3, 4, 5], [6, 10, 4], [3, 7, 5]], 2, 2) == 16"]}
```

**每题固定 3 条断言**，只有 11 题带 `challenge_test_list`。这就是 FP 16.3% 的结构原因：3 条边界过窄，错实现很容易全过。

<a id="d4-3"></a>

## 4.3 LeetCodeHard

`reflexion/programming_runs/benchmarks/leetcode-hard-py.jsonl`：**296 条**〔实测〕，字段与 HumanEval 同构（`task_id / prompt / entry_point / cannonical_solution / test`，注意源码里确实拼成 `cannonical`）。

```json
{"task_id": "median-of-two-sorted-arrays",
 "prompt": "# Given two sorted arrays `nums1` and `nums2` ...\n# Example 1:\n# Input: nums1 = [1,3], nums2 = [2]\n# Output: 2.00000 ...",
 "entry_point": "findMedianSortedArrays", "test": "..."}
```

论文写"40 道 2022-10-08 之后发布的 hard 题"，仓库里是 296 条题库〔实测〕，**没有单独标出那 40 条**——`root/leetcode_metadata` 存的是运行日志，不是筛选清单。要复现 40 题只能按发布日期自己切。

<a id="d4-4"></a>

## 4.4 ALFWorld

仓库只有代码与配置，环境数据要 `python scripts/alfworld-download`（约几百 MB）。134 个环境 / 6 类任务，文本版基于 TextWorld。

判分：环境的 `done` 与 `won` 两个布尔，**没有分步奖励**。Reflexion 因此必须自己造失败信号（重复动作 3 轮 / 总步数 30）。

<a id="d4-5"></a>

## 4.5 HotPotQA

仓库不含数据，`download.sh` 从 CMU 服务器拉三个文件（`hotpot_dev_distractor_v1.json` 等，dev distractor 约 45 MB）。一条记录的长相：

```
{"_id": ..., "question": "...", "answer": "...", "type": "bridge|comparison",
 "level": "easy|medium|hard", "supporting_facts": [[title, sent_idx], ...],
 "context": [[title, [sentences...]], ...]}
```

判分：`hotpot_evaluate_v1.py` 同时算 **EM 与 F1**（归一化后 token 级）。Reflexion 只用 EM 当二元奖励。

<a id="d4-6"></a>

## 4.6 WebShop

仓库含代码与少量资源，商品与指令数据要单独下载（`README` 里的 `./setup.sh -d all`）。判分不看文本，看**最终购买的商品是否命中目标属性集 + 商品 id**。

---

← 上一篇 [3 PersonaMem-v3](03_personamem_v3.md)　·　[索引](../datasets.md)

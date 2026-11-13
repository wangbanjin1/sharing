# 4 Reflexion：把失败写成一段话

← [四篇精读索引](../reading_notes.md)　·　[阅读地图](../../reading_plan.md)　·　[数据集图鉴](../datasets.md)　·　[学习进度](../PROGRESS.md)

**标注层级**：〔正文〕论文原文明确写出 / 〔图表〕仅见于图或表 / 〔实现〕仓库代码与 README / 〔数据集〕数据集自身的定义 / 〔推导〕我按原文数字算出

---

<a id="ch4"></a>

<a id="c4-1"></a>

## 4.1 算法

三件套：Actor（生成动作）、Evaluator（打分）、Self-Reflection（写反思）。附录 Algorithm 1 的循环是〔正文〕：

```
初始化 Actor / Evaluator / Self-Reflection
用 π_θ 生成初始轨迹 τ0
τ0 交给 Evaluator 评分；生成 sr0；mem ← [sr0]
t = 0
while 未通过 and t < max_trials:
    用 π_θ（θ 含 mem）生成 τt
    Evaluator 评 τt
    生成 srt；mem ← mem ⊕ srt
    t += 1
```

$$\text{mem}\leftarrow\text{mem}\oplus sr_t,\qquad |\text{mem}|\le\Omega,\ \Omega\in\{1,3\}$$

**`mem` 是滑窗，不是库。** 上限按域不同：ALFWorld 与 HotPotQA 取 3，代码任务取 **1**〔正文〕。这不是实现偷懒，是原文明说的设计取舍（受上下文长度约束），并在 limitations 里承认"希望未来换成向量库或 SQL"。

<a id="c4-2"></a>

## 4.2 三个域的设置差异

| 域 | 规模 | 失败信号怎么来 | 记忆上限 | 备注 |
|---|---|---|---|---|
| ALFWorld | 134 个环境 / 6 类任务 | **自评**：同一动作同一反馈超过 3 轮，或总步数超过 30 | 3 | 环境只在任务完成时给信号，所以必须自己造失败判据 |
| HotPotQA | 100 题 | **精确匹配**（exact match）判定对错 | 3 | CoT 版喂 gold 上下文，只考推理；ReAct 版走 Wikipedia API，考"检索+推理" |
| HumanEval / MBPP / LeetcodeHard | 164 / — / 40 题 | **自生成单元测试**跑一遍 | 1 | 测试数 $n\le 6$，先用 CoT 生成、再用 AST 过滤掉语法错 |

ALFWorld 那条启发式很值得记：**没有外部奖励时，用"卡住"当失败信号**——重复动作 3 轮、或步数超 30，就判定该反思了。这是个便宜的代理指标，不需要 judge。

<a id="c4-3"></a>

## 4.3 结果，以及一个必须讲的例外

Table 1〔图表〕：

| Benchmark | 此前 SOTA | Reflexion |
|---|---|---|
| HumanEval (Python) | 80.1（GPT-4） | **91.0** |
| HumanEval (Rust, 最难 50 题) | 60.0（GPT-4） | 68.0 |
| **MBPP (Python)** | **80.1（GPT-4）** | **77.1** |
| MBPP (Rust) | 70.9 | 75.4 |
| Leetcode Hard (Python) | 7.5 | 15.0 |

**HumanEval 赢 11 点，MBPP 输 3 点，同一套方法、同一个底座。** 论文没有把这个当作重点讲，但 Table 2 给了机制解释〔图表〕：

| | Base | Reflexion | TP | FN | **FP** | TN |
|---|---|---|---|---|---|---|
| HumanEval (PY) | 0.80 | 0.91 | 0.99 | 0.40 | **0.01** | 0.60 |
| MBPP (PY) | 0.80 | 0.77 | 0.84 | 0.59 | **0.16** | 0.41 |

- **FP = 自测通过、实现其实错**：HumanEval 只有 **1.4%**（表里四舍五入成 0.01），MBPP 高达 **16.3%**。FP 高意味着 agent 以为自己做对了，提前收敛，不再反思——MBPP 的失败几乎全从这里来。
- **FN = 自测失败、实现其实对**：40%（HumanEval）和 59%（MBPP）。这个数更吓人：一半以上的"测试失败"是误报，agent 会去"修"一个本来正确的解。

按 TP 折算一下（报告值 × TP = 真实正确率）〔推导〕：HumanEval 0.91×0.99 ≈ **0.90**，MBPP 0.77×0.84 ≈ **0.65**。也就是说 MBPP 上它不是"输 3 点"，是**输 15 点**。

所以 **91.0 这个数要打折**：它是"自测口径的 pass@1"，不是严格 pass@1。原文自己用 pass@1 这个词，但同时明确说 AlphaCode / Self-Debugging / CodeRL 因为依赖 ground-truth 测试而 "invalidate pass@1 eligibility"，它自己用自生成测试所以"eligible"〔正文〕。这个论证在形式上成立，但 Table 2 的 FP 率就是它的水分。

对我们的直接启示：**用模型自己生成的验证器验证自己，FP 和 FN 会同时偏高，而两者的相对大小决定这套方法看起来有效还是无效。** 这是"自证循环"最具体的一个量化案例，比空谈"要防自证"有用得多。

<a id="c4-4"></a>

## 4.4 消融：没有测试的反思是有害的

HumanEval Rust 最难 50 题，GPT-4 底座〔图表 Table 3〕：

| 配置 | 有测试生成 | 有自我反思 | pass@1 |
|---|---|---|---|
| 基线 | ✗ | ✗ | 0.60 |
| 只反思、不给测试 | ✗ | ✓ | **0.52** |
| 只给测试、不反思 | ✓ | ✗ | 0.60 |
| 完整 Reflexion | ✓ | ✓ | **0.68** |

两件事：

1. **没有测试生成时，反思让成绩变差（0.60 → 0.52）。** 原文的解释是 agent 无法判断当前实现对不对，只能每轮都改，做出**有害编辑**。
2. **只有测试、没有反思，等于没提升（0.60）。** 测试能抓语法和逻辑错，但"修"这一步不会因为看到报错就自动发生。

这就是"反思"真正的适用条件：**必须先有一个可信的、外部的判定信号，反思才有对象**。否则反思会退化成"让模型自我批评"，而自我批评没有 ground truth，容易把偶然因素固化成规则。

还有一个更硬的边界〔图表 Table 4〕：换成 starchat-beta 做底座，pass@1 **0.26 → 0.26，8 次运行零提升**。**反思能力本身依赖底座模型**，弱模型上这套方法完全失效。

<a id="c4-5"></a>

## 4.5 反思产物是什么形态

附录里的真实样例（原文照录的思路）：

> "My reasoning for the profession John Lanchester and Alan Dean Foster have in common failed because I incorrectly assumed that they both had the same profession. In the future, when attempting this question, I should focus on better researching the individual backgrounds of both authors…"

**一段 60–90 词的英文自然语言，不是结构化条目。** 它包含三件事：哪一步错了、为什么错、下次该怎么做。没有槽位、没有 id、没有生效条件、没有失效时间。

→ 这直接回答了我们报告里 S-03 那道题的设计问题：Reflexion 式的"程序记忆"是**叙述性教训**，检索时靠语义相似度而不是键匹配。所以如果我们要测"系统能不能自己归纳规则"，判分不能用"规则是否与 gold 字面一致"，只能判"下次同类任务是否不再犯"——也就是**必须多次运行**，单次任务测不出来。

<a id="c4-6"></a>

## 4.6 边界

- 需要**可判定的成败信号 + 可重试**。开放式对话里没有 evaluator，这套就退化成自我批评。
- 原文自己承认会陷入局部最优。WebShop 上跑 4 轮就终止，因为"没显示出改善迹象"，也没生成有用的反思〔正文〕。原文的判断是：**需要大量探索多样性的任务，Reflexion 解不了**——ALFWorld 能解是因为允许的动作都写在观测里，HotPotQA 能解是因为维基检索的搜索空间足够宽。
- 代码场景受限于 TDD：非确定性函数、有副作用、依赖硬件的函数，输入输出映射写不准。
- 记忆是滑窗（1–3 条），**它不积累，只覆盖**。所以它不解决"长期一致性"，只解决"这一轮别重复上一轮的错误"。

---

← 上一章 [PersonaMem-v3](03_personamem_v3.md)　·　[索引](../reading_notes.md)　·　下一章 [数据集](05_datasets.md) →

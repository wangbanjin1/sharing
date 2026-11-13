# 四篇精读：索引

← 返回 [阅读地图](../reading_plan.md)　·　[学习进度](PROGRESS.md)　·　[数据集图鉴](datasets.md)　·　[记忆系统综述](memory_summary.md)

**范围**：Mem0（arXiv 2504.19413）、τ²-bench（2506.07982）、PersonaMem-v3（2608.21381 v2）、Reflexion（2303.11366）；四篇涉及的十一个数据集与各自的答案构造见第 5 篇。
**材料**：Mem0 / τ² / Reflexion 用本地 PDF 逐页提取；PersonaMem-v3 的 PDF 有 14.5 MB，直连反复断流，改用 arXiv HTML v2 全文 + HuggingFace 数据集卡片核对。

**标注层级**：每条数字都要能追到来源，所以分五档。

| 标记 | 含义 |
|---|---|
| 〔正文〕 | 论文正文明确写出的设定、数字、结论 |
| 〔图表〕 | 只出现在图/表里，正文未复述（引用时要注明图表号） |
| 〔实现〕 | 仓库代码、README、数据集卡片里的实际做法 |
| 〔数据集〕 | 数据集自己的论文 / 发行仓库里的定义，不是这四篇写的 |
| 〔推导〕 | 我按原文数字算出来的，原文没有这个数 |

**读法**：四篇不是同一条线上的四段。Mem0 是被测者，PersonaMem-v3 是考卷（它把 Mem0 作为一个 mode，最弱的一档：偏好演化 56.9%、过期立场率 51.4%）；τ² 与 PersonaMem-v3 并列，一个只判终态、一个判生成质量；Reflexion 提供的不是评测方法，而是一种记忆形态。**Mem0 与 PersonaMem-v3 的分数不能放在一张表里**，τ² 与 PersonaMem-v3 的判分方式必须二选一或显式分层。

---

<a id="toc"></a>

## 目录

七篇各自成文件，按顺序读即可；每篇底部有上一章 / 下一章的直链。

| # | 文件 | 行数 | 主题 | 小节 |
|---|---|---|---|---|
| 1 | [Mem0：抽取—更新两段式 → V3 只 ADD](papers/01_mem0.md) | 283 | 论文算法、Mem0ᵍ 图管线、V3 只 ADD 的八阶段实现、七处落差、冗余与适用边界、评测集归属、榜单不可比 | [1.1](papers/01_mem0.md#c1-1) 流水线 · [1.2](papers/01_mem0.md#c1-2) 结果 · [1.3](papers/01_mem0.md#c1-3) Mem0ᵍ · [1.4](papers/01_mem0.md#c1-4) 提示词 · [1.5](papers/01_mem0.md#c1-5) V3 · [1.6](papers/01_mem0.md#c1-6) 落差 · [1.7](papers/01_mem0.md#c1-7) 冗余 · [1.8](papers/01_mem0.md#c1-8) 评测集 · [1.9](papers/01_mem0.md#c1-9) 榜单 · [1.10](papers/01_mem0.md#c1-10) 边界 |
| 2 | [τ²-bench：只判终态的双端基准](papers/02_tau2_bench.md) | 166 | 七元组形式化、五阶段构建、五种评估准则它只用一种、Pass^k 与三分法消融、用户模拟器、实现对照 | [2.1](papers/02_tau2_bench.md#c2-1) 形式化 · [2.2](papers/02_tau2_bench.md#c2-2) 构建 · [2.3](papers/02_tau2_bench.md#c2-3) 准则 · [2.4](papers/02_tau2_bench.md#c2-4) 结果 · [2.5](papers/02_tau2_bench.md#c2-5) 模拟器 · [2.6](papers/02_tau2_bench.md#c2-6) 提示词 · [2.7](papers/02_tau2_bench.md#c2-7) 对照 |
| 3 | [PersonaMem-v3：把题面做成四族二十七类](papers/03_personamem_v3.md) | 161 | 数据管线、两条规模事实、77/13/8/1 的分母、27 vs 31 的口径冲突、八项判分、三个实验、+37 点的来源 | [3.1](papers/03_personamem_v3.md#c3-1) 管线 · [3.2](papers/03_personamem_v3.md#c3-2) 规模 · [3.3](papers/03_personamem_v3.md#c3-3) 轨迹 · [3.4](papers/03_personamem_v3.md#c3-4) 分类 · [3.5](papers/03_personamem_v3.md#c3-5) 判分 · [3.6](papers/03_personamem_v3.md#c3-6) 实验 · [3.7](papers/03_personamem_v3.md#c3-7) 错误 · [3.8](papers/03_personamem_v3.md#c3-8) 预算 |
| 4 | [Reflexion：把失败写成一段话](papers/04_reflexion.md) | 120 | 算法、三个域的差异、结果与一个必须讲的例外、无测试反思有害的消融、反思产物形态、边界 | [4.1](papers/04_reflexion.md#c4-1) 算法 · [4.2](papers/04_reflexion.md#c4-2) 三域 · [4.3](papers/04_reflexion.md#c4-3) 结果 · [4.4](papers/04_reflexion.md#c4-4) 消融 · [4.5](papers/04_reflexion.md#c4-5) 形态 · [4.6](papers/04_reflexion.md#c4-6) 边界 |
| 5 | [数据集：十一个数据集，五种答案形态](papers/05_datasets.md) | 323 | 总表、LoCoMo / τ 系 / PersonaMem 的答案怎么造、六个能力基准、五种答案形态、三条落点、十二个真实例子 | [5.1](papers/05_datasets.md#c5-1) 总表 · [5.2](papers/05_datasets.md#c5-2) LoCoMo · [5.3](papers/05_datasets.md#c5-3) τ 系 · [5.4](papers/05_datasets.md#c5-4) PersonaMem · [5.5](papers/05_datasets.md#c5-5) 六基准 · [5.6](papers/05_datasets.md#c5-6) 五形态 · [5.7](papers/05_datasets.md#c5-7) 落点 · [5.8](papers/05_datasets.md#c5-8) 例子 |
| 6 | [横向：能搬进报告的东西](papers/06_cross_paper.md) | 39 | 七条改法、论文自身的三处口径冲突 | [6.1](papers/06_cross_paper.md#c6-1) 七条改法 · [6.2](papers/06_cross_paper.md#c6-2) 口径冲突 |
| 7 | [工程上会踩的五个坑](papers/07_pitfalls.md) | 19 | PDF 下不全、版本对不上、提示词合规、31/27 混用、91% 不是 pass@1 | — |

**第 5 篇与 [数据集图鉴](datasets.md) 的分工**：第 5 篇站在论文侧，回答"这个数据集为什么存在、答案是谁造的、因此测不到什么"；图鉴站在仓库侧，回答"文件长什么样、字段叫什么、判分代码在哪一行、本地克隆在哪"。两份都看才不会把口径写错。

---

[↑ 回到目录](#toc)　·　分篇文件在 [papers/](papers/) 目录下

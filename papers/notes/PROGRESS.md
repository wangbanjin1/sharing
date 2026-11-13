# 学习进度

← 返回 [阅读地图](../reading_plan.md)　·　[阅读笔记](reading_notes.md)　·　[数据集图鉴](datasets.md)　·　[记忆系统综述](memory_summary.md)

**更新**：2026-11-13

**口径**：一行只记「哪一侧读完了」，不记读了几遍。论文侧 = 原文机制与数字；实现侧 = 仓库代码核对；数据集侧 = 文件结构、答案构造、判分代码；报告侧 = 是否已并入 `.lavish/` 报告。

<a id="toc"></a>

## 目录

- [§1 总览](#p1) — 六个对象 × 四个维度的完成度矩阵
- [§2 逐项完成度](#p2) — [Mem0](#p2-1) · [τ² / PersonaMem / Reflexion](#p2-2) · [数据集与仓库](#p2-3)
- [§3 产出清单](#p3) — 四份文档的规模与覆盖
- [§4 待补清单](#p4) — 五项，按优先级
- [§5 口径约定](#p5) — 引分四件套 + 三条禁令

---

<a id="p1"></a>

## 1 总览

| 对象 | 论文侧 | 实现侧 | 数据集侧 | 报告侧 | 主要落点 |
|---|---|---|---|---|---|
| Mem0 | ✓ | ✓ | ✓ | 部分 | [§1.1–1.10](papers/01_mem0.md) |
| τ²-bench | ✓ | ✓ | ✓ | 部分 | [§2](papers/02_tau2_bench.md) · [datasets §2](datasets/02_tau.md) |
| PersonaMem-v3 | ✓（缺图） | ✓ | ✓ | 部分 | [§3](papers/03_personamem_v3.md) · [datasets §3](datasets/03_personamem_v3.md) |
| Reflexion | ✓ | ✓ | ✓ | 未并入 | [§4](papers/04_reflexion.md) · [datasets §4](datasets/04_ability.md) |
| 数据集总表（11 个） | — | ✓ | ✓ | 未并入 | [§5](papers/05_datasets.md) · [datasets §0](datasets.md#d0) |
| 因子体系（L1 13 + L2 27） | — | — | — | ✓ | 报告 4.4 + `two_layer_factors.xlsx` |

「部分」指结论已经写进笔记，但报告正文的还是旧版；逐条列在 [§4](#p4)。

<a id="p2"></a>

## 2 逐项完成度

<a id="p2-1"></a>

### 2.1 Mem0

| 项 | 状态 | 说明 |
|---|---|---|
| 论文机制（抽取 + 更新两段式） | ✓ | [§1.1](papers/01_mem0.md#c1-1)，含附录 B Algorithm 1 的伪码与判定顺序 |
| 主结果与效率前沿 | ✓ | [§1.2](papers/01_mem0.md#c1-2)，Table 1/2 全表 + 三条推导（总分不等于四类平均） |
| Mem0ᵍ 图管线 | ✓ | [§1.3](papers/01_mem0.md#c1-3)，四步 + 两种删除语义并存的问题 |
| 旧版提示词三面对账 | ✓ | [§1.4](papers/01_mem0.md#c1-4)，7 类信息 / 四操作 / 5–6 词答案 |
| V3 实现（ADD-only 8 阶段） | ✓ | [§1.5](papers/01_mem0.md#c1-5)，含三处实现事实与检索公式 |
| 论文 → V3 七处落差 | ✓ | [§1.6](papers/01_mem0.md#c1-6)，含成本账 |
| 冗余与适用边界 | ✓ | [§1.7](papers/01_mem0.md#c1-7)，冗余来源 3 / 收敛 4 / 不成立 4 |
| 评测集归属 | ✓ | [§1.8](papers/01_mem0.md#c1-8)，`evaluation/` 是 submodule，BEAM 是 ICLR 2026 第三方 |
| 榜单不可比 | ✓ | [§1.9](papers/01_mem0.md#c1-9)，三处硬伤 |
| **V3 对应的论文原文** | **缺** | 本地只有 2504.19413（2025-04）；讲 V3 的那版材料未到，§1.5–1.9 全部基于代码与二手聚合站 |

<a id="p2-2"></a>

### 2.2 τ²-bench / PersonaMem-v3 / Reflexion

| 项 | 状态 | 缺口 |
|---|---|---|
| τ² 七元组与五准则 | ✓ | — |
| τ² 终态判分与 Pass^k | ✓ | — |
| τ² 实跑验证 | **未跑** | 需环境与 API，未做 |
| PersonaMem 四族 31 类 | ✓ | — |
| PersonaMem 图表数值 | **缺** | Fig 3 热力图、Fig 9 容量曲线、Fig 11 错误环只有图 |
| Reflexion 三个域差异 | ✓ | — |
| Reflexion 91% 的口径折算 | ✓ | 已按 Table 2 的 TP 折算到 89.7 / 64.7 |

<a id="p2-3"></a>

### 2.3 数据集与仓库

- 11 个数据集全部过了一遍「文件长相 → 答案怎么来 → 怎么测 → 坑」，见 [数据集图鉴](datasets.md) 的四篇分文件。
- 13 个仓库（含 `memory-benchmarks`、`_data/mbpp.jsonl`）已克隆到 `papers/repos/`，总计约 1.4 GB。
- 读代码后修正过的判断都写在 `datasets/*.md` 对应小节，不在正文保留"原以为…"的过程。

<a id="p3"></a>

## 3 产出清单

| 文件 | 行数 | 覆盖 |
|---|---|---|
| [notes/reading_notes.md](reading_notes.md) | 42 | 索引：标注层级、读法、七篇分文件的直达表 |
| [notes/papers/01_mem0.md](papers/01_mem0.md) | 283 | Mem0 论文两段式 → V3 只 ADD 八阶段，含七处落差、冗余边界、评测集归属、榜单不可比 |
| [notes/papers/02_tau2_bench.md](papers/02_tau2_bench.md) | 166 | τ² 七元组、五阶段构建、Pass^k、三份法消融、用户模拟器 |
| [notes/papers/03_personamem_v3.md](papers/03_personamem_v3.md) | 161 | PersonaMem-v3 数据管线、27 vs 31、八项判分、三个实验 |
| [notes/papers/04_reflexion.md](papers/04_reflexion.md) | 120 | Reflexion 算法、三域差异、91% 的口径折算、无测试反思有害 |
| [notes/papers/05_datasets.md](papers/05_datasets.md) | 323 | 11 个数据集为什么存在、答案怎么造、五种答案形态、12 个例子 |
| [notes/papers/06_cross_paper.md](papers/06_cross_paper.md) | 39 | 七条改法、论文自身三处口径冲突 |
| [notes/papers/07_pitfalls.md](papers/07_pitfalls.md) | 19 | 五个工程坑 |
| [notes/datasets.md](datasets.md) | 112 | 数据集图鉴索引：总表、目录、抄什么、仓库清单 |
| [notes/datasets/01_locomo.md](datasets/01_locomo.md) | 99 | LoCoMo 字段、分母、两套判分、五个坑 |
| [notes/datasets/02_tau.md](datasets/02_tau.md) | 132 | τ-bench / τ² 任务文件、终态哈希、断言三件套 |
| [notes/datasets/03_personamem_v3.md](datasets/03_personamem_v3.md) | 82 | PersonaMem-v3 生成管线、rubric、27/31/33 |
| [notes/datasets/04_ability.md](datasets/04_ability.md) | 88 | 六个能力基准的数据入口与判分 |
| [notes/memory_summary.md](memory_summary.md) | 808 | 七套记忆系统拆解 + 版本对照 |
| [notes/PROGRESS.md](PROGRESS.md) | 136 | 本文件：完成度、待补、口径 |
| `.lavish/*.html` | — | 技术路线报告（含 4.4 两层因子表） |
| `.lavish/two_layer_factors.xlsx` | 41 行 × 3 sheet | 因子取值机读版 |

<a id="p4"></a>

## 4 待补清单

按优先级：

1. **Mem0 V3 的论文材料**。当前 §1.5–1.9 缺论文级出处，所有 V3 结论只能标〔实现〕。材料到位后补「设计动机」与「官方口径」两节。
2. **报告正文同步**。三处已确认但未并入：[§6.1 七条改法](papers/06_cross_paper.md)、`datasets.md` 的分母口径修正、mem0 V3 的一致性降级结论。
3. **PersonaMem-v3 图表**。三张图只有影像没有数字，要引具体值必须读图或等完整 PDF。
4. **mem0 评测实跑**。本地无 `OPENAI_API_KEY` / `MEM0_API_KEY`，且需 `docker compose up -d` 起 mem0 + qdrant；最小验证命令已备：`--conversations 0 --max-questions 20`。
5. **横向系统材料**。Hindsight、Zep/Graphiti、MemOS 的原始材料均未到，目前 §1.9 只能引聚合站分数并标注来源性质。

<a id="p5"></a>

## 5 口径约定

引任何分数必须四件套齐全，缺一项不进对比表：

| 项 | 例 |
|---|---|
| 数据集 + 版本/子集 | LoCoMo 10 段 / 1,540 题（排除 adversarial） |
| 答案来源 | 人工答案 / rubric 检查项 / 终态哈希 |
| 判分器 | LLM judge（型号）/ 代码执行 / 字符串匹配 |
| 检索预算 | top_50 / top_200、tokens per query |

三条禁令：

1. 不把「厂商自报」写成「SOTA」。
2. 不把不同 cutoff、不同 judge、不同分母的数放进同一列。
3. 不用四类题的简单平均代替总分（Mem0 差 5.2 点，Mem0ᵍ 差 6.75 点）。

---

[↑ 回到目录](#toc)　·　[→ 阅读笔记](reading_notes.md)　·　[→ 数据集图鉴](datasets.md)

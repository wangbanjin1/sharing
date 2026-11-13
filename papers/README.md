# papers/ 资料目录

本目录存放论文与 benchmark 原始材料，**按种类分目录**。原始材料由用户提供并先自行阅读，我方只在其后做归类、整理与产出。

## 目录结构

| 目录 | 放什么 | 例 |
|---|---|---|
| `inbox/` | 新到、尚未归类的材料。落地后在此暂存，归类时再移动 | 刚下载的 PDF |
| `memory/` | 记忆系统与上下文管理 | MemoryOS、MemOS、Mem0、MemoryBank、MIRIX、MemGPT |
| `benchmark/` | 评测基准、数据集、用户模拟器 | PersonaMem-v3、τ²-bench、LoCoMo、LongMemEval、IN3 |
| `agent/` | Agent 能力：推理、自省、工具使用、多智能体 | Reflexion、ReAct、ExpeL、Self-Refine |
| `notes/` | 我方产出的讲义、综述、拆解 | `memory_summary.md`（七套记忆系统精读）；`reading_notes.md`（四篇精读索引）＋ `papers/`（01 Mem0 / 02 τ² / 03 PersonaMem / 04 Reflexion / 05 数据集 / 06 横向 / 07 工程坑，七篇各自成文件）；`datasets.md`（数据集图鉴索引）＋ `datasets/`（01 LoCoMo / 02 τ 系 / 03 PersonaMem-v3 / 04 六个能力基准，另含总表、抄什么、仓库清单）；`PROGRESS.md`（学习进度：逐篇完成度、产出清单、待补项、引分口径） |

## 命名约定

- 原始材料：`<简称>_<年份>.<ext>`，年份取论文首次公开年。例：`PersonaMem-v3_2026.pdf`
- 我方笔记：`notes/<简称>_notes.md`，与材料同名以便对应
- 一篇论文有多种格式（pdf / html / 补充材料）时，统一放同一目录，用后缀区分：`Mem0_2025.pdf`、`Mem0_2025_supp.pdf`

## 阅读地图

`reading_plan.md` 是这轮阅读的导读：每篇的定位、读之前先定的判断问题、读法（哪几节精读）、配套工作、以及**读完后该给我什么材料**。四篇的读序与对应关系见该文件开头的总览表。

## 清单

状态含义：**已给材料** = 用户已提供原始文件；**待给** = 在阅读清单里但材料未到；**已产出** = 我方已有对应笔记。

| 分类 | 简称 | 全称 / 主题 | 出处 | 材料 | 状态 | 关联 |
|---|---|---|---|---|---|---|
| benchmark | PersonaMem-v3 | 全平台个人智能基准（GIST-Bench 起底，31 类任务） | arXiv:2608.21381 | `benchmark/PersonaMem-v3_2026.pdf` | PDF 不完整（正文已从 HTML 版读全，图表待补） | `notes/papers/03_personamem_v3.md` |
| benchmark | τ²-bench | 双端控制的工具调用基准（Dec-POMDP，114 题电信域） | arXiv:2506.07982 | `benchmark/tau2-bench_2025.pdf` | 已给材料 | `notes/papers/02_tau2_bench.md` |
| agent | Reflexion | 言语化反思与情节记忆（NeurIPS 2023） | arXiv:2303.11366 | `agent/Reflexion_2023.pdf` | 已给材料 | `notes/papers/04_reflexion.md` |
| memory | Mem0 | 抽取—更新两段式事实记忆 | arXiv:2504.19413 | `memory/Mem0_2025.pdf` | 已给材料 | `notes/papers/01_mem0.md` |
| memory | MemoryOS / MemOS / MemoryBank / MIRIX | 分页调度 / 资源治理 / 遗忘曲线 / 多智能体分库 | 见 `notes/memory_summary.md` §9 | — | 已产出笔记 | `notes/memory_summary.md` |

## 维护规则

1. 用户给材料 → 先落 `inbox/`，按命名约定改名，再在清单登记一行。
2. 归类时移动到对应目录，同时更新"材料"列路径。
3. 能读到原文才填参数与数字；拿不到原文的字段留空并标 `待补`，不用二手信息回填。

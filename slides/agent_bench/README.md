# “联接”Agent 意图理解、多轮交互与认知记忆评测体系深度调研报告

本目录归档了围绕**“联接”Agent（面向通信网络质量保障场景的多轮多意图理解、主动澄清与三层认知记忆协同系统）**的评测基准（Benchmark）与评测方法论深度调研报告。

## 核心交付件

- **交互式 Web 深度调研报告（支持 `暖阳米纸 #FBF7F0` / `GitHub 简洁 #F6F8FA` 双浅色主题切换、`长卷通览 / 分章聚焦` 视图切换、左侧实时过滤目录树、KaTeX 公式符号释义与防溢出自适应架构图）**：[index.html](./index.html)

---

## 报告四层推演逻辑结构概览

1. **第 1 章：评测对象界定与五维正交分类体系构建（评什么 & 怎么分类）**
   - `1.1` 为什么必须建立统一的评测分类坐标系？当前领域的五大碎片化痛点 vs. 目标机制双栏对比
   - `1.2` 五维正交分类坐标系（5D Orthogonal Taxonomy：任务认知子域 $D_1 \times$ 交互耦合形态 $D_2 \times$ 环境状态闭环 $D_3 \times$ 观测截面粒度 $D_4 \times$ 真值与评分机制 $D_5$）
   - `1.3` 五大维度下 23 个细分类别的核心定义、考察重点与数学化评判标准（Turn-JGA、证据接地率 $\text{EGR}_t$、$\text{Pass}\text{\textasciicircum}k$、算术契约自洽度 $\mathcal{V}_{\text{arith}}$）
2. **第 2 章：主流评测方案盘点与全景横向对比（目前有哪些方案）**
   - `2.1` 基于 `literature-search-arxiv` 与 `literature-search-openalex` 实证检索的五大评测簇（共 28 个代表性基准：MultiWOZ 2.4、SGD、$\tau$-bench、ToolSandbox、AppWorld-UL、CICC、ClarifyMT-Bench、Clarification $\neq$ Correction、LoCoMo-Plus、LongMemEval、EvolMem、MemUse、GroundEval、RuVerBench 等）深度盘点
   - `2.2` 18 个主流方案在“评测粒度、交互方式、环境构建、真值（GT）形态、核心计算指标、代表性 SOTA 水位”六维全景横向对比矩阵
   - `2.3` 四代评测演进脉络与三大底层技术流派（表层参考同构流派 vs. 概率生成裁判流派 vs. 状态契约与轨迹不变量流派）的设计逻辑本质差异
3. **第 3 章：现有方案的优缺点剖析与适用边界判定（各自优劣势与局限性）**
   - `3.1` 七大核心评分机制（符号精确匹配/AST、确定性规则校验、DB 终态断言、判别式小模型、LLM-as-a-Judge、Agent-as-a-Judge & GroundEval 确定性轨迹审计、专家人工评测）的优势机理与精准检出域
   - `3.2` 五大固有盲区与顶会实证失败归因（Off-Policy 温室效应与模拟器顺从泄密、早期后验坍缩 `arXiv:2609.25337` 与欠澄清偏置 `arXiv:2512.21120`、LLM 裁判的证据路径失明 `arXiv:2606.22737`、记忆 Direct QA 与自然融合的 71pt 鸿沟 `arXiv:2608.24189`、单次 $\text{Pass}@1$ 方差掩盖）
   - `3.3` 六类代表性方案的能力边界、最佳适用阶段与严格失效条件（Failure Conditions）判定表
4. **第 4 章：面向“联接”Agent 业务场景的选型指南与分级落地架构（结合场景怎么用）**
   - `4.1` “联接”Agent 业务特征与通用开源方案直接套用的六大 Gap 双栏对照
   - `4.2` “复用（Reuse）· 改造（Adapt）· 自建（Build）”三层选型取舍与裁剪组合矩阵
   - `4.3` 跨三仓四级门禁评测落地架构（`Gate L0` 合成数据自洽门禁 $\rightarrow$ `Gate L1` 三层记忆检索与同行槽位投影白盒审计 $\rightarrow$ `Gate L2` Python 状态沙箱与树状快/慢双路径评测 $\rightarrow$ `Gate L3` 慢路径经验沉淀回写与 $\text{Pass}\text{\textasciicircum}k$ 回归）
   - `4.4` **端到端全链路真实评测样本举例（`sess_cog_u018_04`）**：并排展示真实记忆库快照、多轮复合/否定输入、中间向量命中记录与同行结构化槽位列读取、二阶段关联表补全 SQL、沙箱代码产出及四级门禁逐项对账表
   - `4.5` 横跨 `cross_memory_data`、`memory_system` 与 `qwen_intent_rag` 三个代码仓的函数级工程落地路线图
5. **附录与文献**：标准工程术语规范对照表与 40 篇实证检索学术文献完整可点击 URL 索引

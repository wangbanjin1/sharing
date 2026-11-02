# 意图理解的分级处理框架：规则 · 小模型 · 大模型 深度研究报告（v3.0 专著版）

本目录归档了围绕**意图理解（Intent Understanding / SLU / OOD Rejection / Multi-Turn DST / Tiered Model Cascades）**的深度学术与工业界研究专著报告。

## 核心交付件

- **出版级 PDF 深度研究专著（53 页，含两遍排版精确页码目录、原生 PDF 书签、KaTeX 数学形式化推导、72+ 原论文架构图与实验原表、106 篇实证检索文献索引）**：[intent_tiered_understanding_deep_research.pdf](./intent_tiered_understanding_deep_research.pdf)
- **交互式 Web 报告（带左侧可折叠多级大纲导航栏、全文检索过滤、暖阳米纸 `#FBF7F0` / GitHub 简洁 `#F6F8FA` 双浅色主题切换）**：[index.html](./index.html)
- **原版论文提取图表与实验表资源目录**：[assets/](./assets/)（共 77 幅从里程碑论文 PDF 原文中无损提取的架构图与实验评测对比表）

---

## 全书九章 + 双附录结构概览

- **摘要：核心判断与报告结构**
  - `0.1` 五个核心判断（意图契约的四次搬家、三大被低估的真实难度轴、级联成本比与验真器不等式、P99 尾延迟对在线升级率的硬约束、共形预测集合 + 期望风险边界）
  - `0.2` 九个关键量化锚点（标注证据等级 A/B/C 与原始论文出处）
  - `0.3` 报告结构与实证文献检索声明（`literature-search-arxiv` + `literature-search-openalex`）
- **第 1 章：问题界定、术语与评测口径**
  - `1.1` 意图的三种可操作定义（语用行为、任务槽位框架、智能体路由接口）
  - `1.2` 十个易混淆概念边界与对照表
  - `1.3` 核心数据集（ATIS / SNIPS / BANKING77 / CLINC150 / MixATIS / MixSNIPS / TOP / MultiWOZ / MIntRec 2.0）与六个主指标口径陷阱
  - `1.4` 研究方法与 A/B/C 证据分级规则
  - `1.5` 三条真实难度轴（标签基数、标签开放性、交互深度）
- **第 2 章：意图相关任务的子课题谱系**
  - `2.1` 三个正交维度的生成逻辑
  - `2.2` 十类子课题及其三代技术演进与当前 SOTA 水位
  - `2.3` 谱系背后的三条演进规律
- **第 3 章：技术演进：六个阶段与关键节点（1966—2026）**
  - `3.0` 一条主线：意图契约的四次搬家
  - `3.1` 符号规则期（1966—1989）：ELIZA / SHRDLU / GUS 与文法驱动 IVR
  - `3.2` 统计学习期（1990—2009）：DARPA ATIS / SVM / CRF / W3C SRGS & VoiceXML / HVS
  - `3.3` 深度神经网络期（2010—2017）：TextCNN / fastText / BiLSTM-CRF / Attention BiRNN（含原图与 Table 4 原表）/ Hybrid Code Networks / Rasa
  - `3.4` 预训练微调期（2018—2022）：BERT / TOP / JointBERT / Stack-Propagation / CLINC150 / AGIF / GL-GIN / ReLa-Net
  - `3.5` 大模型提示期（2020—2024）：GPT-3 / Seq2Seq-Ptr / FLAN / Gorilla / ToolLLM / IntentGPT
  - `3.6` 智能体与路由期（2023—2026）：ReAct / FrugalGPT / RouteLLM / 共形意图澄清（CIC）/ MCP & CALM
  - `3.7` 演进规律的三个定量观察
- **第 4 章：基于规则的意图处理**
  - `4.1—4.3` 六族规则算法、Aho-Corasick 自动机与热带半环 WFST 数学形式化、Action Mask 混合机制
  - `4.3.6` 工业级混合规则代表作精读：**Snips Voice Platform (`arXiv:1805.10190`)** 与 **Rasa DIET (`arXiv:2004.09936`)** 稀疏规则特征融合（含原图与消融原表）
  - `4.4—4.6` 六桶评测协议、六种结构性失效边界、**个性化表述映射 / 用户自定义表述映射层（`expression`）**
- **第 5 章：基于小模型的意图处理**
  - `5.1—5.3` 浅层基线与四代联合建模：**JointBERT (`arXiv:1902.10909`)** 与 **Stack-Propagation (`arXiv:1909.02188`)** 数学形式化与原表对比
  - `5.4` 多意图小模型：**AGIF (`arXiv:2004.10087`)** 与 **GL-GIN (`arXiv:2106.01925`)** 图消息传递方程与 $11.88\times$ 推理加速原表；**双塔句向量检索 (`BANKING77`, `arXiv:2003.04807`)**、**向量相似度检索与同行槽位提取（读取同行结构化槽位列 Row-Level Column Projection）**及**二阶段关联表补全（通过 `service_to_app` / `periodic_preference` 双向关联）**
  - `5.5—5.7` 域外拒识（MSP / Energy / 马氏距离 / **ADB 自适应球面边界 `arXiv:2012.10209`** 与 **SCL `arXiv:2106.08616`**）、意图发现 `DeepAligned` 与模型压缩 `DistilBERT / TinyBERT`
- **第 6 章：基于大模型的意图处理**
  - `6.1—6.5` 条件生成范式转移、提示工程四个杠杆、指令微调 `MIDLM`、意图发现 `IntentGPT` 与工具路由 `Gorilla / ToolLLM`
  - `6.6—6.9` 语义熵不确定性、**亚马逊工业实证精读 `Adaptive ICL + CoT` (`arXiv:2410.01627`) 与基于大模型第 $L/2$ 层表征的二阶段 OOD 检测器**、九大短板清单与 `SetFit + LLM` 混合实测（$56\times$ 时延差距）
- **第 7 章：多轮对话与多意图的交叉场景**
  - `7.1—7.5` 四象限分类、多轮状态追踪（TRADE / TripPy / SimpleTOD / **LDST `arXiv:2310.14970`** 跨轮深度曲线与原表）、多意图 30 点合取鸿沟分解、层次化 TOP
  - `7.6—7.8` **共形意图分类与受控主动澄清 (`arXiv:2403.18973`)**、智能体意图漂移定量分析、**否定子句分离与权重衰减过滤**及**参数调整规则 / 槽位修正动作（Slot Revision Rule / Adjustment Action）**
- **第 8 章：分级框架：结构、边界与任务下传**
  - `8.1—8.4` 受约束最优化数学建模、级联生效的两条必要定理（成本比不等式与验真器误升级率 $\alpha \le 3.1\%$ 推导）、四级参考架构（`L0 → L1 → L1.5 → L2`）、**FrugalGPT / HybridLLM / RouteLLM / AutoMix** 原图原表对比
  - `8.5—8.11` 分裂共形预测与灰区最小期望风险路由伪代码、任务分解与上下文打包下传协议、P99 尾延迟卷积定理与三种工程解法、7B 模型 200ms 时延物理分解与投机解码、**慢路径交互归纳与经验规则沉淀**
  - `8.12` **端到端全链路真实样本举例（End-to-End Real Sample Walkthrough）**：完整展示 JSON 输入、标准记忆状态快照 $B_{t-1}$、L0/L1/L1.5/L2 中间向量得分、同行槽位读取与二阶段关联补全 SQL、共形澄清追问及异步经验规则沉淀对账表
- **第 9 章：结论、落地路线图与开放问题**（十条核心结论、0–12 月三阶段路线图、八个开放问题）
- **附录 A & 文献 B**：106 篇实证检索论文清单、工业系统清单、中英标准工程术语对照表与完整可点击 URL 参考文献索引

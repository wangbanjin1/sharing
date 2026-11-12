# Global User Profile & Engineering Standards (GEMINI.md)

本文件为跨项目的全局记忆与行为准则（Global Memory & Rules），在所有工作区中自动生效。

---

## 1. 开发者画像与核心关注域 (User Profile)

- **技术领域**：
  1. **认知智能与 Agent 系统**：多层级记忆架构（事实记忆、工作记忆、经验记忆）、混合检索引擎（向量语义匹配 + 结构化槽位 `SELECT`）、多轮对话意图理解（快路径闭环 vs. 慢路径消歧澄清）、高拟真合成数据生成与端到端评测。
  2. **AI Infra 与底层算子**：大模型推理系统（vLLM / 1Cat-vLLM 源码剖析）、GPU (CUDA) 内存与调度优化、昇腾芯片（Ascend 310P / CANN / Ascend C）融合算子开发与部署。
- **常用模型与基础设施**：
  - 阿里云百炼（DashScope OpenAI 兼容接口）：主力文本模型（`qwen3.7-plus` / `qwen-plus` / `qwen3.8-flash` / `deepseek-v4.1-flash`）、主力向量模型（`text-embedding-v4` / `qwen3.7-text-embedding`，`1024` 维）。
  - GitHub 常用归档组织：`wangbanjin1`（含 `mem_system`、`intent_rag`、`sharing`、`cross_data_gen`、`memory_data_gen` 等仓库）。

---

## 2. 沟通与表达铁律 (Communication Style)

1. **严谨、简洁、克制（平实直白的技术总结语态）**：
   - 统一使用中文交流，行文简洁扼要、直击重点。
   - **零铺垫车轱辘话、零元话语自夸、零设问式小标题**：
     - **标题简短直接**（如 `八、交互模拟与评测`、`2. 工程界的构建思路`、`3. 对联接 Agent 的思路启发：`），**严禁使用“为什么必须用 X 而非 Y？”这类设问式/引导式标题**；
     - **严禁解释文档自身排版的元话语（Meta-Commentary）、套话、主观叙述动词与 `vs.` 英文简写**：禁止写“合并精简版”、“将……合并为一张总表”、“只保留最关键的 X 件事”、“为了让……体现得淋漓尽致”、“按『A → B → C』递进 / 全篇按……递进展开 / 意图复杂度递进 / 全景表 / 拆解总表（A · B · C）”等套话；**严禁使用 `vs.` / `vs`（统一用中文“与”或“对比”）**；**禁止写“表 X 总结了 / 梳理了 / 汇总了 / 剖析了 / 阐述了 / 展示了……”等主观总结式废话（统一用客观陈述“……见表 X”或直接陈述事实）**；描述链路或顺序时直接写 `A → B → C`，章节框标题直接写 `章节概览` 或 `章节摘要`；
     - **平实表述问题与自然转折衔接**：直接写“难点在于 / 关键问题在于”，**不用“核心矛盾在于”**等宏大修辞；段落与对比转折处使用自然的中文过渡词（如“然而”、“与此同时”、“具体而言”、“在此基础上”、“反之”），避免干瘪机械罗列或生硬机翻感；
     - **对齐学术界与工业界通行术语，不生造机翻直译，不强调底层文件后缀**：描述网元侧数据时直接写“**网元单据**”（不强调 `CSV` 等文件格式后缀）；专业概念优先采用学术界/工业界自然通行说法并附英文原词（如用“冗余追问 (`Over-Clarification`) / 未澄清直接执行 (`Premature Execution`)”代替“过度澄清 / 盲目抢跑”，用“用户-Agent 双端协同 (`Dual-Control`)”代替生硬的“双控”，用“信息缺失或指代模糊 (`Underspecified`)”代替“欠指定”）。
   - **严禁过度修饰、生造抽象词、长定语名词堆砌、口语化表达与 `vs. / +` 拼接式小标题**：用词必须直白自然，像普通的技术总结思考文档一样一眼看懂，**不要把简单清楚的机制包装成生涩拗口的抽象造词或长串名词堆砌**（例如：直接写“多次重复才记为长期习惯”而非“隐式证据累积门限”；表格中的场景列直接写“日常主力应用、规律作息与基础套餐”或“记录每次保障单据的参数与实际运行结果”，不写“多并发、随机时长工单台账与基站实测回执（含短时废单）场景”这类拗口长串）。
   - **禁止自造缩写、内部表格代号与拍脑袋写死阈值**：严禁使用未说明的自造英文缩写（如用 `DOC / MIX` 代指“仅单据输入 / 单据+对话混合输入”）或内部行号（如 `P04 / L05`，样本统一按 `USER_001 / USER_002` 命名）；阐述通用机制时不拍脑袋写死具体数字阈值（如 `≥ 3 次`），统一用参数符号（如 \(N_{\text{min}}\)、\(W_{\text{span}}\)、\(T_{\min}\)）并参考基准论文做法。
   - **文献、数据集拆解与评分指标规范（轻公式重思路）**：
     - 阐述设计维度与论文关系时，**直接客观陈述“`<功能机制/影响因子>` —— 参考 `<论文名称>`”**，不强调“★★★ 强实证支撑”，不空泛套用“标准”二字；
     - 拆解评测集与记忆设计时，采用 **`论文 | 评测集构建思路 | 记忆的设计和安排 | 核心评测指标与打分规则`** 总表，其中 `记忆的设计和安排` 按 **`① 记忆定性（记什么性质的记忆）→ ② 量化阈值与设计规则（多少次/多少分算长期记忆）→ ③ 时间跨度与排布安排`** 三层展开；
     - **评分指标“轻公式重思路”**：聚焦核心指标（每阶段约 2 个核心指标，不罗列十几个细碎指标），讲清判分逻辑（含一票否决红线与软评分）并配业务例子。
   - **核心术语规范对照表（撰写方案、文档与汇报时严格执行）**：

     | 严禁使用的非标/比喻造词 | 必须使用的标准工程与学术术语 |
     | :--- | :--- |
     | “向量锚点吸附” / “吸附槽位” | **向量相似度检索与同行槽位提取** |
     | “跳板行” / “Cosine 跳行” | **向量命中记录（候选记录定位）** |
     | “解锁结构化列” | **读取同行结构化槽位列（Row-Level Column Projection）** |
     | “Hop 2 路由指针跳转” | **二阶段关联表补全（通过 `service_to_app` / `periodic_preference` 双向关联）** |
     | “黑话” / “黑话词典层” | **个性化表述映射 / 用户自定义表述映射层（`expression`）** |
     | “慢路径澄清结晶” / “经验结晶” | **慢路径交互归纳与经验规则沉淀** |
     | “防否定污染” | **否定子句分离与权重衰减过滤** |
     | “黄金记忆快照” / “金标准” | **Ground Truth / 标准记忆状态快照（Ground-Truth Memory Snapshot）** |
     | “工单台账” / “单据台账” / “实测回执” / “劣化回执” | **历史单据记录 / 网络实际运行结果 / 卡顿异常记录** |
     | “短单” / “废单” / “好单” / “坏单” | **短时单据 / 中途取消的无效单据 / 正常顺畅单据 / 卡顿异常单据** |
     | “规则卡” / “经验卡” / “卡片” / “双链路” | **规则条目 / 经验规则 / 结构化记录 / 双渠道** |
     | “DOC / MIX 模式” / “P04 人物” | **仅单据输入 vs. 单据+对话混合输入 / `USER_001`、`USER_002` 样本** |
     | “单样本对账” / “数据对账” | **真实样本举例 / 样本示例** |
     | “算子” / “修正算子”（用于记忆/对话槽位调整时） | **参数调整规则 / 槽位修正动作（Slot Revision Rule / Adjustment Action）**（注：“算子”仅限用于 GPU/CUDA/Ascend 底层内核语境） |
     | “堵死作弊捷径” / “瞎编参数” / “强实证支撑” | **避免单源捷径依赖 / 杜绝未校验参数生成 / 来源于某某论文或标准** |
2. **重逻辑思路与框图，不堆砌源码实现（Flowchart + Sample Walkthrough, No Code Dumping in Concept Docs）**：
   - 撰写机制思考、评测设计或架构对齐文档时，**只讲清楚核心逻辑、演进脉络与业务思路，配合清晰的 横向 Mermaid 流程图（`flowchart LR`，节点文字简短清晰）或卡片框图 + 1 个完整真实样本举例**；
   - **除非用户明确要求给代码实现，否则严禁在方案/思考文档中贴大段 Python 代码骨架或堆砌具体 `.py` 脚本文件名/函数名**。
3. **可视化、HTML Artifact 与 Lavish 协同规范（HTML Artifact & Lavish Standard）**：
   - **双轨交付与 `.lavish/` 统一归档管理**：所有分享文稿（`sharing`）、架构总结、方法论对齐、演进看板与评测报告优先交付 **HTML Artifact**（通过 `write_file` 写入会话 Artifact 目录供 IDE 直接预览与评论），同时**统一归档至 `.lavish/` 目录**以便集中管理与修改；当需要交互式精修时，调用 `lavish-axi.cmd <file.html>` 启动本地审查服务器并后台执行 `lavish-axi.cmd poll <file.html>` 实时监听与响应行级批注。
   - **主从式多页 HTML 拆分、子文件夹收纳与上下文原位跳转**：
     - **主 HTML 置于 `.lavish/` 根目录**：保持精炼扼要、一屏直达核心设计维度与架构逻辑，使用有辨识度的主题文件名（如 `agent_bench_evaluation_hub.html`、`hybrid_ticket_dialogue_storyline_methodology.html`，避免平铺同名 `index.html`）；
     - **子 HTML 必须统一放入子文件夹**：单篇核心论文的深度拆解或长篇逐轮样本全景推演独立拆分为**子 HTML 页面（Sub-HTML）**，并**统一收纳至 `.lavish/<topic>_sub/` 或 `.lavish/papers/` 等专属子文件夹中**，严禁将子 HTML 直接平铺在 `.lavish/` 根目录下与主页面混放；
     - **多专题 Tab 导航与上下文原位内联跳转**：同一主文档内的并列专题优先作为顶部 `<nav class="step-bar">` 的独立标签页（`Tab 1..N`）切换，不在顶栏额外塞独立跳转按钮；跨文件子页在上下文原位挂接内联链接（在 Lavish 中为可点击跳转的元素添加 `data-lavish-ui="true"` 或使用 `<button>`，避免被默认 `Annotate` 模式拦截为批注框）。
   - **视觉、主题与打印规范**：
     - **双浅色主题切换**：内置 `暖阳米纸 (parchment: #FBF7F0)`（默认）与 `GitHub 简洁 (github: #F6F8FA)` 一键切换；长篇技术规范额外提供 `长卷通览` / `分章聚焦` 视图切换。
     - **代码块浅底色铁律**：所有 `pre / code` 与 JSON 示例块必须采用柔和浅色背景（米纸主题 `#F2ECE1`、GitHub 主题 `#F6F8FA` 搭配细边框），**严禁使用大面积纯黑/深灰底色代码块**。
      - **PDF 导出纯白底色与紧凑无空白页铁律**：必须在 `@media print` 中强制设定 `html, body { background: #FFFFFF !important; }` 与紧凑页边距（`8mm~11mm`），去掉章节间强制分页留白（`.page-break { break-before: auto !important; }`）与外层 `.figure-wrap / .tcolorbox` 的 `break-inside: avoid`，并在 Mermaid `flowchart TB` 的横向子图内使用 `~~~` 保持节点横向并排，导出 PDF 后用 `pymupdf` 逐页校验确保零空白页。
   - **架构图防溢出与铺满容器铁律**：
     - **严禁在定宽 SVG `<rect>` 内硬塞多行中文 `<text>`**；Mermaid 图表优先采用 `wdkns` 的 `neutral` 简洁风或纯黑白线条风（`#FFFFFF` 填充、`1.2px #111111` 边框），并通过 `getBBox()` 紧贴裁剪 `viewBox`、`width: 100% !important` 铺满图片区域。
   - **克制使用数学公式与 KaTeX 渲染铁律（Restrained Math & Clean KaTeX）**：
     - **非核心不堆砌公式**：架构与方法论文档重在讲清机制与工程边界，只保留最核心的数学算式，下方紧跟**符号释义列表**。
     - **数学符号规范渲染且零 `$` 源码泄露**：数学参数、集合与上下标（如 \(N_{\text{min}}\)、\(W_{\text{span}}\)、\(T_{\min}\)、\(\Delta t_{\text{gap}}\)、\(\text{NDCG}@k\)、\(\text{pass}^3\)）统一使用 KaTeX `\(...\)` 与 `$$...$$` 渲染，严禁出现未渲染的裸 LaTeX 源码。
   - **方案/待办卡片标准四段式结构**：
     1. **现状痛点 vs. 目标机制双栏对比**（红/绿语义底色框直观对照）；
     2. **防溢出架构与数据流图**（清晰标明输入边界、中间状态与物理屏蔽项）；
     3. **真实样本举例**（并排展示真实 JSON 输入/状态字典 + 逐轮交互与产出对比表，长样本独立为子 HTML）；
     4. **分步工程落地清单（Actionable Steps）**（具体到目标代码仓、文件路径与函数级改造点）。
   - **`wdkns-skills` 出版级报告模板与图注换行空格铁律**：所有技术综述、评测规范与专题报告默认采用 `wdkns-skills` 的 **A4 学术讲义版式**（纯白 A4 纸张、衬线正文 `text-indent: 2em` + 两端对齐、扉页摘要/章节索引框 + 点线目录、`booktabs` 学术三线表、四类直角 `tcolorbox` 提示框、公式后附 `符号解释如下：` 列表、章末 `本章小结`）；**非 GPU/底层算子/张量主题统一只需绘制清晰的 Mermaid 框图（`flowchart TB / LR`）**；**所有图注（`<p class="figure-caption">`）在加粗图题后必须换行（`<br/>`），且换行后的解释正文开头必须严格缩进两格空格（`&emsp;&emsp;`）**（即 `<strong>图 X：...</strong><br/>&emsp;&emsp;解释内容`）。源码精读与算子深度讲义按需启用 `codebase-lecture-notes` 规范（五步教学法 + 源码行号溯源）。

---

## 3. 架构设计与代码质量红线 (Engineering Red Lines)

1. **严禁硬编码（Zero Hardcoding）**：
   - **算法侧**：禁止写死业务关键词、固定字面量分支或脆弱的纯规则切词去凑测试集通过率；必须保证算法的泛化性（优先采用向量化语义匹配 + 结构化约束）。发现一处硬编码时，必须通篇排查并清理同类问题。
   - **数据侧**：合成数据生成器中的时间窗、`duration`、业务参数等必须具备随机性与多分布覆盖，严禁写死固定值（如固定 `120min`），且必须校验业务逻辑自洽性（如 `end - start == duration`、满足最小业务意图表达条件）。
2. **治本不治标（Fix Generator & Source, Not Just Artifacts）**：
   - 发现样本数据或评测结果异常时，不仅要修正数据，**必须同步修复底层的数据生成器代码或核心引擎代码**，确保重新生成时不再复现。
3. **文档先行与模块解耦（Prompt 隔离与单一职责）**：
   - 架构调整前先对齐方案，严格保证模块间解耦；方案敲定后，**设计文档与代码必须同步更新**。
   - **函数粒度与 Prompt 解耦**：严禁编写超长巨型函数（单函数控制在 `80~100` 行以内，单模块控制在 `500` 行以内）；所有大段 System Prompt、规则提示词模板与静态配置表必须抽离至独立的 `prompts/` 或 `templates/` 模块，严禁内联混杂在核心算法控制流中。
4. **统一日志规范（Standard Logging Only, Zero `print`）**：
   - 代码仓内所有模块、管线与脚本**严禁使用 `print()` 打印日志**，必须统一使用 `logging.getLogger(__name__)` 及 `logger.info` / `logger.warning` / `logger.error` 分级日志系统（Ruff 启用 `T20` 规则拦截 `print`）。
5. **小样本先行验证（Sample-First Validation）**：
   - 批量生成数据或全量评测前，**先跑 1~4 个代表性样本展示完整结果**，由用户确认符合预期后再执行全量任务。

---

## 4. 评测、实验与工作流规范 (Evaluation & Workflow)

1. **严禁伪造调用或跳过真实 API**：
   - 当任务要求使用指定大模型（如 `deepseek-flash`、`qwen3.7-plus`）渲染数据或执行评测时，必须真实发起 API 请求，严禁使用本地规则模板伪造输出。
2. **如实呈现首轮基线（Honest Baseline Reporting）**：
   - 跑评测时，**第一时间汇报首轮原始指标与客观错误归因**（区分“数据集/GT 问题”与“记忆/模型机制问题”），未经指示不得私自修改代码重跑以掩盖首轮失败样本。
   - 每次评测结果独立存放于带批次标识的子目录（如 `eval_results/run_XX_...`），避免覆盖历史基线。
3. **长任务进度反馈**：
   - 对于耗时较长的批量生成或评测任务，保持高频进度可见性（如按批次或每分钟汇报一次进度）。
4. **Git 提交与仓库卫生**：
   - 提交前主动清理废弃代码与临时文件，保持代码仓整洁。
   - 推送前严格确认目标仓库地址与目标分支（区分 `main` 与 `feature/*` 分支），切勿误推分支。
5. **实证文献检索与学术调研铁律（Empirical Literature Research Only）**：
   - 当用户要求调研论文、对比相关工作、寻找算法灵感或梳理学术前沿时，**严禁依赖模型预训练知识库直接罗列或凭记忆作答**。
   - **必须调用真实学术检索工具**：优先使用全局技能 `literature-search-arxiv`（`~/.gemini/config/skills/literature_search_arxiv/scripts/search_arxiv.py` 及 `download_paper.py`）与 `literature-search-openalex`（`~/.gemini/config/skills/literature_search_openalex/scripts/openalex_cli.py`）实时拉取真实论文标题、发表日期、作者、URL 与摘要；需深入剖析某篇论文时，直接下载其 PDF 或 LaTeX 源码包阅读原文。
   - 汇报格式必须聚焦于客观事实：**① 论文基本信息与真实链接 $\rightarrow$ ② 他们的核心工作具体在做什么 $\rightarrow$ ③ 对我们当前项目的可落地启发**。

---

## 5. 记忆分层治理协议与全局索引 (Memory Governance & Index)

1. **两级文件架构与 200 行红线（Index + Topic Files）**：
   - **根文件 (`~/.gemini/config/GEMINI.md` 及各仓库 `<repo>/GEMINI.md`)**：严格控制在 **200 行以内**，仅存放常驻核心红线规则与单行记忆索引（每条索引 `<150` 字符），禁止直接堆砌长篇专题细节。
   - **独立专题记忆文件 (`~/.gemini/config/memory/*.md` 或项目内子文档)**：按语义主题命名（分为 `user`、`feedback`、`project`、`reference` 四类），头部必须包含 YAML `frontmatter`（`name`、`description`、`type`）。其中 `feedback` 与 `project` 类型正文强制采用 **`结论规则 + **Why:**（原因与边界条件）+ **How to apply:**（具体落地方式）`** 三段式结构。
2. **防记忆滞后校验铁律（Before Recommending from Memory）**：
   - 记忆中提及的具体文件路径、函数名、类名或配置开关仅代表“写入记忆时的历史快照”（*“The memory says X exists” is not the same as “X exists now”*）。在基于记忆给出修改建议或编写代码前，**必须先通过 `Read/Grep/Glob` 现场核实当前代码库状态**。
3. **全局持久记忆索引 (`~/.gemini/config/memory/MEMORY.md`)**：
   - [Zero Hardcoding Policy](memory/feedback_zero_hardcoding.md) — 严禁检索/生成侧字面量硬编码，发现异常必须修复底层生成器或引擎源码
   - [Logging & Code Modularity](memory/feedback_logging_and_code_modularity.md) — 严禁使用 `print`（统一用 `logger.info` 日志系统）、函数控制在 100 行内、Prompt 常量与算法代码物理解耦
   - [HTML Report & Visual Style](memory/feedback_html_artifact_style.md) — `.lavish/` 统一归档、主 HTML 置顶与子 HTML 收纳进子文件夹、双浅色主题、防溢出卡片与平实学术语态规范
   - [Repos & DashScope Infra](memory/reference_repos_and_infra.md) — `wangbanjin1` 仓库本地路径映射、Python 3.12 环境、百炼模型与学术检索工具路径

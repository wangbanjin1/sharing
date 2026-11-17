# 08 · MemOS (`arXiv:2507.03724`, MemTensor & 上海交大等, 2025.07/11) — 精读与源码对账

- **作者与出处**：Zhiyu Li, Shichao Song, Chanyu Wang 等 (MemTensor 记忆张量 / 上海交大 / 浙大 / 中科大 / 人大). *MemOS: A Memory OS for AI System*. `arXiv:2507.03724v4` (2025-07 首发, 2025-11 v4 更新).
- **本地归档**：
  - 论文与 LaTeX 源码：[MemOS_2025.pdf](file:///D:/coding/sharing/papers/memory/MemOS_2025.pdf) ｜ [2507.03724.md](file:///D:/coding/sharing/papers/memory/2507.03724/2507.03724.md) ｜ `D:\coding\sharing\papers\memory\2507.03724\source\`
  - 官方仓库：`D:\coding\sharing\papers\repos\MemOS\`（`https://github.com/MemTensor/MemOS`）
- **矩阵定位（系统级高并发治理与推理加速底座）**：*注：注意与前面 90 维画像的 `MemoryOS` 区分。* 本篇剥去“操作系统（OS）”包装概念后，实质是解决外部记忆框架**“每次拼长文本重算 Prefill 太慢”**与**“同步调 LLM 写图库在 40+ QPS 下超时崩溃”**两大工业级系统瓶颈；支撑联接 Agent 的**异步削峰写库、偏好独立分槽与 `MERGED_TO` 血缘溯源设计**。

---

## 一、核心思路与三大真实工程贡献

### 1. 一句话核心思路 (Core Insight)

以 Mem0、Zep 为代表的外部记忆插件存在两个线上死穴：① **读侧重算浪费**——每轮对话都把几千字常驻背景当明文塞进 Prompt 重新 Prefill，拖慢首字延迟（TTFT）；② **写侧同步阻塞**——每次写入都要同步串行调多次 LLM 做图谱抽取与消歧，高并发下直接雪崩。

**MemOS 剥去造词外壳后的核心破局思路就三招**：

1. **常驻明文下沉为显存 KV Cache（Activation Memory）**：把短期不变的高频用户背景提前跑一次前向传播，存成 KV Cache 张量直接拼在请求前缀上，跳过重复 Prefill；
2. **Redis 异步队列读写解耦（`MemScheduler`）**：前台请求只管塞队列 200ms 秒回，把耗时的 Neo4j 树图挂载、余弦 $\ge 0.8$ 冲突检测与 `MERGED_TO` 归并全扔给后台消费者慢慢算；
3. **统一包装盒（`MemCube`）+ 偏好物理拆槽**：给每条记忆套上带来源血缘与权限生命周期的元数据头，并在底层把“用户偏好”从“通用客观事实”里单独拎出来分槽存取。
   *(注：论文大篇幅宣传的第三介质“参数记忆 Parameter Memory / 自动训 LoRA”，经源码核查仅为未实现的 `Placeholder` 空壳，阅读时可直接忽略。)*

### 2. 三大核心贡献 (Key Contributions)

1. **打通“明文记忆 $\rightarrow$ KV Cache 激活记忆”预热注入链路**：在单张 H800 上将 6K Token 背景记忆的推理首字延迟（TTFT）从 0.96s–2.04s 压降至 **0.11s–0.15s（提速 88.8%–94.2%）**。
2. **高并发异步削峰与无损血缘图谱治理**：依靠异步消息队列 + 后台图重组器（`GraphStructureReorganizer`），在 **100 QPS** 高压下保持写入均值 **251.9 ms / 100% 成功率**（同场压测下 Mem0 与 Zep 在 40–100 QPS 大面积超时崩溃）；冲突消解时保留旧节点并挂接 `MERGED_TO` 血缘边，支持历史状态回滚。
3. **偏好物理隔离驱动四大记忆榜单领先**：源码将 `PreferenceTextMemory` 独立拆槽配合三阶段渐进深搜（`AdvancedSearcher`），在 LoCoMo（Judge **75.80**）、LongMemEval（Acc **77.8%**，偏好单项 **96.7%**）、PreFEval 与 PersonaMem 上全面跑赢 Mem0、Zep、Memobase 等 6 种主流框架。

---

## 二、核心系统机制拆解（去概念化·源码真实管线）

```text
[前台在线请求链路]
  ├── 写入 (Add): 原始对话/文档 ──► MemReader 提取时间窗与结构 ──► 投递 Redis/内部异步队列 (200ms 秒回)
  └── 检索与推理 (Search & Chat):
        ├── 动态碎片事实/偏好 ──► 查 TreeTextMemory (Neo4j) + PreferenceTextMemory ──► 最多 3 轮渐进深搜
        └── 高频稳定背景记忆  ──► 直接挂载预计算好的 KVCacheItem (DynamicCache / vLLM Prefix) 跳过 Prefill

[后台异步治理链路] (MemScheduler 消费者 + GraphStructureReorganizer)
  队列消费 ──► 挂载 topic -> concept -> fact 分层树图节点 (状态置为 activated)
           ──► 同作用域向量检索 Top-5 且 Cosine >= 0.80 的相似老节点 (NodeHandler.detect)
           ──► LLM 判定关系 (independent / redundant / contradictory):
                 ├── 独立: 直接保留双节点
                 ├── 可调和冲突/冗余 (resolve): 生成融合新节点 merged，继承双边；
                 │     老节点置为 archived，建立 conflict_a/b --[MERGED_TO]--> merged 血缘边
                 └── 不可调和硬冲突 (_hard_update): 对比 updated_at 时间戳，留新删旧
           ──► 定时扫描高频 WorkingMemory ──► 若文本未变则复用，否则前向提取 KV Cache 落盘 (.Caches)
```

### 1. 统一封装结构 `GeneralMemCube`（`src/memos/mem_cube/general.py:28-48`）

好比标准化的“记忆集装箱”，外层是治理元数据头（记录来源签名 `user_input/knowledge_base`、权限 ACL、TTL 衰减策略、访问热度 `usage` 与修改历史链 `history`），内层在源码中实际划分为 **4 个物理槽位**：

- **`text_mem`**：通用明文记忆（对接向量库或 Neo4j 分层树图 `TreeTextMemory`）；
- **`pref_mem`**：**源码专门独立拆出的用户偏好槽位**（`PreferenceTextMemory`），用专用抽取与召回策略隔离个人喜好与客观事实；
- **`act_mem`**：激活态 KV 缓存（`KVCacheMemory` / `VLLMKVCacheMemory`），支持一键 `dump()` 导出二进制缓存跨机挂载；
- **`para_mem`**：参数态 LoRA 接口桩（当前源码为空壳占位）。

*(注：论文里罗列的 `MemVault`、`MemGovernance`、`MemLoader` 等十余个 OS 映射名词，工程本质就是常规的数据库 Adapter 抽象层、三元权限配置类 `AuthConfig` 与目录序列化函数 `init_from_dir / dump`。)*

### 2. 图谱冲突归并与三阶段深搜（`tree_text_memory/`）

- **带血缘链的软归并（`organize/handler.py:22-212`）**：不同于 Mem0 直接覆写抹除旧文本，MemOS 在余弦阈值 `>= 0.8` 触发 LLM 融合后，把被替代的旧节点转为 `archived` 冷态移出热检索池，并用 `MERGED_TO` 有向边指向新节点——既避免新旧矛盾事实同时塞进上下文，又保留了完整的审计回滚链（Time Machine）。
- **三轮渐进式深搜（`retrieve/advanced_searcher.py:53-364`）**：针对复杂跨期问题，在基础“向量 + BM25 + Reranker”快搜之上提供最多 `thinking_stages = 3` 轮迭代检索——每轮由 LLM 评估当前捞出的节点够不够答题（`can_answer`），不够则自动补充新查询词往图谱深层跳，最后重整为紧凑摘要。

### 3. KV Cache 激活记忆的预热与失效边界（`activation_memory_manager.py:31-186`）

后台定时把用户近期高频访问的 `WorkingMemory` 条目按固定编号模板拼成一段长文本：

- 先做字符串比对：若与上次缓存的文本完全一致则直接跳过，零算力消耗；
- 若发生变化：执行一次模型前向计算抽出各层 $(K, V)$ 张量落盘；但受限于自回归因果注意力掩码（Causal Mask）的位置强依赖，**只要其中任意一条记忆更新或顺序变动，整块拼接的 KV Cache 就必须全量作废重算（`act_mem.delete_all()`）**。

---

## 三、实验账本对账：准确率、100 QPS 压测与 TTFT 加速

全量实验统一采用 **`GPT-4o-mini`** 作为生成与裁判底座，横向对比 6 个主流开源/商业记忆框架。

### 1. 四大权威记忆基准主实验 (`Tables 3–6`)

- **LoCoMo 长对话评测（`Table 3`）**与 **LongMemEval 跨会话评测（`Table 4`）**：

| 记忆框架        | LoCoMo: Single / Multi / Temp / Open (Judge ↑) | LoCoMo 总分 / F1 / Tokens | LongMemEval: Pref / Temp / Multi / Update (Acc% ↑) | LongMemEval 总分      |
|:--------------- |:----------------------------------------------:|:-------------------------:|:--------------------------------------------------:|:---------------------:|
| **Mem0**        | 73.3 / 58.8 / 52.3 / 45.8                      | 64.57 / 43.46 / 1,172     | 90.0 / 72.2 / 63.2 / 66.7                          | 66.4% (~1.1k tok)     |
| **Zep**         | 66.2 / 52.1 / 54.8 / 33.3                      | 59.22 / 41.23 / 2,701     | 53.3 / 54.1 / 47.4 / 74.4                          | 63.8% (~1.6k tok)     |
| **Memobase**    | 73.1 / 64.7 / **81.2** / 53.1                  | 72.01 / **50.18** / 2,102 | 80.1 / 75.9 / 66.9 / **89.7**                      | 72.4% (~1.5k tok)     |
| **MIRIX**       | 68.2 / 54.3 / 68.5 / 46.9                      | 64.33 / 28.10 / —         | 53.3 / 25.6 / 30.1 / 52.6                          | 43.5% (—)             |
| **Supermemory** | 67.3 / 51.1 / 31.8 / 42.7                      | 55.34 / 34.87 / 500       | 89.9 / 44.4 / 52.6 / 55.1                          | 58.4% (~0.4k tok)     |
| **MemU**        | 66.3 / 63.1 / 27.1 / 50.0                      | 56.55 / 35.15 / 617       | 76.7 / 17.3 / 42.1 / 41.0                          | 38.4% (~0.5k tok)     |
| **MemOS-1031**  | **81.1 / 67.5** / 75.2 / **55.9**              | **75.80** / 45.27 / 1,589 | **96.7 / 77.4 / 70.7** / 74.3                      | **77.8%** (~1.4k tok) |

*(注：LongMemEval 其余两列 `SS-Asst / SS-User` 中，MemOS 为 `67.9% / 95.7%`，Zep 为 `75.0% / 92.9%`，Mem0 为 `26.8% / 82.9%`。)*

- **专项偏好评测 PreFEval（`Table 5`）与 PersonaMem（`Table 6`）**：
  - **PreFEval 隐式偏好遵循率**：无干扰（0 turns）下 MemOS 达 **`77.2%`**（遗忘率仅 `4.6%`），大幅甩开 Mem0（`65.9%`）与 Zep（`40.7%`）；插入 10 轮无关对话干扰后仍稳在 **`71.9%`**（Mem0 `63.7%`，MIRIX 崩至 `7.9%`）。
  - **PersonaMem 四选一准确率**：MemOS 取得 **`61.2%`**（1,424 tokens），高于 Memobase（`58.9%`）、Zep（`57.8%`）与 Mem0（`43.1%`）。

### 2. 高并发吞吐压测与 KV-Cache 加速实测 (`Tables 7–8`)

- **10 / 40 / 100 QPS 在线读写压测（`Table 7`）**：

| 并发档位    | 框架           | 写入 Add 均值 / P99 (ms)         | Add 成功率     | 检索 Search 均值 / P99 (ms)      | Search 成功率  |
|:-----------:|:-------------- |:--------------------------------:|:--------------:|:--------------------------------:|:--------------:|
| **10 QPS**  | Mem0 / Zep     | 1,385 / 6,401 ｜ 1,569 / 5,094   | 99.6% ｜ 73.9% | 1,246 / 2,870 ｜ 2,135 / 5,009   | 100% ｜ 78.3%  |
| **10 QPS**  | **MemOS-1031** | **191.9 / 318.8**                | **100%**       | **440.5 / 777.1**                | **100%**       |
| **40 QPS**  | Mem0 / Zep     | 12,146 / 28,996 ｜ 3,126 / 5,112 | 41.7% ｜ 26.6% | 10,875 / 25,689 ｜ 3,897 / 5,106 | 51.2% ｜ 26.8% |
| **40 QPS**  | **MemOS-1031** | **192.6 / 312.6**                | **100%**       | **613.8 / 934.0**                | **100%**       |
| **100 QPS** | Mem0 / Zep     | 超时崩溃 (`-`)                   | **< 15%**      | 超时崩溃 (`-`)                   | **< 15%**      |
| **100 QPS** | **MemOS-1031** | **251.9 / 489.6**                | **100%**       | **741.2 / 1,171.1**              | **100%**       |

- **单卡 H800 上 KV-Cache 注入首字延迟实测（`Table 8`，背景 `6,064` tok + 查询 `167` tok）**：

| 模型规格        | 一次性 KV 预热构建耗时 | 传统明文重算 Dir TTFT | MemOS 激活注入 KV TTFT | TTFT 相对加速比 |
|:--------------- |:----------------------:|:---------------------:|:----------------------:|:---------------:|
| **Qwen3-8B**    | 0.93 s                 | 2.04 s                | **0.12 s**             | **94.2%**       |
| **Qwen3-32B**   | 0.71 s                 | 0.96 s                | **0.11 s**             | **88.8%**       |
| **Qwen2.5-72B** | 1.27 s                 | 1.79 s                | **0.15 s**             | **91.4%**       |

---

## 四、论文宣传 vs. 官方仓库源码对账（脱水去魅）

精读 `repos/MemOS/src/memos/` 后，梳理出 **5 处关键的论文包装与真实代码落差**：

| 审计项                        | 论文白皮书描述                                                 | 仓库真实代码实现                                                                                                            | 工程审阅结论                                                                     |
|:----------------------------- |:-------------------------------------------------------------- |:--------------------------------------------------------------------------------------------------------------------------- |:-------------------------------------------------------------------------------- |
| **1. LoRA 参数记忆为空壳**    | 三大核心支柱之一，支持明文自动蒸馏为 LoRA 热插拔 (`Sec 4.1.3`) | `memories/parametric/lora.py:1-41` 顶部写明 `# TODO: serves as a placeholder`，`dump()` 只写死 `b"Placeholder"`             | 所谓“三态统一调度”实际只落地了**明文图谱 + KV Cache 两态**，参数内化纯属远期愿景 |
| **2. 偷偷拆出第四偏好槽**     | `MemCube` 封装 Text / Act / Para 三类载荷 (`Fig. 5`)           | `mem_cube/general.py:28-48` 实际定义了 **4 个槽**：额外拆出独立的 `self.pref_mem` (`PreferenceTextMemory`)                  | **真正的刷榜功臣**：把用户偏好与客观事实物理隔离抽取，直接撑起了偏好榜单的高分   |
| **3. 状态机靠图边实现**       | 画了 6 态流转图（含 `Generated / Merged / Frozen`，`Fig. 7`）  | `textual/item.py:124` 实际只有 4 个枚举：`activated / resolving / archived / deleted`（外加 `MERGED_TO` 边）                | 用并发锁状态 `resolving` + 图数据库有向边替代了繁琐的状态枚举                    |
| **4. 扩展了 10 种业务子类型** | 正文仅按作用域分私有/共享/全局                                 | `item.py:113-123` 细化出 `ToolSchemaMemory`、`ToolTrajectoryMemory`、`SkillMemory` 等 10 类，并新增 `dream/` 巩固目录       | 代码库在工具轨迹与技能沉淀上的工程划分比论文正文更实用                           |
| **5. 批量导入跳过工作记忆**   | 新记忆先入工作记忆再异步归并 (`Sec 5.2`)                       | `organize/manager.py:239` 留有 `# TODO: working id is same with item.id`，导致 `_add_memories_batch` 跳过了 `WorkingMemory` | 批量灌库压测时存在 ID 冲突未修 Bug，直接走了长期库写入通道                       |

---

## 五、架构短板与向联接 Agent（主报告）的落地映射

### 1. 不宜照搬的两处原生短板

- **整块 KV Cache 牵一发动全身**：多条记忆拼成单块 `DynamicCache` 后，任意单条状态微调都会因位置编码偏移导致整块缓存失效重算，仅适合**极度静态的全局人设/通用规程**，不适合高频跳变的实时网元指标。
- **后台逐对调 LLM 消歧成本高**：每进一个新节点都要拉出 Top-5 相似节点逐对调大模型判冲突，海量网元流水单据全量走这套图重组会把后台 Token 烧穿（对结构化单据应优先用确定性主键/规则合并）。

### 2. 向联接 Agent（[主报告](file:///d:/coding/sharing/.lavish/storyline_and_evaluation_merged_technical_route_report.html)）的三大直接借鉴

1. **偏好槽与事实槽物理分家（对齐 `pref_mem` 拆槽实证）**：
   MemOS 拆出 `PreferenceTextMemory` 后在 `SS-Pref` 拿到 `96.7%` 的结果，直接验证了我们主报告将**用户周期性习惯/黑话映射（`periodic_preference / expression`）**与**网元客观履历（`Fact Memory`）**分表建模、分路召回的路线完全正确。
2. **软归档 + `MERGED_TO` 版本演化链（支撑偏好漂移溯源）**：
   借鉴 `TreeNodeTextualMemoryMetadata` 的血缘字段，在每条画像/经验条目上记录 `sources`（区分来自 `ticket_record` 保障单据还是 `dialogue_turn` 会话轮次）；当用户变更套餐或作息窗口时，不物理删老记录，而是将旧记录置为 `archived` 并挂接 `MERGED_TO` 指向新节点——既杜绝在线检索新旧冲突，又为离线评测集的“跨期偏好漂移”保留完整真值链。
3. **前台轻量入队 + 后台异步归并（对齐 100 QPS 削峰架构 + vLLM Prefix Caching）**：
   线上对话与单据落库采用 MemOS 的读写解耦模式：前台仅写轻量流水并在 200ms 内返回，后台异步消费队列执行相似度 `>= 0.80` 的冲突归并与经验蒸馏；同时在推理引擎侧（vLLM）将固定不变的**系统规程 + 用户静态基础画像**排在 Prompt 最前缀，自然吃满 vLLM 原生 Prefix Caching 红利，无需手搓脆弱的 `DynamicCache` 磁盘序列化。

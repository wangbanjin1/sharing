# “联接”Agent 评测体系现状、对标与论文按需展开库（Multi-HTML 方案）

本目录归档了围绕**“联接”Agent（多轮多意图理解、快/慢路径澄清消歧与三层认知记忆协同系统）**的评测工作归类总结、本地现状盘点、可落地启发与代表性论文按需展开库。

---

## 1. 多 HTML 页面导航结构（1 主站 + 5 专题论文页）

| 页面路径 | 页面定位 | 收录核心内容 / 代表性论文 |
| :--- | :--- | :--- |
| **[index.html](./index.html)** | **🏠 总览与选型主站** | ① 业界 Agent 评测五大流派归类总结；<br/>② 我们“联接”Agent 的评测现状（三大代码仓已建底座 vs. 五大短板）；<br/>③ 外部工作对我们的启发与落地方案（含 KaTeX 指标公式与真实样本全链路举例）；<br/>④ 24+ 篇代表性论文按需抽屉展开与实时检索过滤索引。 |
| **[papers/stateful_tool_user.html](./papers/stateful_tool_user.html)** | **专题 ①：状态化工具与多轮用户交互** | `τ-bench` (`2406.12045`)、`ToolSandbox` (`2408.04682`)、`AppWorld` (`2407.18901`) & `AppWorld-UL` (`2607.20536`)、`MINT` (`2309.10691`)、`StableToolBench` (`2403.07714`)、`Gorilla / BFCL` (`2305.15334`) |
| **[papers/clarification_revision.html](./papers/clarification_revision.html)** | **专题 ②：模糊消歧、主动澄清与槽位修正** | `ClarifyMT-Bench` (`2512.21120`)、`Clarification Is Not Correction` (`2609.25337`)、`CICC` (`2403.18973`)、`ProductAgent` (`2407.00942`)、`CLAM` (`2212.07769`) |
| **[papers/cognitive_memory.html](./papers/cognitive_memory.html)** | **专题 ③：跨会话长周期认知记忆** | `LoCoMo` (`2402.17753`) & `LoCoMo-Plus` (`2602.10715`)、`LongMemEval` (`2410.10813`)、`EvolMem` (`2601.03543`)、`MemUse` (`2608.24189`)、`PersistBench` (`2602.01146`) & `AgentMemGate` (`2610.07707`) |
| **[papers/judge_and_trace_audit.html](./papers/judge_and_trace_audit.html)** | **专题 ④：评测裁判机制与轨迹证据审计** | `GroundEval` (`2606.22737`)、`RuVerBench` (`2606.29920`)、`Agent-as-a-Judge` (`2410.10934`)、`MT-Bench` (`2306.05685`) / `G-Eval` / `Prometheus` (`2310.08491`)、`LiveBench` (`2406.19314`) |
| **[papers/multi_turn_dst.html](./papers/multi_turn_dst.html)** | **专题 ⑤：多意图并发与多轮 DST 基石** | `MultiWOZ 2.4` (`2104.00773`)、`SGD` (`1909.05855`)、`AGIF / MixATIS` (`2004.10087`)、`GL-GIN` (`2106.01925`)、`CLINC150` (`1909.02027`) & `LDST` (`2310.14970`) |

---

## 2. 视觉与交互特性

- **双浅色主题一键切换**：默认 `暖阳米纸 (#FBF7F0)`，支持切换 `GitHub 简洁 (#F6F8FA)`（跨页面自动记忆主题偏好），所有代码块统一采用柔和浅底色（`#F2ECE1` / `#F6F8FA`）。
- **按需展开论文卡片**：每篇论文均按 **「① 论文基本信息与真实 arXiv 链接 → ② 他们具体在做什么 → ③ 优劣势与适用边界 → ④ 对我们联接 Agent 的可落地启发」** 四模块拆解，支持关键词即时筛选、单篇抽屉展开或一键全部展开/收起。

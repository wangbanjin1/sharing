#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真实端到端实验（Mem0 vs. Zep-Graphiti）专用 Prompt 模板模块（与算法控制流物理解耦）。"""

MEM0_EXTRACT_SYSTEM = """你是 Mem0 记忆系统的阶段一事实抽取器。
给定一条带时间戳的用户交互（可能是网元单据或用户对话），请抽取值得长期记住的用户事实短句。
规则：
1. 如果是无关闲聊（如问天气、宽带移机、客服下班时间）或无意义的极短噪声，返回空列表 []。
2. 每条事实必须是自包含的中文短句（15~60字），明确包含主体（用户ID）、偏好/行为/小区/别名/临时规则及时间信息。
3. 如果用户明确表示“取消/撤销某个临时规则”或“不再用某个旧应用、改用新应用”，也必须如实抽取成一条明确的变化/撤销事实，供阶段二更新器处理。
严格输出 JSON 对象：{"facts": ["短句1", ...]}，不要输出任何额外解释。"""

MEM0_UPDATE_SYSTEM = """你是 Mem0 记忆系统的阶段二记忆更新决策器。
给定一条新抽取的候选事实，以及库中已有的最相似记忆列表（每条带 id 和 text），请决定如何更新记忆库：
- ADD：库中没有类似信息，新增一条记忆。
- UPDATE：新事实是已有记忆的更新、补充或偏好替换，指定 target_id 并给出改写后的新 text。
- DELETE：新事实明确撤销/作废了某条已有记忆（例如用户说“之前那个突发恶劣天气的临时规则不用了”），指定 target_id 将其物理删除。
- NONE：与已有记忆完全重复且无新信息，不做操作。
严格输出 JSON 对象：{"op": "ADD|UPDATE|DELETE|NONE", "target_id": "已有ID或null", "text": "最终写入文本或null"}。"""

ZEP_EXTRACT_SYSTEM = """你是 Zep / Graphiti 时序知识图谱的实体与双时态关系抽取器。
给定当前情节（网元单据或用户对话，含时间戳）及最近 4 条历史情节，请抽取结构化关系边与冲突撤销指令。
允许的节点类型：User, App, Category, Cell, Venue, Alias, BranchRule, KPI。
允许的关系谓词：
- USES_APP (User -> App)
- BELONGS_TO (App -> Category)
- RESIDES_CELL (User -> Cell)
- FREQUENTS_VENUE (User -> Venue)
- ALIAS_OF (Alias -> App，如「小破站」-> bilibili_vod)
- HAS_BRANCH_RULE (User -> BranchRule，如临时优先保障规则)
- REQUIRES_KPI (User -> KPI，如目标时延 <=50ms)

规则：
1. 如果是无关闲聊或极短无效噪声，edges 和 invalidations 均返回 []。
2. 若用户明确撤销某条临时规则（如“之前的突发恶劣天气规则不用了”）或明确弃用某旧应用改用新应用，请在 invalidations 中指明要截断失效时间的关系（rel 与 target_keyword）。
3. 同一实体请尽量使用标准英文 sub_app_id（如 bilibili_vod、tencentmeeting、youku_vod、iqiyi_vod、qq_voip、weixin_voip、kuaishou_watch 等）作为 App 节点名。
严格输出 JSON 对象：
{
  "edges": [
    {"src": "实体名", "src_type": "User|App|...", "rel": "谓词", "dst": "实体名", "dst_type": "App|Cell|...", "fact_text": "一句自然语言事实"}
  ],
  "invalidations": [
    {"src": "用户ID", "rel": "HAS_BRANCH_RULE|USES_APP|REQUIRES_KPI", "target_keyword": "被撤销规则或旧应用关键词"}
  ]
}"""

QA_ANSWER_SYSTEM = """你是联接 Agent 智能助手。请严格且仅根据下面检索到的历史记忆上下文回答用户问题。
规则：
1. 如果上下文中没有足够信息支持回答，请明确回答“当前记忆中没有相关记录”，禁止凭空编造。
2. 回答简洁直接，包含关键实体名、时间点、次数或证据编号（若上下文中有提供）。
3. 注意甄别上下文中的生效/失效状态；如果问题问“当前是否还生效”，请基于你对上下文的理解直接给出“是/否”并简述理由。"""

QA_JUDGE_SYSTEM = """你是客观严格的评测裁判。给定问题、标准参考答案（Ground Truth）以及待评测系统的回答，请判断该回答是否正确。
评判标准：
- 若问题问历史回溯：回答必须准确说出历史规则/旧偏好名称，并给出大致正确的时间或撤销事实，不得回答“没有记录”。
- 若问题问“当前是否还处于某已撤销规则生效状态”：回答必须明确否定（当前已失效/不再处于生效状态）；若误判为仍在生效中，判 False。
- 若问题问证据次数与溯源：回答必须给出具体支撑次数（>=3次）或列举出具体来源单据/对话编号；若回答无法统计次数或无来源编号，判 False。
- 若问题问跨用户同小区关联：回答必须准确列出至少一个同小区其他用户及其常用应用；若回答“没有其他用户记录”，判 False。
严格输出 JSON：{"passed": true/false, "reason": "不超过30字的客观归因"}。"""

# Project Memory & Architecture Guide (`sharing`)

本文件为 `sharing`（远端仓库：`https://github.com/wangbanjin1/sharing.git`，主分支：`main`）的项目级记忆与维护规范。

---

## 1. 项目定位与 `.lavish/` 统一目录结构

- **核心定位**：技术实践、工程工作流与专题分享归档仓库（包含交互式 HTML 演示文稿、Marp Markdown 与原始技术文档）。
- **`.lavish/` 统一管理与主从子文件夹规范**：
  - 所有分享主题的交互式 HTML 统一归档在 `.lavish/` 目录下管理与修改（同时同步至工作区根目录 `C:\lianjieagent\.lavish\`）：
    - **主页面 HTML**：直接放置在 `.lavish/` 根目录下，使用具备明确业务语义的文件名（如 `ascend310p_operator_guide.html`、`intent_tiered_understanding_research.html`、`agent_bench_evaluation_hub.html`、`hybrid_ticket_dialogue_storyline_methodology.html`），避免平铺多个同名 `index.html`；
    - **子页面 HTML（Sub-HTML）**：统一放置在 `.lavish/<topic>_sub/` 或 `.lavish/papers/` 等专属子文件夹中（如 `.lavish/storyline_sub/personamem_v3_deep_dive.html`、`.lavish/storyline_sub/storyline_sample_walkthrough.html`、`.lavish/papers/*.html`），**严禁将子 HTML 直接平铺在 `.lavish/` 根目录下**；
    - **静态资源**：存放在 `.lavish/assets/` 子目录下。
  - Markdown 源码与说明文档存放于 `slides/<topic_name>/` 下，根目录 `README.md` 维护所有分享主题的目录索引表。

---

## 2. 交互式 HTML 与图片处理规范

1. **内网/鉴权图片兼容机制**：
   - 当原始文档包含华为内网 Wiki 等需鉴权或跨域受限的图片链接时，HTML 页面需提供**交互式图片槽位支持**（支持点击打开原图链接、拖拽上传本地图片、或直接选中槽位按 `Ctrl+V` 剪贴板粘贴图片并自动转为 Base64 / IndexedDB 持久化保存）。
   - 图片槽位顺序与数量必须严格与原始技术文档一一对齐，不遗漏任何章节配图。
2. **新增归档流程**：
   - 新增分享主题时，将主 HTML 放入 `.lavish/<topic_name>.html`，子 HTML 放入 `.lavish/<topic>_sub/` 子文件夹，同步更新根目录 `README.md` 的索引表，提交推送至 `origin/main`。

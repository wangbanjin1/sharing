# Project Memory & Architecture Guide (`sharing`)

本文件为 `D:\coding\sharing`（远端仓库：`https://github.com/wangbanjin1/sharing.git`，主分支：`main`）的项目级记忆与维护规范。

---

## 1. 项目定位与目录结构

- **核心定位**：技术实践、工程工作流与专题分享归档仓库（包含交互式 HTML 演示文稿、Marp Markdown 与原始技术文档）。
- **目录结构规范**：
  - 每个分享主题独立存放于 `slides/<topic_name>/` 子目录下（例如 `slides/ascend310p/` 存放《Ascend 310P 融合算子开发与入图全流程》）。
  - 子目录内标准构成：
    - `index.html`：自包含、高交互性的 Web Slides / 技术报告页面；
    - `slides.md`：Marp 格式 Markdown 源码；
    - `README.md`：原始技术文档与参考链接归档；
    - `assets/`（可选）：本地静态图片资源。
  - 根目录 `README.md`：维护所有分享主题的目录索引表。

---

## 2. 交互式 HTML 与图片处理规范

1. **内网/鉴权图片兼容机制**：
   - 当原始文档包含华为内网 Wiki 等需鉴权或跨域受限的图片链接时，HTML 页面需提供**交互式图片槽位支持**（支持点击打开原图链接、拖拽上传本地图片、或直接选中槽位按 `Ctrl+V` 剪贴板粘贴图片并自动转为 Base64 / IndexedDB 持久化保存）。
   - 图片槽位顺序与数量必须严格与原始技术文档一一对齐，不遗漏任何章节配图。
2. **新增归档流程**：
   - 新增分享主题时，创建 `slides/<topic>/` 目录并完成 HTML 与 Markdown 后，必须同步更新根目录 `README.md` 的索引表，提交推送至 `origin/main`。

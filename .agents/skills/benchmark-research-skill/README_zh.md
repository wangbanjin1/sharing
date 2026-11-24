# benchmark-research-skill

[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-7C3AED)](#)
[![arXiv Source First](https://img.shields.io/badge/arXiv-source--first-0EA5E9)](#)
[![Obsidian Friendly](https://img.shields.io/badge/Obsidian-Friendly-8B5CF6)](#)
[![Markdown Reports](https://img.shields.io/badge/output-Markdown-334155)](#)

[English](README.md)

`benchmark-research-skill` 是一个 Claude Code 风格的 benchmark 调研 skill。

它主要做两件事：

1. 分析单篇论文：这篇 paper 用了哪些 benchmark、dataset、metric、baseline、实验图表？
2. 调研一个方向：这个领域有哪些可用 benchmark，相关工作是怎么评测的？

设计思路很简单：

- 脚本负责取证据、整理上下文
- Claude Code 负责语义抽取
- 最终 Markdown 报告写入你配置好的 Obsidian 目录

## 它能做什么

### 模式一：单篇论文

给一个 arXiv ID 或本地 PDF，它会：

- 优先抓 arXiv source / tex
- 读取 experiment / evaluation / results 章节
- 抽取表格和 benchmark 相关片段
- 需要时补原始 figure 或 PDF 页面截图
- 让 Claude Code 写 `benchmarks.json`
- 按配置决定是否补链接
- 生成最终 Markdown 笔记

### 模式二：方向调研

给一个 topic，它会：

- 搜索相关 method / system papers
- 优先选择真正做了实验的论文
- 阅读它们的 benchmark 部分
- 沿 baseline / compared methods 扩展相关工作
- 汇总 dataset、metric、代表工作和发现路径
- 生成方向调研报告

## 仓库结构

```text
benchmark-research-skill/
  SKILL.md
  config.example.yaml
  requirements.txt
  scripts/
    config_utils.py
    fetch_context.py
    search_papers.py
    collect_links.py
    generate_report.py
```

真正面向使用的主脚本只有 4 个：

- `fetch_context.py`
- `search_papers.py`
- `collect_links.py`
- `generate_report.py`

`config_utils.py` 只是内部 helper，用来根据 config 解析路径。

## 安装

```bash
pip install -r requirements.txt
```

## 最小配置

把 `config.example.yaml` 复制为 `config.yaml`，然后设置真实的 `vault_path`。

```yaml
language: "zh"
vault_path: "E:/Your/Obsidian/Vault"

benchmark_survey:
  workspace_dir: "Benchmark_Surveys"
  papers_dir_name: "papers"
  reports_dir_name: "reports"
  survey_runs_dir_name: "surveys"
  enable_collect_links: false
```

这里最重要的是这些字段：

| 字段 | 用途 | 重要性 |
|---|---|---|
| `vault_path` | 所有输出的根目录 | 高 |
| `workspace_dir` | benchmark 工作区根目录 | 高 |
| `papers_dir_name` | 单篇论文证据目录 | 高 |
| `reports_dir_name` | 最终 Markdown 报告目录 | 高 |
| `survey_runs_dir_name` | 方向调研运行目录 | 高 |
| `enable_collect_links` | 默认是否联网补链接 | 高 |
| `language` | 输出偏好 / 未来模板行为 | 低 |

## 可选搜索偏好

这部分只对 `search_papers.py` 有帮助，主要服务于方向调研。

```yaml
research_domains:
  "your-topic":
    keywords:
      - "main phrase"
      - "synonym"
      - "related task phrase"
    arxiv_categories:
      - "cs.AI"
      - "cs.LG"

excluded_keywords:
  - "workshop"
  - "survey"
  - "review"
```

如果你平时主要跑单篇分析，这部分几乎不重要。


### 单篇保存路径

如果分析 `2503.10522`，上面的 config 会把文件落到：

```text
Path/to/Your/Obsidian/Vault/
  Benchmark_Surveys/
    papers/
      2503.10522/
        context.json
        benchmarks.json
        links.json
        assets/
    reports/
      2503.10522.md
```

### 方向调研保存路径

如果 topic 是 `text-to-audio`，则会落到：

```text
Path/to/Your/Obsidian/Vault/
  Benchmark_Surveys/
    surveys/
      YYYY-MM-DD-text-to-audio/
        papers.json
        links.json
        reports/
          benchmark-survey.md
```

## 平时怎么用

正常情况下，你直接把它当 Claude Code skill 来用。

### 单篇论文

直接对 Claude Code 说：

```text
Use benchmark-research-skill to analyze what benchmarks this paper uses: 2503.10522
```

或者：

```text
Use benchmark-research-skill to read this PDF and tell me the datasets, metrics, baselines, and experiment figures.
```

### 方向调研

直接对 Claude Code 说：

```text
Use benchmark-research-skill to survey benchmarks for text-to-audio generation.
```

或者：

```text
Use benchmark-research-skill to find what benchmarks this direction uses, follow related work up to two layers, and produce a Markdown report.
```

## 输出长什么样

### 单篇报告

```markdown
# Benchmark Analysis: [Paper Title]

## Conclusion

## Benchmark Table
| Dataset | Link | Evaluated Ability | Metrics | Compared Methods | Evidence |
|---|---|---|---|---|---|

## Datasets And Metrics

## Related Work / Baselines
```

### 方向调研报告

```markdown
# Benchmark Survey: [Direction]

## TL;DR

## Basic Metrics

## Benchmark Overview
| Dataset | Link | Suitable Task | Common Metrics | Representative Work |
|---|---|---|---|---|

## Representative Works

## Grouped By Benchmark

## Experiment Figures/Tables

## Related Work Discovery Path
```

## 备注

- 单篇模式默认应该尽量快。
- `collect_links` 是可选的，因为它可能慢，而且容易被限流。
- 表格是最重要的证据来源。
- 这个 skill 追求的是可审计：证据和报告放在一起，方便回看。

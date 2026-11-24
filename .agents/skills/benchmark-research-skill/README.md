# benchmark-research-skill

[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-7C3AED)](#)
[![arXiv Source First](https://img.shields.io/badge/arXiv-source--first-0EA5E9)](#)
[![Obsidian Friendly](https://img.shields.io/badge/Obsidian-Friendly-8B5CF6)](#)
[![Markdown Reports](https://img.shields.io/badge/output-Markdown-334155)](#)

[中文版](README_zh.md)

`benchmark-research-skill` is a Claude Code style skill for benchmark research.

It is built for two jobs:

1. Analyze one paper and answer: what benchmarks, datasets, metrics, baselines, and experiment evidence does it use?
2. Survey a direction and answer: what benchmarks are practical for evaluating work in this area?

The design is deliberately simple:

- scripts fetch and organize evidence
- Claude Code does the semantic extraction
- reports are written into your configured Obsidian workspace

## What It Does

### Mode 1: Single Paper

Given an arXiv ID or PDF, the skill will:

- fetch arXiv source / tex first
- read experiment, evaluation, and result sections
- extract tables and benchmark-facing snippets
- optionally recover source figures or render PDF pages
- let Claude Code write `benchmarks.json`
- optionally collect missing links
- generate a Markdown note

### Mode 2: Direction Survey

Given a topic, the skill will:

- search related method/system papers
- prefer papers with real experiments, not just titles containing "benchmark"
- read their benchmark sections
- expand through compared methods and baseline relations
- aggregate datasets, metrics, representative works, and discovery paths
- generate a survey report


## Repository Layout

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

Only four scripts are part of the public workflow:

- `fetch_context.py`
- `search_papers.py`
- `collect_links.py`
- `generate_report.py`

`config_utils.py` is only an internal helper for config-based path resolution.

## Install

```bash
pip install -r requirements.txt
```

## Minimal Config

Copy `config.example.yaml` to `config.yaml`, then set a real `vault_path`.

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

These are the fields that matter most:

| Field | Used For | Important? |
|---|---|---|
| `vault_path` | root save location | yes |
| `workspace_dir` | benchmark workspace root | yes |
| `papers_dir_name` | single-paper evidence folder | yes |
| `reports_dir_name` | final Markdown reports | yes |
| `survey_runs_dir_name` | topic survey runs | yes |
| `enable_collect_links` | whether to run network link search by default | yes |
| `language` | output preference / future template behavior | optional |

## Optional Search Tuning

These are only used by `search_papers.py`, mostly for direction survey mode.

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

If you mostly use single-paper analysis, this section is not important.

### Single-paper save layout

For paper `2503.10522`, the config above resolves to:

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

### Survey save layout

For topic `text-to-audio`, the config above resolves to:

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

## Typical Usage

You normally use this as a Claude Code skill in natural language.

### Single Paper

Ask Claude Code:

```text
Use benchmark-research-skill to analyze what benchmarks this paper uses: 2503.10522
```

Or:

```text
Use benchmark-research-skill to read this PDF and tell me the datasets, metrics, baselines, and experiment figures.
```

### Direction Survey

Ask Claude Code:

```text
Use benchmark-research-skill to survey benchmarks for text-to-audio generation.
```

Or:

```text
Use benchmark-research-skill to find what benchmarks this direction uses, follow related work up to two layers, and produce a Markdown report.
```
## Output Shape

### Single-paper report

```markdown
# Benchmark Analysis: [Paper Title]

## Conclusion

## Benchmark Table
| Dataset | Link | Evaluated Ability | Metrics | Compared Methods | Evidence |
|---|---|---|---|---|---|

## Datasets And Metrics

## Related Work / Baselines
```

### Survey report

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

## Notes

- Single-paper mode should stay fast by default.
- Link collection is optional because it can be slow and rate-limited.
- Tables are primary evidence.
- The skill is meant to be auditable: evidence stays next to the note.

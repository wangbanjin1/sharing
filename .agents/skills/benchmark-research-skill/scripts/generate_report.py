#!/usr/bin/env python3
"""Generate Markdown reports from benchmark extraction JSON.

This script is intentionally boring: Claude Code does the semantic extraction;
the script just turns already-extracted facts into a readable note.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from config_utils import ConfigError, build_single_report_path, build_survey_report_path, load_runtime_config


def read_text_loose(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)


def load_json(path: Path) -> Any | None:
    if not path.exists():
        print(f"Skipping missing input: {path}", file=sys.stderr)
        return None
    try:
        return json.loads(read_text_loose(path))
    except json.JSONDecodeError as exc:
        print(f"Skipping invalid JSON {path} at line {exc.lineno}, column {exc.colno}: {exc.msg}", file=sys.stderr)
        return None


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def metric_name(metric: Any) -> str:
    if isinstance(metric, dict):
        return str(metric.get("name", "")).strip()
    return str(metric).strip()


def metric_label(metric: Any) -> str:
    name = metric_name(metric)
    if not name:
        return ""
    if isinstance(metric, dict):
        direction = metric.get("direction", "unknown")
        if direction == "lower_is_better":
            return f"{name}↓"
        if direction == "higher_is_better":
            return f"{name}↑"
    return name


def method_name(method: Any) -> str:
    if isinstance(method, dict):
        return str(method.get("name", "")).strip()
    return str(method).strip()


def paper_title(paper: dict[str, Any]) -> str:
    return str(paper.get("title") or paper.get("id") or "Unknown Paper").strip()


def first_link(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    if item.get("url"):
        return str(item["url"])
    for candidate in item.get("candidates", []) or []:
        if isinstance(candidate, dict) and candidate.get("url"):
            return str(candidate["url"])
    return ""


def convert_old_extract_schema(data: dict[str, Any]) -> dict[str, Any]:
    paper = data.get("paper", {})
    old = data.get("benchmarks") or {}
    benchmarks = []
    for dataset in old.get("datasets", []) or []:
        if isinstance(dataset, dict):
            name = dataset.get("name") or dataset.get("dataset")
            metrics = dataset.get("metrics", old.get("metrics", []))
            description = dataset.get("description", "")
        else:
            name = str(dataset)
            metrics = old.get("metrics", [])
            description = ""
        if name:
            benchmarks.append(
                {
                    "dataset": name,
                    "task": description,
                    "metrics": [{"name": metric_name(m), "direction": "unknown", "meaning": ""} for m in metrics],
                    "compared_methods": old.get("compared_methods", []),
                    "evidence": "",
                    "assets": [],
                    "notes": "",
                }
            )
    return {"paper": paper, "benchmarks": benchmarks, "eval_scripts": [], "related_work_edges": []}


def load_inputs(input_files: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    papers: list[dict[str, Any]] = []
    benchmark_docs: list[dict[str, Any]] = []
    links: dict[str, Any] = {"datasets": {}, "metrics": {}, "eval_scripts": {}}

    for file in input_files:
        data = load_json(Path(file))
        if data is None:
            continue
        if isinstance(data, dict) and isinstance(data.get("papers"), list):
            papers.extend(x for x in data["papers"] if isinstance(x, dict))
        elif isinstance(data, dict) and "benchmarks" not in data and any(k in data for k in ["datasets", "metrics", "eval_scripts"]):
            for key in ["datasets", "metrics", "eval_scripts"]:
                if isinstance(data.get(key), dict):
                    links.setdefault(key, {}).update(data[key])
        elif isinstance(data, dict) and isinstance(data.get("benchmarks"), list):
            benchmark_docs.append(data)
        elif isinstance(data, dict) and isinstance(data.get("paper"), dict) and isinstance(data.get("benchmarks"), dict):
            benchmark_docs.append(convert_old_extract_schema(data))
        elif isinstance(data, list):
            benchmark_docs.extend(x for x in data if isinstance(x, dict))
    return papers, benchmark_docs, links


def dataset_link(dataset: str, benchmark: dict[str, Any], links: dict[str, Any]) -> str:
    explicit = benchmark.get("dataset_link")
    if explicit:
        return f"[Link]({explicit})"
    url = first_link(links.get("datasets", {}).get(dataset))
    return f"[Link]({url})" if url else "-"


def aggregate(benchmark_docs: list[dict[str, Any]]) -> dict[str, Any]:
    by_dataset: dict[str, list[dict[str, Any]]] = defaultdict(list)
    metric_info: dict[str, dict[str, str]] = {}
    works = []
    edges = []
    assets = []

    for doc in benchmark_docs:
        paper = doc.get("paper", {}) if isinstance(doc.get("paper"), dict) else {}
        benches = doc.get("benchmarks", []) if isinstance(doc.get("benchmarks"), list) else []
        works.append({"paper": paper, "benchmarks": benches})
        edges.extend(as_list(doc.get("related_work_edges")))

        for bench in benches:
            if not isinstance(bench, dict):
                continue
            dataset = str(bench.get("dataset", "")).strip()
            if not dataset:
                continue
            by_dataset[dataset].append({"paper": paper, "benchmark": bench})
            for metric in as_list(bench.get("metrics")):
                name = metric_name(metric)
                if not name:
                    continue
                if isinstance(metric, dict):
                    metric_info.setdefault(
                        name,
                        {
                            "direction": str(metric.get("direction", "unknown")),
                            "meaning": str(metric.get("meaning", "")),
                        },
                    )
                else:
                    metric_info.setdefault(name, {"direction": "unknown", "meaning": ""})
            for asset in as_list(bench.get("assets")):
                if asset:
                    assets.append({"paper": paper, "dataset": dataset, "asset": str(asset)})

    return {"by_dataset": by_dataset, "metric_info": metric_info, "works": works, "edges": edges, "assets": assets}


def generate_report(topic: str, benchmark_docs: list[dict[str, Any]], links: dict[str, Any]) -> str:
    agg = aggregate(benchmark_docs)
    by_dataset = agg["by_dataset"]
    metric_info = agg["metric_info"]
    works = agg["works"]

    lines: list[str] = []
    lines.append(f"# Benchmark Survey: {topic}")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append("")

    lines.append("## TL;DR")
    if by_dataset:
        names = ", ".join(sorted(by_dataset))
        lines.append(f"Found {len(by_dataset)} evaluated benchmark dataset(s): {names}.")
    else:
        lines.append("No extracted benchmark datasets were found. Check benchmarks.json.")
    lines.append("")

    lines.append("## Basic Metrics")
    if metric_info:
        for name, info in sorted(metric_info.items()):
            direction = info.get("direction") or "unknown"
            arrow = "↓" if direction == "lower_is_better" else "↑" if direction == "higher_is_better" else ""
            meaning = info.get("meaning") or ""
            lines.append(f"- **{name}{arrow}**: {meaning}".rstrip())
    else:
        lines.append("- No metrics extracted.")
    lines.append("")

    if links.get("eval_scripts"):
        lines.append("## Eval Scripts")
        for name, item in sorted(links["eval_scripts"].items()):
            url = first_link(item)
            lines.append(f"- [{name}]({url})" if url else f"- {name}")
        lines.append("")

    lines.append("## Benchmark Overview")
    lines.append("| Dataset | Link | Suitable Task | Common Metrics | Representative Work |")
    lines.append("|---|---|---|---|---|")
    if by_dataset:
        for dataset, entries in sorted(by_dataset.items()):
            metrics = sorted({metric_label(m) for e in entries for m in as_list(e["benchmark"].get("metrics")) if metric_label(m)})
            tasks = sorted({str(e["benchmark"].get("task", "")).strip() for e in entries if str(e["benchmark"].get("task", "")).strip()})
            titles = sorted({paper_title(e["paper"]) for e in entries})
            link = dataset_link(dataset, entries[0]["benchmark"], links)
            lines.append(f"| {dataset} | {link} | {'; '.join(tasks) or '-'} | {', '.join(metrics) or '-'} | {', '.join(titles) or '-'} |")
    else:
        lines.append("| - | - | - | - | - |")
    lines.append("")

    lines.append("## Representative Works")
    for work in works:
        paper = work["paper"]
        title = paper_title(paper)
        arxiv = paper.get("links", {}).get("arxiv", "") if isinstance(paper.get("links"), dict) else ""
        lines.append(f"### [{title}]({arxiv})" if arxiv else f"### {title}")
        for bench in work["benchmarks"]:
            dataset = bench.get("dataset", "")
            metrics = ", ".join(metric_label(m) for m in as_list(bench.get("metrics")) if metric_label(m)) or "-"
            methods = ", ".join(method_name(m) for m in as_list(bench.get("compared_methods")) if method_name(m)) or "-"
            task = bench.get("task") or "-"
            lines.append(f"- **{dataset}**: {task}; metrics: {metrics}; compared methods: {methods}")
            if bench.get("evidence"):
                lines.append(f"  - Evidence: {bench['evidence']}")
            if bench.get("notes"):
                lines.append(f"  - Notes: {bench['notes']}")
        lines.append("")

    lines.append("## Grouped By Benchmark")
    for dataset, entries in sorted(by_dataset.items()):
        lines.append(f"### {dataset}")
        for entry in entries:
            title = paper_title(entry["paper"])
            bench = entry["benchmark"]
            metrics = ", ".join(metric_label(m) for m in as_list(bench.get("metrics")) if metric_label(m)) or "-"
            methods = ", ".join(method_name(m) for m in as_list(bench.get("compared_methods")) if method_name(m)) or "-"
            lines.append(f"- **{title}**: uses {dataset}; metrics: {metrics}; compared with: {methods}.")
        lines.append("")

    if agg["assets"]:
        lines.append("## Experiment Figures/Tables")
        for item in agg["assets"]:
            asset = item["asset"]
            lines.append(f"- {paper_title(item['paper'])} / {item['dataset']}: `{asset}`")
            if asset.lower().endswith((".png", ".jpg", ".jpeg")):
                lines.append(f"  ![[{Path(asset).name}]]")
        lines.append("")

    lines.append("## Related Work Discovery Path")
    if agg["edges"]:
        for edge in agg["edges"]:
            if isinstance(edge, dict):
                lines.append(f"- {edge.get('source', '-')} -> {edge.get('target', '-')} ({edge.get('reason', '')})")
    else:
        for dataset, entries in sorted(by_dataset.items()):
            for entry in entries:
                title = paper_title(entry["paper"])
                for method in as_list(entry["benchmark"].get("compared_methods")):
                    name = method_name(method)
                    if name:
                        lines.append(f"- {title} -> compare_with {name} -> related candidate on {dataset}")
    lines.append("")
    return "\n".join(lines)


def generate_single_paper_report(benchmark_docs: list[dict[str, Any]], links: dict[str, Any]) -> str:
    if not benchmark_docs:
        return "# Benchmark Analysis\n\nNo extracted benchmark datasets were found. Check benchmarks.json.\n"

    doc = benchmark_docs[0]
    paper = doc.get("paper", {}) if isinstance(doc.get("paper"), dict) else {}
    benches = doc.get("benchmarks", []) if isinstance(doc.get("benchmarks"), list) else []
    title = paper_title(paper)

    lines: list[str] = []
    lines.append(f"# Benchmark Analysis: {title}")
    lines.append("")
    if isinstance(paper.get("links"), dict):
        parts = []
        if paper["links"].get("arxiv"):
            parts.append(f"[arXiv]({paper['links']['arxiv']})")
        if paper["links"].get("pdf"):
            parts.append(f"[PDF]({paper['links']['pdf']})")
        if parts:
            lines.append(" | ".join(parts))
            lines.append("")

    lines.append("## Conclusion")
    if benches:
        dataset_names = ", ".join(str(bench.get("dataset", "")).strip() for bench in benches if str(bench.get("dataset", "")).strip())
        lines.append(f"This paper evaluates on {dataset_names}.")
    else:
        lines.append("No extracted benchmark datasets were found. Check benchmarks.json.")
    lines.append("")

    lines.append("## Benchmark Table")
    lines.append("| Dataset | Link | Evaluated Ability | Metrics | Compared Methods | Evidence |")
    lines.append("|---|---|---|---|---|---|")
    for bench in benches:
        dataset = str(bench.get("dataset", "")).strip() or "-"
        link = dataset_link(dataset, bench, links)
        task = str(bench.get("task", "")).strip() or "-"
        metrics = ", ".join(metric_label(metric) for metric in as_list(bench.get("metrics")) if metric_label(metric)) or "-"
        methods = ", ".join(method_name(method) for method in as_list(bench.get("compared_methods")) if method_name(method)) or "-"
        evidence = str(bench.get("evidence", "")).strip() or "-"
        lines.append(f"| {dataset} | {link} | {task} | {metrics} | {methods} | {evidence} |")
    if not benches:
        lines.append("| - | - | - | - | - | - |")
    lines.append("")

    lines.append("## Datasets And Metrics")
    for bench in benches:
        dataset = str(bench.get("dataset", "")).strip() or "Unknown Dataset"
        lines.append(f"### {dataset}")
        if bench.get("task"):
            lines.append(f"- Purpose: {bench['task']}")
        metrics = ", ".join(metric_label(metric) for metric in as_list(bench.get("metrics")) if metric_label(metric))
        if metrics:
            lines.append(f"- Metrics: {metrics}")
        methods = ", ".join(method_name(method) for method in as_list(bench.get("compared_methods")) if method_name(method))
        if methods:
            lines.append(f"- Compared methods: {methods}")
        if bench.get("evidence"):
            lines.append(f"- Evidence: {bench['evidence']}")
        if bench.get("notes"):
            lines.append(f"- Notes: {bench['notes']}")
        lines.append("")

    lines.append("## Related Work / Baselines")
    edges = as_list(doc.get("related_work_edges"))
    if edges:
        for edge in edges:
            if isinstance(edge, dict):
                lines.append(f"- {edge.get('source', '-') } -> {edge.get('target', '-')} ({edge.get('reason', '')})")
    else:
        lines.append("- No explicit related-work edges were extracted.")
    lines.append("")
    return "\n".join(lines)


def resolve_output_path(
    output: str | None,
    config_path: str | None,
    mode: str,
    paper_id: str | None,
    topic: str,
) -> Path:
    if output:
        return Path(output).expanduser().resolve()
    try:
        config = load_runtime_config(config_path)
    except ConfigError as exc:
        raise SystemExit(f"{exc} Or pass --output explicitly.") from exc

    if mode == "single-paper":
        if not paper_id:
            raise SystemExit("Single-paper mode needs --paper-id when --output is omitted.")
        return build_single_report_path(config, paper_id).resolve()
    return build_survey_report_path(config, topic).resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate benchmark survey Markdown")
    parser.add_argument("--input", required=True, help="Comma-separated JSON inputs")
    parser.add_argument("--output", help="Output Markdown file")
    parser.add_argument("--config", help="Path to config.yaml")
    parser.add_argument("--paper-id", help="Paper id for single-paper report path resolution")
    parser.add_argument("--mode", choices=["survey", "single-paper"], default="survey", help="Report mode")
    parser.add_argument("--topic", default="Benchmark Survey", help="Survey topic")
    args = parser.parse_args()

    input_files = [x.strip() for x in args.input.split(",") if x.strip()]
    _, benchmark_docs, links = load_inputs(input_files)
    report = (
        generate_single_paper_report(benchmark_docs, links)
        if args.mode == "single-paper"
        else generate_report(args.topic, benchmark_docs, links)
    )
    output = resolve_output_path(args.output, args.config, args.mode, args.paper_id, args.topic)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"Wrote report to {output}", flush=True)


if __name__ == "__main__":
    main()

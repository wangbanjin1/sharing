#!/usr/bin/env python3
"""Collect candidate links for datasets, metrics, eval scripts, and methods."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from config_utils import ConfigError, load_runtime_config


FETCH_TIMEOUT = 8


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
    # JSON does not allow bare ASCII control characters inside strings.
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)


def load_json_loose(path: Path) -> Any:
    text = read_text_loose(path)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        print(
            f"Could not parse {path} as JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc


def fetch_json(url: str) -> Any | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "benchmark-arxiv/0.1"})
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        print(f"Link fetch failed: {exc}", file=sys.stderr)
        return None


def fetch_text(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "benchmark-arxiv/0.1"})
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as response:
            return response.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def search_github(query: str, max_results: int = 4) -> list[dict[str, str]]:
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
        {"q": query, "per_page": max_results, "sort": "stars", "order": "desc"}
    )
    data = fetch_json(url)
    results = []
    for item in (data or {}).get("items", [])[:max_results]:
        results.append(
            {
                "source": "github",
                "url": item.get("html_url", ""),
                "title": item.get("full_name", item.get("name", "")),
                "description": item.get("description") or "",
            }
        )
    return results


def search_huggingface_dataset(query: str, max_results: int = 4) -> list[dict[str, str]]:
    url = "https://huggingface.co/api/datasets?" + urllib.parse.urlencode({"search": query, "limit": max_results})
    data = fetch_json(url)
    results = []
    if isinstance(data, list):
        for item in data[:max_results]:
            dataset_id = item.get("id") or ""
            results.append(
                {
                    "source": "huggingface",
                    "url": f"https://huggingface.co/datasets/{dataset_id}" if dataset_id else "",
                    "title": dataset_id,
                    "description": item.get("description") or "",
                }
            )
    return results


def search_arxiv(query: str, max_results: int = 2) -> list[dict[str, str]]:
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": f'all:"{query}"', "start": 0, "max_results": max_results, "sortBy": "relevance"}
    )
    text = fetch_text(url)
    if not text:
        return []
    root = ET.fromstring(text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    results = []
    for entry in root.findall("atom:entry", ns)[:max_results]:
        link = entry.findtext("atom:id", default="", namespaces=ns)
        title = " ".join(entry.findtext("atom:title", default="", namespaces=ns).split())
        results.append({"source": "arxiv", "url": link, "title": title, "description": ""})
    return results


def search_paperswithcode(query: str, max_results: int = 4) -> list[dict[str, str]]:
    url = "https://paperswithcode.com/search/?" + urllib.parse.urlencode({"q": query})
    html = fetch_text(url)
    results = []
    seen = set()
    for path, title in re.findall(r'href="(/(?:dataset|task|paper|method|sota)[^"]+)"[^>]*>([^<]+)<', html):
        full = f"https://paperswithcode.com{path}"
        if full in seen:
            continue
        seen.add(full)
        results.append({"source": "paperswithcode", "url": full, "title": re.sub(r"\s+", " ", title).strip(), "description": ""})
        if len(results) >= max_results:
            break
    return results


def normalize_metric(metric: Any) -> str:
    if isinstance(metric, dict):
        return str(metric.get("name", "")).strip()
    return str(metric).strip()


def read_benchmark_file(path: Path) -> tuple[set[str], set[str], set[str]]:
    data = load_json_loose(path)
    datasets: set[str] = set()
    metrics: set[str] = set()
    scripts: set[str] = set()

    def visit(obj: Any) -> None:
        if isinstance(obj, dict):
            if obj.get("dataset"):
                datasets.add(str(obj["dataset"]).strip())
            if obj.get("name") and obj.get("type") == "dataset":
                datasets.add(str(obj["name"]).strip())
            for dataset in obj.get("datasets", []) or []:
                if isinstance(dataset, dict):
                    name = dataset.get("name") or dataset.get("dataset")
                    if name:
                        datasets.add(str(name).strip())
                elif isinstance(dataset, str):
                    datasets.add(dataset.strip())
            for metric in obj.get("metrics", []) or []:
                name = normalize_metric(metric)
                if name:
                    metrics.add(name)
            for script in obj.get("eval_scripts", []) or []:
                if isinstance(script, dict) and script.get("name"):
                    scripts.add(str(script["name"]).strip())
                elif isinstance(script, str):
                    scripts.add(script.strip())
            for value in obj.values():
                visit(value)
        elif isinstance(obj, list):
            for item in obj:
                visit(item)

    visit(data)
    return datasets, metrics, scripts


def collect_item(name: str, kind: str) -> dict[str, Any]:
    if kind == "dataset":
        queries = [f"{name} dataset benchmark", f"{name} official dataset"]
        results = []
        results.extend(search_huggingface_dataset(name, max_results=3))
        results.extend(search_github(queries[0], max_results=3))
        results.extend(search_paperswithcode(name, max_results=2))
        if len(results) < 2:
            results.extend(search_arxiv(queries[1], max_results=2))
    elif kind == "metric":
        results = []
        results.extend(search_github(f"{name} evaluation metric", max_results=3))
        results.extend(search_paperswithcode(f"{name} metric", max_results=2))
    else:
        results = []
        results.extend(search_github(f"{name} audio evaluation", max_results=3))
        if len(results) < 2:
            results.extend(search_arxiv(name, max_results=2))
    return {"name": name, "kind": kind, "candidates": results}


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect candidate benchmark links")
    parser.add_argument("--config", help="Path to config.yaml")
    parser.add_argument("--input", help="Benchmark JSON file")
    parser.add_argument("--datasets", help="Comma-separated dataset names")
    parser.add_argument("--metrics", help="Comma-separated metric names")
    parser.add_argument("--eval-scripts", help="Comma-separated eval script names")
    parser.add_argument("--force", action="store_true", help="Ignore config enable_collect_links and collect anyway")
    parser.add_argument("--output", help="Output JSON")
    args = parser.parse_args()

    output_path = args.output
    if not output_path:
        if args.input:
            output_path = str(Path(args.input).expanduser().resolve().with_name("links.json"))
        else:
            output_path = "links.json"

    if args.config and not args.force:
        try:
            config = load_runtime_config(args.config)
        except ConfigError as exc:
            raise SystemExit(str(exc)) from exc
        if not config.enable_collect_links:
            result = {
                "datasets": {},
                "metrics": {},
                "eval_scripts": {},
                "skipped": True,
                "reason": "collect_links disabled by config",
            }
            Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Skipped link collection because enable_collect_links is false in {config.config_path}", file=sys.stderr)
            return

    datasets: set[str] = set()
    metrics: set[str] = set()
    scripts: set[str] = set()
    if args.input:
        d, m, s = read_benchmark_file(Path(args.input))
        datasets |= d
        metrics |= m
        scripts |= s
    if args.datasets:
        datasets |= {x.strip() for x in args.datasets.split(",") if x.strip()}
    if args.metrics:
        metrics |= {x.strip() for x in args.metrics.split(",") if x.strip()}
    if args.eval_scripts:
        scripts |= {x.strip() for x in args.eval_scripts.split(",") if x.strip()}

    result = {
        "datasets": {name: collect_item(name, "dataset") for name in sorted(datasets)},
        "metrics": {name: collect_item(name, "metric") for name in sorted(metrics)},
        "eval_scripts": {name: collect_item(name, "eval_script") for name in sorted(scripts)},
    }

    Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Wrote links for {len(datasets)} datasets, {len(metrics)} metrics, {len(scripts)} eval scripts to {output_path}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()

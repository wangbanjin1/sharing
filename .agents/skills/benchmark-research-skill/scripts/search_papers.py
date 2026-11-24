#!/usr/bin/env python3
"""Search arXiv papers for a benchmark survey."""

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

from config_utils import ConfigError, build_survey_run_dir, load_runtime_config


DEFAULT_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.MM", "cs.SD"]


def load_config(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    config_path = Path(path)
    if not config_path.exists():
        print(f"Warning: config not found: {config_path}", file=sys.stderr)
        return {}
    try:
        import yaml
    except ImportError:
        print("Warning: PyYAML not installed; ignoring config", file=sys.stderr)
        return {}
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def domain_for_topic(topic: str, config: dict[str, Any]) -> dict[str, Any] | None:
    topic_l = topic.lower()
    best: tuple[int, dict[str, Any]] | None = None
    for name, domain in (config.get("research_domains") or {}).items():
        keywords = [name, *(domain.get("keywords") or [])]
        score = sum(1 for kw in keywords if str(kw).lower() in topic_l or topic_l in str(kw).lower())
        if score and (best is None or score > best[0]):
            best = (score, domain)
    return best[1] if best else None


def categories_for_topic(topic: str, config: dict[str, Any], cli_categories: str | None) -> list[str]:
    if cli_categories:
        return [c.strip() for c in cli_categories.split(",") if c.strip()]
    domain = domain_for_topic(topic, config)
    if domain and domain.get("arxiv_categories"):
        return list(dict.fromkeys(domain["arxiv_categories"]))
    return DEFAULT_CATEGORIES


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9\-]{1,}", text)]


def relevance_score(paper: dict[str, Any], topic: str, config: dict[str, Any]) -> float:
    topic_terms = set(tokenize(topic))
    domain = domain_for_topic(topic, config) or {}
    keyword_terms = set()
    for kw in domain.get("keywords") or []:
        keyword_terms.update(tokenize(str(kw)))
    terms = topic_terms | keyword_terms
    if not terms:
        return 0.0

    title = set(tokenize(paper.get("title", "")))
    summary = set(tokenize(paper.get("summary", "")))
    title_hits = len(terms & title)
    summary_hits = len(terms & summary)
    return title_hits * 2.0 + summary_hits * 0.5


def is_excluded(paper: dict[str, Any], config: dict[str, Any]) -> bool:
    haystack = f"{paper.get('title', '')} {paper.get('summary', '')}".lower()
    return any(str(word).lower() in haystack for word in config.get("excluded_keywords") or [])


def build_query(query_text: str, categories: list[str]) -> str:
    topic_query = f'all:"{query_text}"'
    category_query = " OR ".join(f"cat:{cat}" for cat in categories)
    return f"({topic_query}) AND ({category_query})"


def search_arxiv(query_text: str, max_results: int, categories: list[str]) -> dict[str, Any]:
    query = build_query(query_text, categories)
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"https://export.arxiv.org/api/query?{urllib.parse.urlencode(params)}"
    print(f"Searching arXiv for query={query_text!r}", file=sys.stderr)

    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            xml_content = response.read().decode("utf-8")
    except Exception as exc:
        print(f"Error fetching arXiv results: {exc}", file=sys.stderr)
        return {"total": 0, "papers": [], "query": query, "query_text": query_text, "categories": categories}

    root = ET.fromstring(xml_content)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    papers: list[dict[str, Any]] = []

    for entry in root.findall("atom:entry", ns):
        entry_id = entry.findtext("atom:id", default="", namespaces=ns)
        pdf_link = ""
        for link in entry.findall("atom:link", ns):
            if link.get("title") == "pdf":
                pdf_link = link.get("href", "")
        paper = {
            "id": entry_id.rsplit("/", 1)[-1],
            "title": " ".join(entry.findtext("atom:title", default="", namespaces=ns).split()),
            "summary": " ".join(entry.findtext("atom:summary", default="", namespaces=ns).split()),
            "authors": [
                name.text
                for author in entry.findall("atom:author", ns)
                for name in [author.find("atom:name", ns)]
                if name is not None and name.text
            ],
            "published": entry.findtext("atom:published", default="", namespaces=ns)[:10],
            "categories": [cat.get("term") for cat in entry.findall("atom:category", ns) if cat.get("term")],
            "links": {"arxiv": entry_id, "pdf": pdf_link},
        }
        papers.append(paper)

    return {"total": len(papers), "papers": papers, "query": query, "query_text": query_text, "categories": categories}


def merge_paper_results(results: list[dict[str, Any]], topic: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for result in results:
        query_text = result.get("query_text", "")
        for paper in result.get("papers", []):
            paper_id = paper.get("id", "")
            if not paper_id:
                continue
            target = merged.setdefault(paper_id, paper)
            target.setdefault("matched_queries", [])
            if query_text and query_text not in target["matched_queries"]:
                target["matched_queries"].append(query_text)

    filtered = []
    for paper in merged.values():
        if is_excluded(paper, config):
            continue
        base = relevance_score(paper, topic, config)
        related_bonus = min(len(paper.get("matched_queries", [])), 5) * 0.7
        experiment_bonus = 0.0
        haystack = f"{paper.get('title', '')} {paper.get('summary', '')}".lower()
        for token in ["experiment", "evaluation", "benchmark", "dataset", "baseline", "state-of-the-art", "results"]:
            if token in haystack:
                experiment_bonus += 0.25
        paper["relevance_score"] = base + related_bonus + experiment_bonus
        filtered.append(paper)
    filtered.sort(key=lambda p: (p.get("relevance_score", 0.0), p.get("published", "")), reverse=True)
    return filtered


def main() -> None:
    parser = argparse.ArgumentParser(description="Search arXiv papers for benchmark survey")
    parser.add_argument("--topic", help="Search topic used for ranking and as default query")
    parser.add_argument("--query", action="append", help="Search query. Can be repeated.")
    parser.add_argument("--queries-file", help="JSON file containing seed_queries/benchmark_queries or a list of strings")
    parser.add_argument("--config", help="YAML config path")
    parser.add_argument("--output", help="Output JSON file")
    parser.add_argument("--max-results", type=int, default=50, help="Maximum arXiv results")
    parser.add_argument("--categories", help="Comma-separated arXiv categories")
    parser.add_argument("--top-n", type=int, default=0, help="Keep top N after scoring; 0 keeps all")
    args = parser.parse_args()

    config = load_config(args.config)
    queries = list(args.query or [])
    if args.queries_file:
        data = json.loads(Path(args.queries_file).read_text(encoding="utf-8"))
        if isinstance(data, list):
            queries.extend(str(item) for item in data)
        elif isinstance(data, dict):
            for key in ["seed_queries", "benchmark_queries", "queries"]:
                queries.extend(str(item) for item in data.get(key, []) or [])
    if args.topic:
        queries.insert(0, args.topic)
    queries = list(dict.fromkeys(q.strip() for q in queries if q and q.strip()))
    if not queries:
        parser.error("provide --topic, --query, or --queries-file")

    ranking_topic = args.topic or queries[0]
    categories = categories_for_topic(ranking_topic, config, args.categories)
    results = [search_arxiv(query, args.max_results, categories) for query in queries]
    filtered = merge_paper_results(results, ranking_topic, config)
    if args.top_n > 0:
        filtered = filtered[: args.top_n]

    result = {
        "topic": ranking_topic,
        "queries": queries,
        "categories": categories,
        "total_raw": sum(r.get("total", 0) for r in results),
        "total_after_dedupe_filter": len(filtered),
        "papers": filtered,
    }

    output_path = args.output
    if not output_path:
        try:
            runtime = load_runtime_config(args.config)
        except ConfigError as exc:
            raise SystemExit(f"{exc} Or pass --output explicitly.") from exc
        output_path = str(build_survey_run_dir(runtime, ranking_topic) / "papers.json")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(filtered)} papers to {output}", file=sys.stderr)


if __name__ == "__main__":
    main()

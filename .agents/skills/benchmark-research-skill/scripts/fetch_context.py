#!/usr/bin/env python3
"""Fetch benchmark-focused paper context for Claude Code.

This script is the single-paper backbone:
- fetch arXiv abs/source/PDF evidence
- extract experiment/evaluation sections and tables
- optionally recover source figures and render likely experiment pages
- write one context.json that Claude Code can read directly
"""

from __future__ import annotations

import argparse
import gzip
import html
import json
import os
import re
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from config_utils import ConfigError, build_single_paper_dir, load_runtime_config


USER_AGENT = "benchmark-arxiv/0.1 (mailto:none@example.com)"
ABS_TIMEOUT = 10
API_TIMEOUT = 6
SOURCE_TIMEOUT = 35
PDF_TIMEOUT = 20
SECTION_HINTS = [
    "experiment",
    "experimental",
    "evaluation",
    "benchmark",
    "result",
    "ablation",
    "dataset",
    "metric",
]
SECTION_END_HINTS = [
    "conclusion",
    "related work",
    "references",
    "acknowledg",
    "appendix",
]
PAGE_KEYWORDS = [
    "experiment",
    "experimental",
    "evaluation",
    "benchmark",
    "dataset",
    "metric",
    "result",
    "ablation",
    "baseline",
    "fad",
    "mos",
    "accuracy",
]
SOURCE_DIR_HINTS = ["pics", "figures", "fig", "images", "img"]
SOURCE_FIGURE_EXTS = {".png", ".jpg", ".jpeg", ".pdf", ".eps", ".svg"}


def normalize_arxiv_id(value: str) -> str:
    value = value.strip().replace("arXiv:", "").replace("arxiv:", "")
    value = value.rstrip("/")
    if "/" in value:
        value = value.rsplit("/", 1)[-1]
    return value


def log_step(message: str) -> None:
    print(f"[benchmark-arxiv] {message}", file=sys.stderr, flush=True)


def resolve_output_dir(output_dir: str | None, config_path: str | None, paper_id: str | None, pdf: str | None) -> Path:
    if output_dir:
        return Path(output_dir).expanduser().resolve()
    try:
        config = load_runtime_config(config_path)
    except ConfigError as exc:
        raise SystemExit(str(exc)) from exc

    paper_key = normalize_arxiv_id(paper_id) if paper_id else Path(pdf or "local.pdf").stem
    return build_single_paper_dir(config, paper_key).resolve()


def fetch_url(url: str, suffix: str, destination: Path | None = None, retries: int = 1, timeout: int = 20) -> Path | None:
    if destination is None:
        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        Path(temp_path).unlink(missing_ok=True)
        path = Path(temp_path)
    else:
        path = destination
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = response.read()
            path.write_bytes(data)
            return path
        except urllib.error.HTTPError:
            return None
        except Exception:
            if attempt < retries:
                time.sleep(2 * attempt)
                continue
            return None
    return None


def download_arxiv_pdf(arxiv_id: str, output_path: Path, timeout: int = 30) -> Path | None:
    arxiv_id = normalize_arxiv_id(arxiv_id)
    return fetch_url(f"https://arxiv.org/pdf/{arxiv_id}", ".pdf", destination=output_path, timeout=timeout)


def prepare_source_tree(arxiv_id: str, source_dir: Path) -> Path | None:
    arxiv_id = normalize_arxiv_id(arxiv_id)
    source_dir.mkdir(parents=True, exist_ok=True)
    extract_dir = source_dir / "extracted"
    if extract_dir.exists() and any(extract_dir.rglob("*")):
        log_step(f"reuse cached source for {arxiv_id}")
        return extract_dir

    package = source_dir / "arxiv-source.tar.gz"
    log_step(f"download arXiv source for {arxiv_id}")
    package = fetch_url(f"https://arxiv.org/e-print/{arxiv_id}", ".tar.gz", destination=package, timeout=SOURCE_TIMEOUT)
    if not package:
        log_step("source download unavailable, will fall back to PDF/summary if needed")
        return None

    extract_dir.mkdir(parents=True, exist_ok=True)
    try:
        log_step("extract source package")
        with tarfile.open(package, "r:*") as tar:
            safe_members = []
            for member in tar.getmembers():
                if member.name.startswith("/") or ".." in member.name:
                    continue
                if member.issym() or member.islnk():
                    continue
                safe_members.append(member)
            tar.extractall(path=extract_dir, members=safe_members)
        return extract_dir
    except tarfile.ReadError:
        try:
            log_step("source package looks like gzipped tex, converting directly")
            with gzip.open(package, "rb") as handle:
                content = handle.read()
            (extract_dir / "source.tex").write_bytes(content)
            return extract_dir
        except Exception:
            return None
    except Exception:
        return None


def read_source_text(source_root: Path) -> tuple[str, list[dict[str, str]]]:
    files: list[dict[str, str]] = []
    chunks: list[str] = []
    for path in sorted(source_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() != ".tex":
            continue
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = path.relative_to(source_root).as_posix()
        files.append({"path": rel, "chars": str(len(raw))})
        chunks.append(f"\n\n%% FILE: {rel}\n\n{raw}")
    return "\n".join(chunks), files


def discover_source_figure_candidates(source_root: Path, graphics_hints: list[str] | None = None) -> list[Path]:
    hints = set(graphics_hints or [])
    candidates: list[Path] = []
    seen: set[Path] = set()

    for hint_dir in SOURCE_DIR_HINTS:
        for folder in source_root.rglob(hint_dir):
            if not folder.is_dir():
                continue
            for path in folder.iterdir():
                if path.is_file() and path.suffix.lower() in SOURCE_FIGURE_EXTS and path not in seen:
                    seen.add(path)
                    candidates.append(path)

    if not candidates:
        for path in source_root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".pdf"}:
                continue
            lowered = path.name.lower()
            if "logo" in lowered or "icon" in lowered:
                continue
            if path not in seen:
                seen.add(path)
                candidates.append(path)

    def candidate_score(path: Path) -> tuple[int, str]:
        stem = path.stem.lower()
        score = 0
        if path.parent.name.lower() in SOURCE_DIR_HINTS:
            score += 2
        if stem in hints:
            score += 10
        if any(hint and hint in stem for hint in hints):
            score += 4
        if "fig" in stem or "figure" in stem:
            score += 2
        return (score, path.name.lower())

    return sorted(candidates, key=candidate_score, reverse=True)


def get_arxiv_metadata(paper_id: str) -> dict[str, Any] | None:
    paper_id = normalize_arxiv_id(paper_id)
    log_step(f"try arXiv API metadata for {paper_id}")
    path = fetch_url(f"https://export.arxiv.org/api/query?id_list={paper_id}", ".xml", timeout=API_TIMEOUT)
    if not path:
        return None

    root = ET.fromstring(Path(path).read_text(encoding="utf-8", errors="ignore"))
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = root.findall("atom:entry", ns)
    if not entries:
        return None

    entry = entries[0]
    entry_id = entry.findtext("atom:id", default="", namespaces=ns)
    pdf_link = ""
    for link in entry.findall("atom:link", ns):
        if link.get("title") == "pdf":
            pdf_link = link.get("href", "")
    return {
        "id": entry_id.rsplit("/", 1)[-1] or paper_id,
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


def html_meta_values(page: str, name: str) -> list[str]:
    values: list[str] = []
    patterns = [
        rf'<meta\s+name=["\']{re.escape(name)}["\']\s+content=["\']([^"\']*)["\'][^>]*>',
        rf'<meta\s+content=["\']([^"\']*)["\']\s+name=["\']{re.escape(name)}["\'][^>]*>',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, page, re.I):
            values.append(html.unescape(match.group(1)).strip())
    return [value for value in values if value]


def strip_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(value).split())


def parse_abs_metadata(paper_id: str) -> dict[str, Any] | None:
    paper_id = normalize_arxiv_id(paper_id)
    log_step(f"fetch arXiv abs page for {paper_id}")
    path = fetch_url(f"https://arxiv.org/abs/{paper_id}", ".html", timeout=ABS_TIMEOUT)
    if not path:
        return None
    page = Path(path).read_text(encoding="utf-8", errors="ignore")

    title = next(iter(html_meta_values(page, "citation_title")), "")
    authors = html_meta_values(page, "citation_author")
    published = next(iter(html_meta_values(page, "citation_date")), "")
    pdf_url = next(iter(html_meta_values(page, "citation_pdf_url")), "")
    abstract = ""
    abstract_match = re.search(r'<blockquote\s+class=["\']abstract[^"\']*["\'][^>]*>([\s\S]*?)</blockquote>', page, re.I)
    if abstract_match:
        abstract = re.sub(r"^\s*Abstract:\s*", "", strip_html(abstract_match.group(1)), flags=re.I)
    categories = re.findall(r'<span\s+class=["\']primary-subject["\'][^>]*>(.*?)</span>', page, re.I)

    if not title and not authors and not abstract:
        return None
    return {
        "id": paper_id,
        "title": " ".join(title.split()),
        "summary": abstract,
        "authors": authors,
        "published": published[:10],
        "categories": [strip_html(category) for category in categories],
        "links": {
            "arxiv": f"https://arxiv.org/abs/{paper_id}",
            "pdf": pdf_url or f"https://arxiv.org/pdf/{paper_id}",
        },
        "metadata_status": "from_arxiv_abs",
    }


def fallback_metadata(paper_id: str) -> dict[str, Any]:
    paper_id = normalize_arxiv_id(paper_id)
    return {
        "id": paper_id,
        "title": "",
        "summary": "",
        "authors": [],
        "published": "",
        "categories": [],
        "links": {
            "arxiv": f"https://arxiv.org/abs/{paper_id}",
            "pdf": f"https://arxiv.org/pdf/{paper_id}",
        },
        "metadata_status": "fallback_without_arxiv_api",
    }


def read_pdf_text(pdf_path: str) -> str:
    try:
        import fitz
    except ImportError:
        print("PyMuPDF is not installed; cannot read PDF", file=sys.stderr)
        return ""
    try:
        log_step(f"read PDF text from {pdf_path}")
        doc = fitz.open(pdf_path)
        text = "\n\n".join(f"%% PAGE {index + 1}\n{page.get_text()}" for index, page in enumerate(doc))
        doc.close()
        return text
    except Exception as exc:
        print(f"Could not extract PDF text: {exc}", file=sys.stderr)
        return ""


def clean_for_context(text: str) -> str:
    text = re.sub(r"(?<!\\)%.*", "", text)
    text = text.replace("\\&", "&").replace("\\_", "_").replace("~", " ")
    text = re.sub(r"\\(?:cite|ref|label)\*?(?:\[[^\]]*\])?\{[^{}]*\}", " ", text)
    text = re.sub(r"\\(?:textbf|emph|textit)\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def heading_regex() -> re.Pattern[str]:
    hint = "|".join(SECTION_HINTS)
    return re.compile(
        rf"(?im)(\\(?:sub)*section\*?\{{[^}}]*(?:{hint})[^}}]*\}}|^\s*(?:#+\s*)?(?:\d+\.?\s*)?(?:{hint})[^\n]{{0,90}}$)"
    )


def end_regex() -> re.Pattern[str]:
    hint = "|".join(SECTION_END_HINTS)
    return re.compile(rf"(?im)(\\section\*?\{{[^}}]*(?:{hint})[^}}]*\}}|^\s*(?:#+\s*)?(?:\d+\.?\s*)?(?:{hint})\b)")


def find_candidate_sections(text: str, max_chars: int = 18000) -> list[dict[str, Any]]:
    matches = list(heading_regex().finditer(text))
    sections: list[dict[str, Any]] = []
    if not matches:
        return [{"heading": "full_text_fallback", "start": 0, "end": min(len(text), max_chars), "text": text[:max_chars]}]

    for match in matches[:8]:
        start = match.start()
        tail = text[start:]
        end_match = end_regex().search(tail[500:])
        end = start + 500 + end_match.start() if end_match else min(len(text), start + max_chars)
        section_text = text[start:end][:max_chars]
        sections.append(
            {
                "heading": " ".join(match.group(0).split())[:160],
                "start": start,
                "end": end,
                "text": section_text,
            }
        )
    return sections


def extract_table_blocks(text: str, max_blocks: int = 12) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    for match in re.finditer(r"\\begin\{table\*?\}[\s\S]*?\\end\{table\*?\}", text, re.I):
        raw = match.group(0)
        caption_match = re.search(r"\\caption(?:\[[^\]]*\])?\{([\s\S]*?)\}", raw)
        caption = clean_for_context(caption_match.group(1)) if caption_match else ""
        blocks.append({"kind": "latex_table", "caption": caption, "text": clean_for_context(raw)[:5000]})
        if len(blocks) >= max_blocks:
            return blocks

    lines = text.splitlines()
    for index, line in enumerate(lines):
        lowered = line.lower()
        if ("table" in lowered or "benchmark" in lowered or "dataset" in lowered) and len(line) < 180:
            snippet = "\n".join(lines[max(0, index - 5) : min(len(lines), index + 25)])
            blocks.append({"kind": "text_table_context", "caption": line.strip(), "text": snippet[:5000]})
            if len(blocks) >= max_blocks:
                break
    return blocks


def extraction_schema() -> dict[str, Any]:
    return {
        "paper": {"id": "", "title": "", "links": {"arxiv": "", "pdf": ""}},
        "benchmarks": [
            {
                "dataset": "",
                "dataset_link": None,
                "task": "",
                "metrics": [{"name": "", "direction": "lower_is_better|higher_is_better|unknown", "meaning": ""}],
                "protocol": "",
                "compared_methods": [
                    {"name": "", "relationship": "baseline|compare_with|outperform|ablation|other", "evidence": ""}
                ],
                "evidence": "",
                "assets": [],
                "notes": "",
            }
        ],
        "eval_scripts": [{"name": "", "url": ""}],
        "related_work_edges": [{"source": "", "target": "", "reason": ""}],
    }


def load_context_keywords(sections: list[dict[str, Any]], tables: list[dict[str, Any]]) -> list[str]:
    words: list[str] = []
    for table in tables:
        words.extend(str(table.get("caption", "")).lower().split())
    for section in sections:
        words.extend(str(section.get("heading", "")).lower().split())
    return [word.strip(".,:;()[]{}") for word in words if len(word) > 4][:80]


def load_graphics_hints(sections: list[dict[str, Any]]) -> list[str]:
    joined = "\n".join(str(section.get("text", "")) for section in sections)
    refs = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", joined)
    return [Path(ref.strip()).stem.lower() for ref in refs if ref.strip()][:40]


def score_page(text: str, extra_keywords: list[str]) -> int:
    low = text.lower()
    score = sum(low.count(keyword) for keyword in PAGE_KEYWORDS)
    score += sum(1 for keyword in extra_keywords if keyword and keyword in low)
    return score


def extract_source_images(source_root: Path | None, output_dir: Path, graphics_hints: list[str], max_images: int = 12) -> list[dict[str, Any]]:
    if not source_root:
        return []
    try:
        import fitz
    except ImportError:
        return []

    images: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in discover_source_figure_candidates(source_root, graphics_hints):
        key = str(source.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        ext = source.suffix.lower()
        if ext == ".pdf":
            try:
                doc = fitz.open(source)
                if len(doc) < 1:
                    doc.close()
                    continue
                image_path = output_dir / f"source_{source.stem}_page1.png"
                doc[0].get_pixmap(dpi=160, alpha=False).save(image_path)
                doc.close()
                images.append(
                    {
                        "source": "arxiv-source",
                        "kind": "source_pdf_figure",
                        "original": str(source),
                        "image": str(image_path),
                        "name": source.name,
                    }
                )
            except Exception:
                continue
        elif ext in {".png", ".jpg", ".jpeg"}:
            target = output_dir / f"source_{source.name}"
            target.write_bytes(source.read_bytes())
            images.append(
                {
                    "source": "arxiv-source",
                    "kind": "source_image",
                    "original": str(source),
                    "image": str(target),
                    "name": source.name,
                }
            )
        if len(images) >= max_images:
            break
    return images


def extract_assets(
    pdf_path: Path | None,
    source_root: Path | None,
    output_dir: Path,
    sections: list[dict[str, Any]],
    tables: list[dict[str, Any]],
    max_pages: int,
) -> dict[str, Any]:
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    graphics_hints = load_graphics_hints(sections)
    log_step("recover source figures")
    source_images = extract_source_images(source_root, assets_dir, graphics_hints)

    if not pdf_path or not pdf_path.exists():
        return {
            "pdf": None,
            "source_images": source_images,
            "rendered_pages": [],
            "embedded_images": [],
            "note": "No PDF available for page rendering.",
        }

    try:
        import fitz
    except ImportError:
        return {
            "pdf": str(pdf_path),
            "source_images": source_images,
            "rendered_pages": [],
            "embedded_images": [],
            "note": "PyMuPDF is not installed; skipped PDF asset extraction.",
        }

    doc = fitz.open(pdf_path)
    log_step("rank likely experiment pages in PDF")
    extra_keywords = load_context_keywords(sections, tables)
    scored_pages = []
    for index, page in enumerate(doc):
        text = page.get_text()
        scored_pages.append((score_page(text, extra_keywords), index, text[:800]))
    scored_pages.sort(key=lambda item: item[0], reverse=True)
    selected = [item for item in scored_pages if item[0] > 0][:max_pages]
    if not selected:
        selected = scored_pages[: min(max_pages, len(scored_pages))]

    rendered_pages = []
    for rank, (score, index, preview) in enumerate(selected, start=1):
        page = doc[index]
        image_path = assets_dir / f"page_{index + 1:03d}.png"
        page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(image_path)
        rendered_pages.append(
            {
                "rank": rank,
                "page": index + 1,
                "score": score,
                "image": str(image_path),
                "preview": preview,
            }
        )

    embedded_images = []
    for _, index, _ in selected:
        page = doc[index]
        for image_index, image in enumerate(page.get_images(full=True), start=1):
            xref = image[0]
            try:
                extracted = doc.extract_image(xref)
                ext = extracted.get("ext", "png")
                data = extracted["image"]
                path = assets_dir / f"page_{index + 1:03d}_image_{image_index:02d}.{ext}"
                path.write_bytes(data)
                embedded_images.append({"page": index + 1, "image": str(path)})
            except Exception:
                continue

    doc.close()
    return {
        "pdf": str(pdf_path),
        "source_images": source_images,
        "rendered_pages": rendered_pages,
        "embedded_images": embedded_images,
    }


def build_context(paper_id: str | None, pdf: str | None, output_dir: Path, with_assets: bool, max_pages: int) -> dict[str, Any]:
    paper: dict[str, Any]
    raw_text = ""
    source_files: list[dict[str, str]] = []
    source_kind = ""
    pdf_path = Path(pdf).resolve() if pdf else None
    source_root: Path | None = None
    source_dir_value: str | None = None

    if paper_id:
        normalized_id = normalize_arxiv_id(paper_id)
        log_step(f"start single-paper fetch for {normalized_id}")
        paper = parse_abs_metadata(normalized_id) or fallback_metadata(normalized_id)
        source_dir = output_dir / "source"
        source_root = prepare_source_tree(normalized_id, source_dir)
        if source_root:
            log_step("read tex from extracted source")
            raw_text, source_files = read_source_text(source_root)
        if raw_text:
            source_kind = "arxiv_source"
            source_dir_value = str(source_dir.resolve())
        elif not paper.get("title"):
            paper = get_arxiv_metadata(normalized_id) or paper
        if not raw_text and pdf_path is None and paper.get("links", {}).get("pdf"):
            log_step(f"download PDF fallback for {normalized_id}")
            pdf_path = download_arxiv_pdf(normalized_id, output_dir / f"{normalized_id}.pdf", timeout=PDF_TIMEOUT)
    else:
        local_pdf = Path(pdf or "local.pdf")
        paper = {"id": local_pdf.stem, "title": local_pdf.stem, "links": {"pdf": str(local_pdf)}}

    if not raw_text and pdf_path:
        raw_text = read_pdf_text(str(pdf_path))
        source_kind = "pdf"

    if not raw_text:
        raw_text = paper.get("summary", "")
        source_kind = "summary"

    clean_text = clean_for_context(raw_text)
    log_step("extract experiment sections and table snippets")
    sections = find_candidate_sections(clean_text)
    combined_section_text = "\n\n".join(section["text"] for section in sections)
    tables = extract_table_blocks(raw_text) + extract_table_blocks(combined_section_text)
    tables = tables[:16]

    usable_text = source_kind in {"arxiv_source", "pdf"} and len(clean_text.strip()) >= 500
    should_extract_assets = with_assets or not usable_text
    assets = (
        extract_assets(pdf_path, source_root, output_dir, sections, tables, max_pages)
        if should_extract_assets
        else {
            "pdf": str(pdf_path) if pdf_path else None,
            "source_images": [],
            "rendered_pages": [],
            "embedded_images": [],
            "note": "Assets were skipped for fast preparation. Re-run with --with-assets when figures/tables are needed.",
        }
    )
    if source_dir_value:
        assets["source_dir"] = source_dir_value

    return {
        "paper": paper,
        "status": {
            "usable_text": usable_text,
            "text_chars": len(clean_text.strip()),
            "warning": None if usable_text else "No usable paper text was fetched. Do not extract benchmark facts from memory.",
        },
        "source": {
            "kind": source_kind,
            "source_files": source_files,
            "source_dir": source_dir_value,
            "pdf_path": str(pdf_path) if pdf_path else None,
        },
        "sections": sections,
        "tables": tables,
        "assets": assets,
        "agent_task": {
            "instruction": "Read sections, tables, and optional assets. Extract datasets, metrics, protocols, compared methods, evidence, assets, and related-work edges. Do not invent benchmark facts.",
            "schema": extraction_schema(),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch benchmark-focused paper context")
    parser.add_argument("--paper-id", help="arXiv ID")
    parser.add_argument("--pdf", help="Local PDF path")
    parser.add_argument("--config", help="Path to config.yaml")
    parser.add_argument("--output-dir", help="Output directory for context.json and optional assets/")
    parser.add_argument("--with-assets", action="store_true", help="Also recover figures and render likely experiment/result pages")
    parser.add_argument("--max-pages", type=int, default=3, help="Max likely experiment pages to render when assets are enabled")
    args = parser.parse_args()

    if not args.paper_id and not args.pdf:
        parser.error("provide --paper-id or --pdf")

    output_dir = resolve_output_dir(args.output_dir, args.config, args.paper_id, args.pdf)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_step(f"output dir: {output_dir}")
    context = build_context(args.paper_id, args.pdf, output_dir, args.with_assets, args.max_pages)
    output = output_dir / "context.json"
    output.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    log_step(f"wrote context to {output}")


if __name__ == "__main__":
    main()

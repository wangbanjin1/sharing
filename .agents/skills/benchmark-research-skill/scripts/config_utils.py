#!/usr/bin/env python3
"""Internal config helpers for benchmark-arxiv."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


class ConfigError(RuntimeError):
    """Raised when config is missing or invalid."""


@dataclass
class RuntimeConfig:
    config_path: Path
    vault_path: Path
    workspace_dir: str
    papers_dir_name: str
    reports_dir_name: str
    survey_runs_dir_name: str
    enable_collect_links: bool
    language: str = "zh"


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_config_path() -> Path:
    return skill_root() / "config.yaml"


def slugify(value: str) -> str:
    text = re.sub(r"\s+", "-", value.strip().lower())
    text = re.sub(r"[^a-z0-9._-]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "benchmark-run"


def load_runtime_config(config_path: str | None = None) -> RuntimeConfig:
    path = Path(config_path).expanduser().resolve() if config_path else default_config_path()
    if not path.exists():
        raise ConfigError(
            f"Missing config file: {path}. Copy config.example.yaml to config.yaml and set a real vault_path."
        )

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise ConfigError(f"Could not read config {path}: {exc}") from exc

    vault_path_raw = str(data.get("vault_path", "")).strip()
    if not vault_path_raw or vault_path_raw == "/path/to/obsidian-vault":
        raise ConfigError(f"Config {path} must set a real absolute vault_path.")

    vault_path = Path(vault_path_raw).expanduser()
    if not vault_path.is_absolute():
        raise ConfigError(f"vault_path must be absolute: {vault_path_raw}")
    if not vault_path.exists():
        raise ConfigError(f"vault_path does not exist: {vault_path}")

    survey = data.get("benchmark_survey", {}) or {}
    return RuntimeConfig(
        config_path=path,
        vault_path=vault_path,
        workspace_dir=str(survey.get("workspace_dir", "Benchmark_Surveys")).strip() or "Benchmark_Surveys",
        papers_dir_name=str(survey.get("papers_dir_name", "papers")).strip() or "papers",
        reports_dir_name=str(survey.get("reports_dir_name", "reports")).strip() or "reports",
        survey_runs_dir_name=str(survey.get("survey_runs_dir_name", "surveys")).strip() or "surveys",
        enable_collect_links=bool(survey.get("enable_collect_links", False)),
        language=str(data.get("language", "zh")).strip() or "zh",
    )


def workspace_root(config: RuntimeConfig) -> Path:
    return config.vault_path / config.workspace_dir


def build_single_paper_dir(config: RuntimeConfig, paper_key: str) -> Path:
    return workspace_root(config) / config.papers_dir_name / slugify(paper_key)


def build_single_report_path(config: RuntimeConfig, paper_key: str) -> Path:
    return workspace_root(config) / config.reports_dir_name / f"{slugify(paper_key)}.md"


def build_survey_run_dir(config: RuntimeConfig, topic: str, date: str | None = None) -> Path:
    date_prefix = date or datetime.now().strftime("%Y-%m-%d")
    return workspace_root(config) / config.survey_runs_dir_name / f"{date_prefix}-{slugify(topic)}"


def build_survey_report_path(config: RuntimeConfig, topic: str, date: str | None = None) -> Path:
    run_dir = build_survey_run_dir(config, topic, date=date)
    return run_dir / config.reports_dir_name / "benchmark-survey.md"

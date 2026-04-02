from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


_SAFE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9._+\-]+")


def sanitize_component(value: str | None, default: str) -> str:
    """Return a safe single path component."""
    if not value:
        return default

    sanitized = _SAFE_COMPONENT_RE.sub("-", value.strip())
    sanitized = sanitized.strip(".-_+")
    return sanitized or default


def resolve_run_id(run_id: str | None = None, run_label: str | None = None) -> str:
    """Return a canonical run directory name under experiments/results/."""
    explicit_run_id = run_id or os.environ.get("ABR_RUN_ID")
    if explicit_run_id:
        return sanitize_component(explicit_run_id, "run")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    label = sanitize_component(run_label or os.environ.get("ABR_RUN_LABEL"), "")
    if label:
        return f"{timestamp}-{label}"
    return timestamp


@dataclass(frozen=True)
class RunLayout:
    run_id: str
    run_root: Path
    raw_root: Path
    analysis_root: Path
    logs_root: Path


def build_run_layout(
    repo_root: Path,
    *,
    run_id: str | None = None,
    run_label: str | None = None,
) -> RunLayout:
    resolved_run_id = resolve_run_id(run_id=run_id, run_label=run_label)
    run_root = repo_root / "experiments" / "results" / resolved_run_id
    return RunLayout(
        run_id=resolved_run_id,
        run_root=run_root,
        raw_root=run_root / "raw",
        analysis_root=run_root / "analysis",
        logs_root=run_root / "logs",
    )


def build_eoh_output_root(
    repo_root: Path,
    *,
    output_name: str | None,
    run_id: str | None = None,
    run_label: str | None = None,
) -> Path:
    layout = build_run_layout(repo_root, run_id=run_id, run_label=run_label)
    return layout.raw_root / "eoh" / sanitize_component(output_name, "eoh")


def build_analysis_csv_path(
    repo_root: Path,
    *,
    run_id: str | None = None,
    run_label: str | None = None,
) -> Path:
    layout = build_run_layout(repo_root, run_id=run_id, run_label=run_label)
    return layout.analysis_root / "results_summary.csv"


def build_plots_dir(
    repo_root: Path,
    *,
    run_id: str | None = None,
    run_label: str | None = None,
) -> Path:
    layout = build_run_layout(repo_root, run_id=run_id, run_label=run_label)
    return layout.analysis_root / "plots"


def build_eval_logs_root(
    repo_root: Path,
    *,
    run_id: str | None = None,
    run_label: str | None = None,
) -> Path:
    layout = build_run_layout(repo_root, run_id=run_id, run_label=run_label)
    return layout.raw_root / "eval_logs"


def build_eval_log_dir(
    repo_root: Path,
    *,
    dataset: str,
    run_id: str | None = None,
    run_label: str | None = None,
) -> Path:
    eval_logs_root = build_eval_logs_root(
        repo_root,
        run_id=run_id,
        run_label=run_label,
    )
    return eval_logs_root / sanitize_component(dataset, "dataset")


def build_run_report_path(
    repo_root: Path,
    *,
    run_id: str | None = None,
    run_label: str | None = None,
) -> Path:
    layout = build_run_layout(repo_root, run_id=run_id, run_label=run_label)
    return layout.analysis_root / "run_report.md"


def build_log_path(
    repo_root: Path,
    *,
    log_name: str,
    run_id: str | None = None,
    run_label: str | None = None,
) -> Path:
    layout = build_run_layout(repo_root, run_id=run_id, run_label=run_label)
    return layout.logs_root / f"{sanitize_component(log_name, 'log')}.log"


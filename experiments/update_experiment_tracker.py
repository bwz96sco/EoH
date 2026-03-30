#!/usr/bin/env python3
"""Generate a human-readable tracker for canonical experiment runs."""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

from run_layout import build_experiment_tracker_path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
RESULTS_ROOT = REPO_ROOT / "experiments" / "results"

RUN_ID_TIMESTAMP_RE = re.compile(r"^(?P<date>\d{4})(?P<month>\d{2})(?P<day>\d{2})-(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})(?:-.+)?$")
POPULATION_GENERATION_RE = re.compile(r"population_generation_(\d+)\.json$")

BASELINE_SCHEMES = ["sim_bb", "sim_bola", "sim_quetra", "sim_rmpc", "sim_bs", "sim_mfd"]
ONLINE_SCHEMES = ["sim_bb", "sim_bola", "sim_quetra", "sim_rmpc"]
SCHEME_LABELS = {
    "sim_bb": "BB",
    "sim_bola": "BOLA",
    "sim_quetra": "QUETRA",
    "sim_rmpc": "RobustMPC",
    "sim_bs": "BeamSearch",
    "sim_mfd": "MFD",
    "sim_eoh": "EoH",
}
SUITE_ROWS = ["ABRBench-3G (avg)", "ABRBench-4G+ (avg)", "Overall (avg)"]
DISPLAY_TARGET_NAMES = {
    "ABRBench-4G": "ABRBench-4G+",
}
PHASE_DEFINITIONS = [
    ("PHASE 1", "Phase 1 (EoH Evolution)"),
    ("PHASE 2", "Phase 2 (SABR Rule-Based Baselines)"),
    ("PHASE 3", "Phase 3 (EoH Heuristic Evaluation)"),
    ("PHASE 4", "Phase 4 (Analysis)"),
]


@dataclass(frozen=True)
class HeuristicSnapshot:
    target: str
    generation: int
    algorithm: str | None
    objective: float | None
    path: Path


@dataclass(frozen=True)
class EohConfigSummary:
    target: str
    model: str | None
    endpoint: str | None
    use_local: bool | None
    pop_size: int | None
    n_pop: int | None
    operators: list[str]
    n_proc: int | None
    timeout: int | None
    seed_mode: str
    config_path: Path


@dataclass(frozen=True)
class SuiteSummary:
    row_name: str
    eoh_value: float | None
    best_online_label: str | None
    best_online_value: float | None
    best_overall_label: str | None
    best_overall_value: float | None


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    run_root: Path
    status: str
    started_at: str
    scope: list[str]
    abstract: str
    phase_status: dict[str, str]
    configs: list[EohConfigSummary]
    primary_summaries: list[SuiteSummary]
    suite_summaries: list[SuiteSummary]
    summary_csv: Path | None
    report_path: Path | None
    log_path: Path | None
    plots_dir: Path | None
    heuristic_snapshots: list[HeuristicSnapshot]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update canonical experiment tracker")
    parser.add_argument(
        "--run-id",
        action="append",
        default=[],
        help="Restrict update to specific run-id values. By default, scan all canonical runs.",
    )
    return parser.parse_args()


def parse_run_started_at(run_id: str, run_root: Path) -> str:
    match = RUN_ID_TIMESTAMP_RE.match(run_id)
    if match:
        return (
            f"{match.group('date')}-{match.group('month')}-{match.group('day')} "
            f"{match.group('hour')}:{match.group('minute')}:{match.group('second')}"
        )
    return "unknown"


def read_json(path: Path) -> dict | None:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def clean_algorithm_description(value: str | None, *, max_len: int = 160) -> str | None:
    if not value:
        return None

    cleaned = " ".join(value.strip().strip("{}").split())
    if not cleaned:
        return None
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3].rstrip() + "..."


def display_target_name(value: str) -> str:
    return DISPLAY_TARGET_NAMES.get(value, value)


def format_path_for_markdown(path_value: str) -> str:
    path = Path(path_value)
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return path_value


def find_best_population(target_dir: Path) -> HeuristicSnapshot | None:
    population_files = sorted(
        target_dir.glob("*/results/pops_best/population_generation_*.json"),
    )
    best_path: Path | None = None
    best_generation = -1
    for path in population_files:
        match = POPULATION_GENERATION_RE.search(path.name)
        if not match:
            continue
        generation = int(match.group(1))
        if generation >= best_generation:
            best_generation = generation
            best_path = path

    if best_path is None:
        return None

    payload = read_json(best_path)
    algorithm = None
    objective = None
    if isinstance(payload, dict):
        algorithm = clean_algorithm_description(payload.get("algorithm"))
        objective = payload.get("objective")
        if not isinstance(objective, (int, float)):
            objective = None

    return HeuristicSnapshot(
        target=display_target_name(target_dir.name),
        generation=best_generation,
        algorithm=algorithm,
        objective=float(objective) if objective is not None else None,
        path=best_path,
    )


def summarize_seed_mode(config: dict) -> str:
    if config.get("exp_use_continue"):
        continue_path = str(config.get("exp_continue_path", "")).strip()
        if continue_path:
            return f"continue from `{format_path_for_markdown(continue_path)}`"
        return "continue from existing population"

    if config.get("exp_use_seed"):
        seed_path = str(config.get("exp_seed_path", "")).strip()
        if seed_path:
            if seed_path.startswith("/var/") or seed_path.startswith("/tmp/"):
                return "use generated temp seed file"
            return f"use seed file `{format_path_for_markdown(seed_path)}`"
        return "use seed file"

    return "fresh population"


def load_configs(run_root: Path) -> list[EohConfigSummary]:
    raw_eoh_root = run_root / "raw" / "eoh"
    if not raw_eoh_root.is_dir():
        return []

    configs: list[EohConfigSummary] = []
    for target_dir in sorted(path for path in raw_eoh_root.iterdir() if path.is_dir()):
        config_paths = sorted(target_dir.glob("*/config.json"))
        for config_path in config_paths:
            payload = read_json(config_path)
            if not isinstance(payload, dict):
                continue
            operators = payload.get("ec_operators")
            configs.append(
                EohConfigSummary(
                    target=display_target_name(target_dir.name),
                    model=payload.get("llm_model"),
                    endpoint=payload.get("llm_api_endpoint"),
                    use_local=payload.get("llm_use_local"),
                    pop_size=payload.get("ec_pop_size"),
                    n_pop=payload.get("ec_n_pop"),
                    operators=operators if isinstance(operators, list) else [],
                    n_proc=payload.get("exp_n_proc"),
                    timeout=payload.get("eva_timeout"),
                    seed_mode=summarize_seed_mode(payload),
                    config_path=config_path,
                )
            )
    return configs


def load_phase_status(log_path: Path | None) -> dict[str, str]:
    phases = {display_label: "unknown" for _, display_label in PHASE_DEFINITIONS}
    if log_path is None or not log_path.is_file():
        return phases

    try:
        content = log_path.read_text()
    except Exception:
        return phases

    for raw_label, display_label in PHASE_DEFINITIONS:
        skipped_marker = f"{raw_label}: SKIPPED"
        normal_marker = f"{raw_label}:"
        if skipped_marker in content:
            phases[display_label] = "skipped"
        elif normal_marker in content:
            phases[display_label] = "ran"
    return phases


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if not value or value == "-":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def select_best_baseline(
    row: dict[str, str],
    schemes: list[str],
) -> tuple[str | None, float | None]:
    best_label = None
    best_value = None
    for scheme in schemes:
        value = parse_float(row.get(scheme))
        if value is None:
            continue
        if best_value is None or value > best_value:
            best_value = value
            best_label = SCHEME_LABELS[scheme]
    return best_label, best_value


def build_suite_summary(row_name: str, row: dict[str, str]) -> SuiteSummary:
    best_online_label, best_online_value = select_best_baseline(row, ONLINE_SCHEMES)
    best_overall_label, best_overall_value = select_best_baseline(row, BASELINE_SCHEMES)
    return SuiteSummary(
        row_name=row_name,
        eoh_value=parse_float(row.get("sim_eoh")),
        best_online_label=best_online_label,
        best_online_value=best_online_value,
        best_overall_label=best_overall_label,
        best_overall_value=best_overall_value,
    )


def load_suite_summaries(summary_csv: Path | None) -> list[SuiteSummary]:
    if summary_csv is None or not summary_csv.is_file():
        return []

    rows: dict[str, dict[str, str]] = {}
    with open(summary_csv, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dataset = row.get("Dataset")
            if dataset:
                rows[dataset] = row

    summaries: list[SuiteSummary] = []
    for row_name in SUITE_ROWS:
        row = rows.get(row_name)
        if row is None:
            continue

        summaries.append(build_suite_summary(row_name, row))
    return summaries


def load_summary_rows(summary_csv: Path | None) -> dict[str, SuiteSummary]:
    if summary_csv is None or not summary_csv.is_file():
        return {}

    rows: dict[str, dict[str, str]] = {}
    with open(summary_csv, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dataset = row.get("Dataset")
            if dataset:
                rows[dataset] = row

    summaries: dict[str, SuiteSummary] = {}
    for row_name, row in rows.items():
        summaries[row_name] = build_suite_summary(row_name, row)
    return summaries


def determine_status(summary_csv: Path | None, configs: list[EohConfigSummary], log_path: Path | None) -> str:
    if summary_csv is not None and summary_csv.is_file():
        return "completed"
    if configs or (log_path is not None and log_path.is_file()):
        return "partial"
    return "empty"


def build_scope(configs: list[EohConfigSummary]) -> list[str]:
    unique_targets = []
    for config in configs:
        if config.target not in unique_targets:
            unique_targets.append(config.target)
    return unique_targets


def primary_row_name_for_scope_item(scope_item: str) -> str:
    if scope_item == "ABRBench-3G":
        return "ABRBench-3G (avg)"
    if scope_item == "ABRBench-4G+":
        return "ABRBench-4G+ (avg)"
    return scope_item


def select_primary_summaries(
    scope: list[str],
    summary_rows: dict[str, SuiteSummary],
) -> list[SuiteSummary]:
    selected: list[SuiteSummary] = []
    for scope_item in scope:
        row_name = primary_row_name_for_scope_item(scope_item)
        summary = summary_rows.get(row_name)
        if summary is not None:
            selected.append(summary)

    if selected:
        return selected

    overall = summary_rows.get("Overall (avg)")
    if overall is not None:
        return [overall]
    return []


def build_abstract(scope: list[str], configs: list[EohConfigSummary], phase_status: dict[str, str], status: str) -> str:
    scope_text = ", ".join(f"`{scope_item}`" for scope_item in scope) if scope else "no discovered raw EoH targets"
    models = sorted({config.model for config in configs if config.model})
    model_text = ", ".join(f"`{model}`" for model in models) if models else "unknown model"

    baseline_phase_label = "Phase 2 (SABR Rule-Based Baselines)"
    if phase_status.get(baseline_phase_label) == "skipped":
        baseline_text = "Baseline phase was skipped, so baseline numbers are reused from existing SABR logs."
    elif phase_status.get(baseline_phase_label) == "ran":
        baseline_text = "Baseline phase ran inside the canonical workflow."
    else:
        baseline_text = "Baseline provenance is unknown from the available artifacts."

    return (
        f"ABR experiment run over {scope_text} using EoH model(s) {model_text}. "
        f"Run status is `{status}`. {baseline_text}"
    )


def discover_run_record(run_root: Path) -> RunRecord:
    run_id = run_root.name
    summary_csv = run_root / "analysis" / "results_summary.csv"
    report_path = run_root / "analysis" / "run_report.md"
    log_path = run_root / "logs" / "full_pipeline.log"
    plots_dir = run_root / "analysis" / "plots"

    configs = load_configs(run_root)
    phase_status = load_phase_status(log_path if log_path.is_file() else None)
    scope = build_scope(configs)
    summary_rows = load_summary_rows(summary_csv if summary_csv.is_file() else None)
    primary_summaries = select_primary_summaries(scope, summary_rows)
    suite_summaries = load_suite_summaries(summary_csv if summary_csv.is_file() else None)
    status = determine_status(summary_csv if summary_csv.is_file() else None, configs, log_path if log_path.is_file() else None)
    abstract = build_abstract(scope, configs, phase_status, status)

    heuristic_snapshots = []
    raw_eoh_root = run_root / "raw" / "eoh"
    if raw_eoh_root.is_dir():
        for target_dir in sorted(path for path in raw_eoh_root.iterdir() if path.is_dir()):
            snapshot = find_best_population(target_dir)
            if snapshot is not None:
                heuristic_snapshots.append(snapshot)

    return RunRecord(
        run_id=run_id,
        run_root=run_root,
        status=status,
        started_at=parse_run_started_at(run_id, run_root),
        scope=scope,
        abstract=abstract,
        phase_status=phase_status,
        configs=configs,
        primary_summaries=primary_summaries,
        suite_summaries=suite_summaries,
        summary_csv=summary_csv if summary_csv.is_file() else None,
        report_path=report_path if report_path.is_file() else None,
        log_path=log_path if log_path.is_file() else None,
        plots_dir=plots_dir if plots_dir.is_dir() else None,
        heuristic_snapshots=heuristic_snapshots,
    )


def format_suite_summary(summary: SuiteSummary) -> str:
    if summary.eoh_value is None:
        return f"- `{summary.row_name}`: EoH result unavailable"

    parts = [f"`EoH = {summary.eoh_value:.4f}`"]
    if summary.best_online_label is not None and summary.best_online_value is not None:
        parts.append(
            f"best online `{summary.best_online_label} = {summary.best_online_value:.4f}`"
        )
    if summary.best_overall_label is not None and summary.best_overall_value is not None:
        parts.append(
            f"best overall `{summary.best_overall_label} = {summary.best_overall_value:.4f}`"
        )

    return f"- `{summary.row_name}`: " + ", ".join(parts)


def format_config(config: EohConfigSummary) -> str:
    transport = "local" if config.use_local else "remote"
    operators = ", ".join(config.operators) if config.operators else "unknown"
    return (
        f"- `{config.target}`: model `{config.model or 'unknown'}` via {transport} "
        f"`{config.endpoint or 'unknown'}`, `ec_pop_size={config.pop_size}`, "
        f"`ec_n_pop={config.n_pop}`, `exp_n_proc={config.n_proc}`, "
        f"`eva_timeout={config.timeout}`, operators `{operators}`, {config.seed_mode}; "
        f"config `{config.config_path.relative_to(REPO_ROOT)}`"
    )


def format_phase_status(phase_status: dict[str, str]) -> list[str]:
    ordered = []
    for _, label in PHASE_DEFINITIONS:
        ordered.append(f"- `{label}`: `{phase_status.get(label, 'unknown')}`")
    return ordered


def format_heuristic_snapshot(snapshot: HeuristicSnapshot) -> str:
    details = f"generation `{snapshot.generation}`"
    if snapshot.objective is not None:
        details += f", stored objective `{snapshot.objective:.5f}`"
    if snapshot.algorithm:
        details += f", algorithm `{snapshot.algorithm}`"
    return f"- `{snapshot.target}`: {details}; file `{snapshot.path.relative_to(REPO_ROOT)}`"


def build_table_row(record: RunRecord) -> str:
    models = ", ".join(sorted({config.model for config in record.configs if config.model})) or "unknown"
    scope = ", ".join(record.scope) if record.scope else "-"
    result_parts = []
    for summary in record.primary_summaries:
        if summary.eoh_value is None:
            continue

        label = summary.row_name.removesuffix(" (avg)")
        summary_parts = [f"{label}: EoH {summary.eoh_value:.1f}"]
        if summary.best_online_label and summary.best_online_value is not None:
            summary_parts.append(
                f"online {summary.best_online_label} {summary.best_online_value:.1f}"
            )
        if summary.best_overall_label and summary.best_overall_value is not None:
            summary_parts.append(
                f"overall {summary.best_overall_label} {summary.best_overall_value:.1f}"
            )
        result_parts.append(" vs ".join(summary_parts))

    result = "; ".join(result_parts) if result_parts else "analysis pending"
    return f"| `{record.run_id}` | `{record.status}` | {models} | {scope} | {result} |"


def render_tracker(records: list[RunRecord]) -> str:
    lines = [
        "# Experiment Tracker",
        "",
        "> Auto-generated by `experiments/update_experiment_tracker.py`. ",
        "> It summarizes canonical runs currently present under `experiments/results/`.",
        "",
        f"Tracked runs: `{len(records)}`",
        "",
        "## Summary Table",
        "",
        "| Run ID | Status | Models | Scope | Primary Comparison (Online / Overall) |",
        "| --- | --- | --- | --- | --- |",
    ]

    if records:
        for record in records:
            lines.append(build_table_row(record))
    else:
        lines.append("| - | - | - | - | no canonical runs found |")

    lines.extend(["", "## Detailed Records", ""])

    if not records:
        lines.append("No canonical experiment runs were found under `experiments/results/`.")
        lines.append("")
        return "\n".join(lines)

    for record in records:
        lines.append(f"### `{record.run_id}`")
        lines.append("")
        lines.append(f"- Status: `{record.status}`")
        lines.append(f"- Started at: `{record.started_at}`")
        lines.append(f"- Run root: `{record.run_root.relative_to(REPO_ROOT)}`")
        lines.append(f"- Abstract: {record.abstract}")

        if record.summary_csv is not None:
            lines.append(f"- Summary CSV: `{record.summary_csv.relative_to(REPO_ROOT)}`")
        if record.plots_dir is not None:
            lines.append(f"- Plots directory: `{record.plots_dir.relative_to(REPO_ROOT)}`")
        if record.report_path is not None:
            lines.append(f"- Run report: `{record.report_path.relative_to(REPO_ROOT)}`")
        if record.log_path is not None:
            lines.append(f"- Pipeline log: `{record.log_path.relative_to(REPO_ROOT)}`")

        lines.append("- Phase record:")
        lines.extend(format_phase_status(record.phase_status))

        if record.configs:
            lines.append("- Models and key parameters:")
            lines.extend(format_config(config) for config in record.configs)
        else:
            lines.append("- Models and key parameters: unavailable")

        if record.suite_summaries:
            lines.append("- Short result record:")
            lines.extend(format_suite_summary(summary) for summary in record.suite_summaries)
        else:
            lines.append("- Short result record: analysis not available")

        if record.primary_summaries:
            lines.append("- Primary comparison focus:")
            lines.extend(format_suite_summary(summary) for summary in record.primary_summaries)

        if record.heuristic_snapshots:
            lines.append("- Best heuristic snapshots:")
            lines.extend(format_heuristic_snapshot(snapshot) for snapshot in record.heuristic_snapshots)

        lines.append("")

    return "\n".join(lines)


def collect_run_roots(selected_run_ids: list[str]) -> list[Path]:
    if not RESULTS_ROOT.exists():
        return []

    if selected_run_ids:
        run_roots = [RESULTS_ROOT / run_id for run_id in selected_run_ids]
        return [run_root for run_root in run_roots if run_root.is_dir() and not run_root.name.startswith("_")]

    return sorted(
        (path for path in RESULTS_ROOT.iterdir() if path.is_dir() and not path.name.startswith("_")),
        key=lambda path: path.name,
        reverse=True,
    )


def main() -> None:
    args = parse_args()
    run_roots = collect_run_roots(args.run_id)
    records = [discover_run_record(run_root) for run_root in run_roots]
    tracker_path = build_experiment_tracker_path(REPO_ROOT)
    tracker_path.parent.mkdir(parents=True, exist_ok=True)
    tracker_path.write_text(render_tracker(records))
    print(f"Experiment tracker saved to {tracker_path}")


if __name__ == "__main__":
    main()

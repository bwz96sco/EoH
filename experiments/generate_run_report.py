#!/usr/bin/env python3
"""Generate a per-run markdown report for a canonical ABR experiment."""

from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from pathlib import Path

from run_layout import build_run_report_path
from update_experiment_tracker import (
    BASELINE_SCHEMES,
    PHASE_DEFINITIONS,
    SCHEME_LABELS,
    SUITE_ROWS,
    RunRecord,
    discover_run_record,
    format_config,
    format_heuristic_snapshot,
)


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
RESULTS_ROOT = REPO_ROOT / "experiments" / "results"


@dataclass(frozen=True)
class DatasetInsight:
    dataset: str
    eoh_value: float
    best_scheme: str
    best_value: float
    eoh_rank: int
    gap_to_best: float
    beat_counts: dict[str, bool]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a canonical ABR run report")
    parser.add_argument(
        "--run-id",
        default=os.environ.get("ABR_RUN_ID"),
        help="Canonical run id under experiments/results/ (or set ABR_RUN_ID)",
    )
    return parser.parse_args()


def load_dataset_insights(summary_csv: Path | None) -> list[DatasetInsight]:
    if summary_csv is None or not summary_csv.is_file():
        return []

    insights: list[DatasetInsight] = []
    with open(summary_csv, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dataset = row.get("Dataset")
            if not dataset or dataset in SUITE_ROWS:
                continue

            values: dict[str, float] = {}
            for scheme in SCHEME_LABELS:
                raw_value = row.get(scheme, "").strip()
                if not raw_value or raw_value == "-":
                    continue
                try:
                    values[scheme] = float(raw_value)
                except ValueError:
                    continue

            eoh_value = values.get("sim_eoh")
            if eoh_value is None:
                continue

            ordered = sorted(values.items(), key=lambda item: item[1], reverse=True)
            best_scheme, best_value = ordered[0]
            eoh_rank = 1 + sum(1 for _, value in ordered if value > eoh_value)
            beat_counts = {
                scheme: eoh_value > values[scheme]
                for scheme in BASELINE_SCHEMES
                if scheme in values
            }

            insights.append(
                DatasetInsight(
                    dataset=dataset,
                    eoh_value=eoh_value,
                    best_scheme=best_scheme,
                    best_value=best_value,
                    eoh_rank=eoh_rank,
                    gap_to_best=eoh_value - best_value,
                    beat_counts=beat_counts,
                )
            )

    return insights


def format_path(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def build_suite_summary_table(record: RunRecord) -> list[str]:
    if not record.suite_summaries:
        return ["Suite summary unavailable."]

    lines = [
        "| Suite | EoH | Best Baseline | Gap To Best Baseline |",
        "| --- | ---: | ---: | ---: |",
    ]
    for summary in record.suite_summaries:
        if summary.eoh_value is None:
            lines.append(f"| {summary.row_name} | - | - | - |")
            continue

        if summary.best_baseline_label is None or summary.best_baseline_value is None:
            lines.append(f"| {summary.row_name} | {summary.eoh_value:.4f} | - | - |")
            continue

        gap = summary.eoh_value - summary.best_baseline_value
        lines.append(
            f"| {summary.row_name} | {summary.eoh_value:.4f} | "
            f"{summary.best_baseline_label} = {summary.best_baseline_value:.4f} | "
            f"{gap:.4f} |"
        )
    return lines


def build_dataset_highlights(insights: list[DatasetInsight]) -> list[str]:
    if not insights:
        return ["Dataset-level summary unavailable."]

    total = len(insights)
    wins = [item for item in insights if item.best_scheme == "sim_eoh"]
    best_dataset = max(insights, key=lambda item: item.eoh_value)
    worst_dataset = min(insights, key=lambda item: item.eoh_value)
    largest_gap_dataset = min(insights, key=lambda item: item.gap_to_best)
    closest_non_win = max(
        (item for item in insights if item.best_scheme != "sim_eoh"),
        key=lambda item: item.gap_to_best,
        default=None,
    )

    beat_summaries = []
    for scheme in BASELINE_SCHEMES:
        wins_against_scheme = sum(1 for item in insights if item.beat_counts.get(scheme, False))
        beat_summaries.append(f"`{SCHEME_LABELS[scheme]}` on `{wins_against_scheme}/{total}` datasets")

    lines = [
        f"- EoH ranked first on `{len(wins)}/{total}` datasets.",
        f"- Best EoH dataset: `{best_dataset.dataset}` with `QoE = {best_dataset.eoh_value:.4f}`.",
        f"- Worst EoH dataset: `{worst_dataset.dataset}` with `QoE = {worst_dataset.eoh_value:.4f}`.",
        (
            f"- Largest deficit to the dataset winner was on `{largest_gap_dataset.dataset}`: "
            f"`gap = {largest_gap_dataset.gap_to_best:.4f}` vs "
            f"`{SCHEME_LABELS[largest_gap_dataset.best_scheme]} = {largest_gap_dataset.best_value:.4f}`."
        ),
    ]

    if closest_non_win is not None:
        lines.append(
            f"- Closest non-winning dataset was `{closest_non_win.dataset}`: "
            f"`EoH = {closest_non_win.eoh_value:.4f}`, "
            f"best `{SCHEME_LABELS[closest_non_win.best_scheme]} = {closest_non_win.best_value:.4f}`."
        )

    if wins:
        win_text = ", ".join(f"`{item.dataset}`" for item in wins)
        lines.append(f"- Datasets won by EoH: {win_text}.")

    lines.append(f"- EoH beat {', '.join(beat_summaries)}.")
    return lines


def render_report(record: RunRecord) -> str:
    report_path = build_run_report_path(REPO_ROOT, run_id=record.run_id)
    dataset_insights = load_dataset_insights(record.summary_csv)

    lines = [
        "# ABR Experiment Report",
        "",
        f"Run id: `{record.run_id}`",
        "",
        f"Status: `{record.status}`",
        f"Started at: `{record.started_at}`",
        f"Abstract: {record.abstract}",
        "",
        "## Artifacts",
        "",
        f"- Run root: `{format_path(record.run_root)}`",
    ]

    if record.summary_csv is not None:
        lines.append(f"- Summary CSV: `{format_path(record.summary_csv)}`")
    if record.plots_dir is not None:
        lines.append(f"- Plots directory: `{format_path(record.plots_dir)}`")
    if record.log_path is not None:
        lines.append(f"- Pipeline log: `{format_path(record.log_path)}`")
    lines.append(f"- Report path: `{format_path(report_path)}`")

    lines.extend(["", "## Phase Record", ""])
    for _, label in PHASE_DEFINITIONS:
        lines.append(f"- `{label}`: `{record.phase_status.get(label, 'unknown')}`")

    lines.extend(["", "## Models And Parameters", ""])
    if record.configs:
        lines.extend(format_config(config) for config in record.configs)
    else:
        lines.append("- Config details unavailable.")

    lines.extend(["", "## Suite Summary", ""])
    lines.extend(build_suite_summary_table(record))

    lines.extend(["", "## Dataset Highlights", ""])
    lines.extend(build_dataset_highlights(dataset_insights))

    lines.extend(["", "## Best Heuristic Snapshots", ""])
    if record.heuristic_snapshots:
        lines.extend(format_heuristic_snapshot(snapshot) for snapshot in record.heuristic_snapshots)
    else:
        lines.append("- Best heuristic snapshots unavailable.")

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    if not args.run_id:
        raise SystemExit("--run-id or ABR_RUN_ID is required")

    run_root = RESULTS_ROOT / args.run_id
    if not run_root.is_dir():
        raise SystemExit(f"Canonical run root not found: {run_root}")

    record = discover_run_record(run_root)
    report_path = build_run_report_path(REPO_ROOT, run_id=args.run_id)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(record))
    print(f"Run report saved to {report_path}")


if __name__ == "__main__":
    main()

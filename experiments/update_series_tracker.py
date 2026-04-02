#!/usr/bin/env python3
"""Generate or update a campaign tracker for a group of related experiments.

Reads results_summary.csv from each run directory, extracts key metrics,
and generates a markdown tracker under experiments/campaigns/<name>.md.

Preserves manually-written Analysis and Next Steps sections on update.

In this repo, one campaign may contain multiple experiment runs that all
serve the same research objective.

Usage:
    python3 experiments/update_series_tracker.py \\
        --name "3g-improve-round1" \\
        --objective "Improve 3G QoE beyond baseline 87.0" \\
        --baseline "87.0 (Quetra seed, seed-impact study)" \\
        --metric "ABRBench-3G (avg)" \\
        --run /path/to/run-dir:LabelForThisRun \\
        --run /path/to/another-run:AnotherLabel

    # Update existing tracker (adds/refreshes data, keeps Analysis/Next Steps):
    python3 experiments/update_series_tracker.py \\
        --name "3g-improve-round1" \\
        --run /path/to/new-run:NewLabel
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
CAMPAIGNS_DIR = SCRIPT_DIR / "campaigns"

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

# Datasets in display order
DATASETS_3G = ["FCC-16", "FCC-18", "Oboe", "Puffer-21", "Puffer-22", "HSR"]
DATASETS_4G = ["Norway3G", "Lumos4G", "Lumos5G", "SolisWi-Fi", "Ghent", "Lab"]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class RunData:
    label: str
    run_dir: Path
    run_id: str = ""
    eoh_value: float | None = None
    baseline_ref: float | None = None  # e.g., RobustMPC for metric row
    per_dataset: dict[str, float | None] = field(default_factory=dict)
    config_summary: str = ""


# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------

def parse_results_csv(csv_path: Path) -> dict[str, dict[str, float | None]]:
    """Parse results_summary.csv → {row_name: {scheme: value}}."""
    if not csv_path.is_file():
        return {}

    rows: dict[str, dict[str, float | None]] = {}
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ds = row.get("Dataset", "").strip()
            if not ds:
                continue
            values: dict[str, float | None] = {}
            for scheme in list(SCHEME_LABELS.keys()):
                raw = row.get(scheme, "").strip()
                if raw and raw != "-":
                    try:
                        values[scheme] = float(raw)
                    except ValueError:
                        values[scheme] = None
                else:
                    values[scheme] = None
            rows[ds] = values
    return rows


def extract_run_id(run_dir: Path) -> str:
    """Extract run ID from directory name or nested structure."""
    name = run_dir.name
    # Direct run dir: experiments/results/<run-id>
    if re.match(r"\d{8}-\d{6}", name):
        return name
    # Maybe a checkout root — look for results subdirs
    results_dir = run_dir / "experiments" / "results"
    if results_dir.is_dir():
        candidates = sorted(
            [d.name for d in results_dir.iterdir() if d.is_dir() and re.match(r"\d{8}-\d{6}", d.name)],
            reverse=True,
        )
        if candidates:
            return candidates[0]
    return name


def find_csv(run_dir: Path) -> Path | None:
    """Find results_summary.csv in a run directory or checkout."""
    # Direct: run_dir/analysis/results_summary.csv
    direct = run_dir / "analysis" / "results_summary.csv"
    if direct.is_file():
        return direct

    # Checkout: run_dir/experiments/results/<run-id>/analysis/results_summary.csv
    results_dir = run_dir / "experiments" / "results"
    if results_dir.is_dir():
        for d in sorted(results_dir.iterdir(), reverse=True):
            candidate = d / "analysis" / "results_summary.csv"
            if candidate.is_file():
                return candidate

    return None


def extract_config_summary(run_dir: Path) -> str:
    """Extract a short config summary from EoH config.json."""
    # Look for config.json in raw/eoh/*/eoh_*/config.json
    patterns = [
        run_dir / "raw" / "eoh",
        run_dir / "experiments" / "results",
    ]
    for base in patterns:
        if not base.is_dir():
            continue
        for config_path in base.rglob("config.json"):
            try:
                with open(config_path) as f:
                    cfg = json.load(f)
                parts = []
                if "llm_model" in cfg:
                    parts.append(cfg["llm_model"])
                if "ec_pop_size" in cfg:
                    parts.append(f"pop={cfg['ec_pop_size']}")
                if "ec_n_pop" in cfg:
                    parts.append(f"gen={cfg['ec_n_pop']}")
                return ", ".join(parts) if parts else ""
            except (json.JSONDecodeError, OSError):
                continue
    return ""


def load_run(run_dir: Path, label: str, metric_row: str) -> RunData:
    """Load data for a single run."""
    csv_path = find_csv(run_dir)
    run_id = extract_run_id(run_dir)
    config_summary = extract_config_summary(run_dir)

    data = RunData(
        label=label,
        run_dir=run_dir,
        run_id=run_id,
        config_summary=config_summary,
    )

    if csv_path is None:
        print(f"  WARNING: no CSV found for {run_dir}", file=sys.stderr)
        return data

    rows = parse_results_csv(csv_path)

    # Extract EoH value for the metric row
    metric_data = rows.get(metric_row, {})
    data.eoh_value = metric_data.get("sim_eoh")
    data.baseline_ref = metric_data.get("sim_rmpc")

    # Extract per-dataset breakdown
    all_datasets = DATASETS_3G + DATASETS_4G
    for ds in all_datasets:
        ds_data = rows.get(ds, {})
        val = ds_data.get("sim_eoh")
        if val is not None:
            data.per_dataset[ds] = val

    return data


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

def _fmt(val: float | None, precision: int = 1) -> str:
    if val is None:
        return "-"
    return f"{val:.{precision}f}"


def generate_tracker_md(
    name: str,
    objective: str,
    baseline_desc: str,
    metric_row: str,
    runs: list[RunData],
    existing_analysis: str,
    existing_next_steps: str,
) -> str:
    """Generate the full series tracker markdown."""
    lines: list[str] = []

    # Header
    lines.append(f"# Series: {name}")
    lines.append("")
    lines.append("> Auto-generated data by `experiments/update_series_tracker.py`.")
    lines.append("> Analysis and Next Steps sections are manually maintained.")
    lines.append("")

    # Objective
    lines.append("## Objective")
    lines.append(objective)
    lines.append("")

    # Baseline
    if baseline_desc:
        lines.append("## Baseline Reference")
        lines.append(f"- {baseline_desc}")
        lines.append("")

    # Summary table
    lines.append("## Experiments")
    lines.append("")

    # Determine baseline value for delta calculation
    baseline_val: float | None = None
    if runs and baseline_desc:
        # Try to parse first number from description (e.g., "87.0 (Quetra seed)" or "RobustMPC 78.2")
        match = re.search(r"[-+]?\d+\.?\d*", baseline_desc.split(",")[0])
        if match:
            try:
                baseline_val = float(match.group(0))
            except ValueError:
                pass

    lines.append(f"| Label | Config | {metric_row} | vs Baseline | Run ID | Run Root |")
    lines.append("|-------|--------|" + "-" * (len(metric_row) + 2) + "|-------------|--------|----------|")
    for r in runs:
        delta = ""
        if baseline_val is not None and r.eoh_value is not None:
            d = r.eoh_value - baseline_val
            delta = f"{d:+.1f}"
        run_root = str(r.run_dir)
        # Shorten path for readability
        if "/root/code/" in run_root:
            run_root = run_root.replace("/root/code/", "")
        lines.append(
            f"| {r.label} | {r.config_summary} | {_fmt(r.eoh_value)} | {delta} | {r.run_id} | {run_root} |"
        )
    lines.append("")

    # Per-dataset breakdown (only datasets that have data)
    all_ds_with_data: list[str] = []
    for ds in DATASETS_3G + DATASETS_4G:
        if any(ds in r.per_dataset for r in runs):
            all_ds_with_data.append(ds)

    if all_ds_with_data:
        lines.append("## Per-Dataset Breakdown")
        lines.append("")

        header = "| Dataset | Baseline (RMPC) |"
        sep = "|---------|----------------|"
        for r in runs:
            short_label = r.label.split(":")[0].strip() if ":" in r.label else r.label
            if len(short_label) > 20:
                short_label = short_label[:20]
            header += f" {short_label} |"
            sep += "-" * (len(short_label) + 2) + "|"
        lines.append(header)
        lines.append(sep)

        # Get RMPC baselines from first run's CSV
        first_csv = find_csv(runs[0].run_dir) if runs else None
        rmpc_values: dict[str, float | None] = {}
        if first_csv:
            all_rows = parse_results_csv(first_csv)
            for ds in all_ds_with_data:
                ds_data = all_rows.get(ds, {})
                rmpc_values[ds] = ds_data.get("sim_rmpc")

        for ds in all_ds_with_data:
            row = f"| {ds} | {_fmt(rmpc_values.get(ds))} |"
            for r in runs:
                row += f" {_fmt(r.per_dataset.get(ds))} |"
            lines.append(row)
        lines.append("")

    # Analysis (preserve existing)
    lines.append("## Analysis")
    if existing_analysis.strip():
        lines.append(existing_analysis.strip())
    else:
        lines.append("<!-- 手动填写 -->")
    lines.append("")

    # Next Steps (preserve existing)
    lines.append("## Next Steps")
    if existing_next_steps.strip():
        lines.append(existing_next_steps.strip())
    else:
        lines.append("<!-- 手动填写 -->")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Existing content preservation
# ---------------------------------------------------------------------------

def extract_manual_sections(content: str) -> tuple[str, str]:
    """Extract Analysis and Next Steps sections from existing tracker content."""
    analysis = ""
    next_steps = ""

    sections = re.split(r"^## ", content, flags=re.MULTILINE)
    for section in sections:
        if section.startswith("Analysis"):
            body = section[len("Analysis"):].strip()
            # Remove trailing ## Next Steps if accidentally captured
            if "## Next Steps" in body:
                body = body[:body.index("## Next Steps")].strip()
            if body and body != "<!-- 手动填写 -->":
                analysis = body
        elif section.startswith("Next Steps"):
            body = section[len("Next Steps"):].strip()
            if body and body != "<!-- 手动填写 -->":
                next_steps = body

    return analysis, next_steps


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_run_arg(arg: str) -> tuple[str, str]:
    """Parse --run argument in format 'path:label' or just 'path'."""
    if ":" in arg:
        path_str, label = arg.rsplit(":", 1)
        return path_str.strip(), label.strip()
    return arg.strip(), Path(arg.strip()).name


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate or update a campaign tracker for a series of related experiment runs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create new series tracker:
  %(prog)s --name "3g-improve-round1" \\
    --objective "Improve 3G QoE" \\
    --baseline "87.0 (Quetra seed)" \\
    --run /path/to/exp-d:D:CVaR+LargePop15

  # Update existing (preserves Analysis/Next Steps):
  %(prog)s --name "3g-improve-round1" \\
    --run /path/to/exp-g:G:NewExperiment
""",
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Campaign name (used as filename: campaigns/<name>.md)",
    )
    parser.add_argument(
        "--objective",
        default="",
        help="Campaign objective description shared by the experiment series (only used on initial creation)",
    )
    parser.add_argument(
        "--baseline",
        default="",
        help='Baseline reference description, e.g. "87.0 (Quetra seed)"',
    )
    parser.add_argument(
        "--metric",
        default="ABRBench-3G (avg)",
        help="Row name in CSV to use as primary metric (default: ABRBench-3G (avg))",
    )
    parser.add_argument(
        "--run",
        action="append",
        dest="runs",
        default=[],
        help="Run directory and label in format 'path:label'. Repeatable.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Override output path (default: experiments/campaigns/<name>.md)",
    )

    args = parser.parse_args()

    if not args.runs:
        parser.error("At least one --run is required.")

    # Determine output path
    output_path = Path(args.output) if args.output else CAMPAIGNS_DIR / f"{args.name}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing content for preservation
    existing_analysis = ""
    existing_next_steps = ""
    existing_objective = args.objective
    existing_baseline = args.baseline

    if output_path.is_file():
        old_content = output_path.read_text()
        existing_analysis, existing_next_steps = extract_manual_sections(old_content)

        # Preserve objective/baseline from existing file if not provided
        if not args.objective:
            m = re.search(r"^## Objective\n(.+?)(?=\n##|\Z)", old_content, re.MULTILINE | re.DOTALL)
            if m:
                existing_objective = m.group(1).strip()
        if not args.baseline:
            m = re.search(r"^- (.+)", old_content[old_content.find("## Baseline"):] if "## Baseline" in old_content else "", re.MULTILINE)
            if m:
                existing_baseline = m.group(1).strip()

    # Load runs
    run_data: list[RunData] = []
    for run_arg in args.runs:
        path_str, label = parse_run_arg(run_arg)
        run_dir = Path(path_str).resolve()
        if not run_dir.exists():
            print(f"WARNING: run directory does not exist: {run_dir}", file=sys.stderr)
            continue
        print(f"Loading: {label} from {run_dir}")
        rd = load_run(run_dir, label, args.metric)
        run_data.append(rd)

    if not run_data:
        print("ERROR: no valid runs found.", file=sys.stderr)
        sys.exit(1)

    # Generate markdown
    md = generate_tracker_md(
        name=args.name,
        objective=existing_objective,
        baseline_desc=existing_baseline,
        metric_row=args.metric,
        runs=run_data,
        existing_analysis=existing_analysis,
        existing_next_steps=existing_next_steps,
    )

    output_path.write_text(md)
    print(f"Series tracker saved to {output_path}")

    # Copy results_summary.csv to campaigns/<name>/ for git tracking
    data_dir = CAMPAIGNS_DIR / args.name
    data_dir.mkdir(parents=True, exist_ok=True)
    for rd in run_data:
        csv_path = find_csv(rd.run_dir)
        if csv_path and csv_path.is_file():
            safe_label = rd.label.replace("/", "_").replace(" ", "_").replace(":", "_")
            dest = data_dir / f"{safe_label}_results_summary.csv"
            shutil.copy2(csv_path, dest)
            print(f"Copied CSV: {csv_path.name} -> {dest}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Manage the global experiment tracker at experiments/experiments_tracker.md.

Supports registering new runs, marking them complete/failed, and bulk-scanning
the results directory.  The tracker file is a Markdown table that is safe to
edit by hand (Campaign / Notes columns are preserved across updates).

Examples
--------
  # Register a new run
  python3 experiments/update_global_tracker.py \\
      --register 20260326-202134-grok-4.1-thinking \\
      --campaign 3g-baseline-models --target "ABRBench-3G, ABRBench-4G+"

  # Mark a run completed (auto-populates Key Result from CSV)
  python3 experiments/update_global_tracker.py --complete 20260326-202134-grok-4.1-thinking

  # Mark a run failed
  python3 experiments/update_global_tracker.py --fail 20260326-202134-grok-4.1-thinking

  # Scan results/ and add any missing runs
  python3 experiments/update_global_tracker.py --scan --campaign my-campaign
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Shared code from the ABR run-record module
# ---------------------------------------------------------------------------

sys.path.insert(0, str(Path(__file__).resolve().parent))

from abr_run_record import (
    RESULTS_ROOT,
    REPO_ROOT,
    SUITE_ROWS,
    discover_run_record,
    load_configs,
    build_scope,
    parse_run_started_at,
)

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
TRACKER_PATH = REPO_ROOT / "experiments" / "experiments_tracker.md"

# ---------------------------------------------------------------------------
# Tracker table schema
# ---------------------------------------------------------------------------

COLUMNS = [
    "Run ID",
    "Campaign",
    "Target",
    "Status",
    "Started",
    "Completed",
    "Key Result",
    "Notes",
]

HEADER = (
    "# Experiments Tracker\n"
    "\n"
    "> Global experiment log. Updated when experiment status changes. Git tracked.\n"
    "> See [campaigns/README.md](campaigns/README.md) for research series details.\n"
    "\n"
)


def _empty_row(run_id: str) -> dict[str, str]:
    return {col: "" for col in COLUMNS} | {"Run ID": run_id}


# ---------------------------------------------------------------------------
# Markdown table parsing / rendering
# ---------------------------------------------------------------------------


def parse_tracker(path: Path) -> list[dict[str, str]]:
    """Read the tracker Markdown file and return a list of row dicts."""
    if not path.is_file():
        return []

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Find the header row (first line starting with |)
    header_idx: int | None = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("|") and "Run ID" in stripped:
            header_idx = i
            break

    if header_idx is None:
        return []

    # Parse column names from header
    header_cells = [c.strip() for c in lines[header_idx].strip().strip("|").split("|")]

    # Find separator line (|---...|)
    sep_idx = header_idx + 1
    if sep_idx >= len(lines):
        return []
    sep_line = lines[sep_idx].strip()
    if not sep_line.startswith("|"):
        return []

    # Parse data rows
    rows: list[dict[str, str]] = []
    for line in lines[sep_idx + 1 :]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            # End of table (blank line or non-table content)
            break
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        row: dict[str, str] = {}
        for j, col in enumerate(header_cells):
            row[col] = cells[j] if j < len(cells) else ""
        rows.append(row)

    return rows


def render_tracker(rows: list[dict[str, str]]) -> str:
    """Render the tracker header + Markdown table from row dicts."""
    # Sort by Run ID descending (newest first)
    rows = sorted(rows, key=lambda r: r.get("Run ID", ""), reverse=True)

    # Compute column widths (minimum width = header label length)
    widths: dict[str, int] = {}
    for col in COLUMNS:
        widths[col] = len(col)
    for row in rows:
        for col in COLUMNS:
            widths[col] = max(widths[col], len(row.get(col, "")))

    def _row_line(cells: list[str]) -> str:
        parts = []
        for col, cell in zip(COLUMNS, cells):
            parts.append(f" {cell:<{widths[col]}} ")
        return "|" + "|".join(parts) + "|"

    header_line = _row_line(COLUMNS)
    sep_line = "|" + "|".join("-" * (widths[col] + 2) for col in COLUMNS) + "|"

    table_lines = [header_line, sep_line]
    for row in rows:
        table_lines.append(_row_line([row.get(col, "") for col in COLUMNS]))

    return HEADER + "\n".join(table_lines) + "\n"


def write_tracker(rows: list[dict[str, str]]) -> None:
    """Write tracker to disk, creating parent directories if needed."""
    TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_PATH.write_text(render_tracker(rows), encoding="utf-8")
    print(f"Tracker updated: {TRACKER_PATH}")


# ---------------------------------------------------------------------------
# Key Result extraction
# ---------------------------------------------------------------------------


def extract_key_result(run_id: str) -> str:
    """Read results_summary.csv and build a compact key-result string."""
    summary_csv = RESULTS_ROOT / run_id / "analysis" / "results_summary.csv"
    if not summary_csv.is_file():
        return ""

    try:
        with open(summary_csv, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            csv_rows = {row["Dataset"]: row for row in reader if "Dataset" in row}
    except Exception:
        return ""

    parts: list[str] = []
    label_map = {
        "ABRBench-3G (avg)": "3G",
        "ABRBench-4G+ (avg)": "4G+",
    }
    for suite_row, short_label in label_map.items():
        row = csv_rows.get(suite_row)
        if row is None:
            continue
        eoh_val = row.get("sim_eoh", "").strip()
        if not eoh_val or eoh_val == "-":
            continue
        try:
            val = float(eoh_val)
        except ValueError:
            continue
        parts.append(f"{short_label}:{val:.1f}")

    return ", ".join(parts)


# ---------------------------------------------------------------------------
# Auto-populate helpers
# ---------------------------------------------------------------------------


def _auto_target(run_id: str) -> str:
    """Derive target string from EoH configs."""
    run_root = RESULTS_ROOT / run_id
    if not run_root.is_dir():
        return ""
    configs = load_configs(run_root)
    scope = build_scope(configs)
    return ", ".join(scope) if scope else ""


def _auto_model_note(run_id: str) -> str:
    """Derive model name from EoH configs for the Notes column."""
    run_root = RESULTS_ROOT / run_id
    if not run_root.is_dir():
        return ""
    configs = load_configs(run_root)
    models = sorted({c.model for c in configs if c.model})
    return ", ".join(models) if models else ""


def _started_date(run_id: str) -> str:
    """Extract YYYY-MM-DD from run_id via parse_run_started_at."""
    run_root = RESULTS_ROOT / run_id
    ts = parse_run_started_at(run_id, run_root)
    if ts == "unknown":
        return ""
    # parse_run_started_at returns "YYYY-MM-DD HH:MM:SS"
    return ts.split(" ")[0]


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


def _find_row(rows: list[dict[str, str]], run_id: str) -> dict[str, str] | None:
    for row in rows:
        if row.get("Run ID") == run_id:
            return row
    return None


def op_register(
    rows: list[dict[str, str]],
    run_id: str,
    campaign: str,
    target: str,
    status: str,
) -> list[dict[str, str]]:
    """Register a run or update fields on an existing row."""
    existing = _find_row(rows, run_id)
    if existing is not None:
        # Update only provided (non-empty) fields; never overwrite Campaign/Notes
        # if the caller didn't supply them.
        if campaign:
            existing["Campaign"] = campaign
        if target:
            existing["Target"] = target
        if status:
            existing["Status"] = status
        return rows

    row = _empty_row(run_id)
    row["Campaign"] = campaign
    row["Target"] = target
    row["Status"] = status
    row["Started"] = _started_date(run_id)
    rows.append(row)
    print(f"Registered: {run_id} (status={status})")
    return rows


def op_complete(rows: list[dict[str, str]], run_id: str) -> list[dict[str, str]]:
    """Mark a run as completed and auto-populate results."""
    row = _find_row(rows, run_id)
    if row is None:
        # Auto-register first
        rows = op_register(rows, run_id, campaign="", target="", status="running")
        row = _find_row(rows, run_id)
        assert row is not None

    row["Status"] = "completed"
    row["Completed"] = date.today().isoformat()

    # Auto-populate Key Result
    key_result = extract_key_result(run_id)
    if key_result:
        row["Key Result"] = key_result

    # Auto-populate Target if empty
    if not row.get("Target"):
        row["Target"] = _auto_target(run_id)

    # Auto-populate Notes with model name if empty
    if not row.get("Notes"):
        row["Notes"] = _auto_model_note(run_id)

    print(f"Completed: {run_id} -> Key Result: {row.get('Key Result', '')}")
    return rows


def op_fail(rows: list[dict[str, str]], run_id: str) -> list[dict[str, str]]:
    """Mark a run as failed."""
    row = _find_row(rows, run_id)
    if row is None:
        rows = op_register(rows, run_id, campaign="", target="", status="failed")
        row = _find_row(rows, run_id)
        assert row is not None

    row["Status"] = "failed"
    row["Completed"] = date.today().isoformat()

    print(f"Failed: {run_id}")
    return rows


def op_scan(rows: list[dict[str, str]], campaign: str) -> list[dict[str, str]]:
    """Scan results/ and add missing runs to the tracker."""
    if not RESULTS_ROOT.is_dir():
        print(f"Results directory not found: {RESULTS_ROOT}", file=sys.stderr)
        return rows

    existing_ids = {row.get("Run ID") for row in rows}
    added = 0

    for entry in sorted(RESULTS_ROOT.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("_"):
            continue

        run_id = entry.name
        if run_id in existing_ids:
            # Never overwrite Campaign or Notes for existing rows
            continue

        # Auto-detect status via discover_run_record
        try:
            record = discover_run_record(entry)
            status = record.status
        except Exception:
            status = "unknown"

        row = _empty_row(run_id)
        row["Status"] = status
        row["Started"] = _started_date(run_id)
        row["Campaign"] = campaign

        # Auto-populate target and notes
        row["Target"] = _auto_target(run_id)
        row["Notes"] = _auto_model_note(run_id)

        # Auto-populate key result if completed
        if status == "completed":
            key_result = extract_key_result(run_id)
            if key_result:
                row["Key Result"] = key_result
            row["Completed"] = _started_date(run_id)  # best guess

        rows.append(row)
        existing_ids.add(run_id)
        added += 1
        print(f"  Added: {run_id} (status={status})")

    print(f"Scan complete: {added} new run(s) added.")
    return rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="update_global_tracker",
        description="Manage the global experiment tracker (experiments/experiments_tracker.md).",
        epilog=(
            "Examples:\n"
            "  # Register a new run\n"
            "  python3 experiments/update_global_tracker.py \\\n"
            '      --register 20260326-202134-grok-4.1-thinking \\\n'
            '      --campaign 3g-baseline-models --target "ABRBench-3G, ABRBench-4G+"\n'
            "\n"
            "  # Complete a run (auto-populates key result)\n"
            "  python3 experiments/update_global_tracker.py --complete 20260326-202134-grok-4.1-thinking\n"
            "\n"
            "  # Fail a run\n"
            "  python3 experiments/update_global_tracker.py --fail 20260326-202134-grok-4.1-thinking\n"
            "\n"
            "  # Scan results/ for new runs\n"
            "  python3 experiments/update_global_tracker.py --scan --campaign my-campaign\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--register",
        metavar="RUN_ID",
        help="Register a new run (or update an existing one).",
    )
    group.add_argument(
        "--complete",
        metavar="RUN_ID",
        help="Mark a run as completed and auto-populate Key Result.",
    )
    group.add_argument(
        "--fail",
        metavar="RUN_ID",
        help="Mark a run as failed.",
    )
    group.add_argument(
        "--scan",
        action="store_true",
        help="Scan results/ and add missing runs.",
    )

    parser.add_argument(
        "--campaign",
        default="",
        help="Campaign name (used with --register and --scan).",
    )
    parser.add_argument(
        "--target",
        default="",
        help="Target description (used with --register).",
    )
    parser.add_argument(
        "--status",
        default="running",
        help="Initial status (used with --register, default: running).",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Load existing tracker
    rows = parse_tracker(TRACKER_PATH)

    if args.register:
        rows = op_register(rows, args.register, args.campaign, args.target, args.status)
    elif args.complete:
        rows = op_complete(rows, args.complete)
    elif args.fail:
        rows = op_fail(rows, args.fail)
    elif args.scan:
        rows = op_scan(rows, args.campaign)

    write_tracker(rows)


if __name__ == "__main__":
    main()

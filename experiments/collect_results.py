#!/usr/bin/env python3
"""Collect per-trace log results across all datasets and methods.

Parses SABR-format log files from each dataset's LOG_FILE_DIR and produces:
  - Summary table: dataset x method → mean QoE (stdout + CSV)
  - Per-suite averages (ABRBench-3G, ABRBench-4G+)

Usage:
    python collect_results.py --run-id 20260325-120000 [--schemes sim_bb,sim_bola,...]
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

import numpy as np

from run_layout import build_analysis_csv_path

# ---------------------------------------------------------------------------
# Setup imports
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SABR_DIR = REPO_ROOT / "env" / "SABR"

if str(SABR_DIR) not in sys.path:
    sys.path.insert(0, str(SABR_DIR))

from config import _DATASET_OPTION  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VIDEO_LEN = 48

DATASETS_3G = ["FCC-16", "FCC-18", "Oboe", "Puffer-21", "Puffer-22", "HSR"]
DATASETS_4G = ["Norway3G", "Lumos4G", "Lumos5G", "SolisWi-Fi", "Ghent", "Lab"]
ALL_DATASETS = DATASETS_3G + DATASETS_4G

DEFAULT_SCHEMES = ["sim_bb", "sim_bola", "sim_quetra", "sim_rmpc", "sim_bs", "sim_mfd", "sim_eoh"]

SMOOTH_PENALTY = 1


# ---------------------------------------------------------------------------
# Log parsing (adapted from plot_result.py)
# ---------------------------------------------------------------------------

def parse_logs_for_dataset(
    dataset: str,
    schemes: list[str],
) -> dict[str, float | None]:
    """Parse all log files for *dataset* and return {scheme: mean_reward}."""
    ds = _DATASET_OPTION.get(dataset)
    if ds is None:
        return {s: None for s in schemes}

    log_dir = ds["LOG_FILE_DIR"]
    video_bit_rate = ds["VIDEO_BIT_RATE"]
    rebuf_penalty = ds["REBUF_PENALTY"]

    if not os.path.isdir(log_dir):
        return {s: None for s in schemes}

    log_files = os.listdir(log_dir)

    # Collect per-trace rewards for each scheme
    raw_rewards: dict[str, dict[str, list[float]]] = {s: {} for s in schemes}

    for log_file in log_files:
        full_path = os.path.join(log_dir, log_file)
        if os.path.isdir(full_path):
            continue

        matched_scheme = None
        for scheme in schemes:
            if scheme in log_file:
                matched_scheme = scheme
                break
        if matched_scheme is None:
            continue

        trace_name = log_file[len("log_" + matched_scheme + "_"):]
        rewards = []

        try:
            with open(full_path, "r") as f:
                for line in f:
                    parse = line.split()
                    if len(parse) <= 1:
                        break
                    rewards.append(float(parse[-1]))
        except Exception:
            continue

        if len(rewards) >= VIDEO_LEN:
            raw_rewards[matched_scheme][trace_name] = rewards

    # Compute mean per-video reward for each scheme
    # Only include traces common to ALL schemes that have data
    schemes_with_data = [s for s in schemes if raw_rewards[s]]

    if not schemes_with_data:
        return {s: None for s in schemes}

    results: dict[str, float | None] = {}
    for scheme in schemes:
        if not raw_rewards[scheme]:
            results[scheme] = None
            continue
        # Sum rewards over chunks 1..VIDEO_LEN for each trace
        per_video_rewards = []
        for trace_name, rews in raw_rewards[scheme].items():
            per_video_rewards.append(np.sum(rews[1:VIDEO_LEN]))
        results[scheme] = float(np.mean(per_video_rewards)) if per_video_rewards else None

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Collect ABR experiment results")
    parser.add_argument(
        "--run-id",
        default=os.environ.get("ABR_RUN_ID"),
        help="Canonical run id under experiments/results/ (or set ABR_RUN_ID)",
    )
    parser.add_argument("--schemes", default=None,
                        help="Comma-separated scheme names (default: all)")
    args = parser.parse_args()

    if not args.run_id:
        parser.error("--run-id or ABR_RUN_ID is required")

    schemes = args.schemes.split(",") if args.schemes else DEFAULT_SCHEMES
    output_path = build_analysis_csv_path(REPO_ROOT, run_id=args.run_id)

    # Header
    header = ["Dataset"] + schemes
    rows = []

    suite_rewards: dict[str, dict[str, list[float]]] = {
        "ABRBench-3G": {s: [] for s in schemes},
        "ABRBench-4G+": {s: [] for s in schemes},
    }

    for dataset in ALL_DATASETS:
        results = parse_logs_for_dataset(dataset, schemes)
        row = [dataset]
        suite = "ABRBench-3G" if dataset in DATASETS_3G else "ABRBench-4G+"
        for scheme in schemes:
            val = results.get(scheme)
            if val is not None:
                row.append(f"{val:.4f}")
                suite_rewards[suite][scheme].append(val)
            else:
                row.append("-")
        rows.append(row)

    # Suite averages
    for suite_name in ["ABRBench-3G", "ABRBench-4G+"]:
        row = [f"{suite_name} (avg)"]
        for scheme in schemes:
            vals = suite_rewards[suite_name][scheme]
            if vals:
                row.append(f"{np.mean(vals):.4f}")
            else:
                row.append("-")
        rows.append(row)

    # Overall average
    overall_row = ["Overall (avg)"]
    for scheme in schemes:
        all_vals = suite_rewards["ABRBench-3G"][scheme] + suite_rewards["ABRBench-4G+"][scheme]
        if all_vals:
            overall_row.append(f"{np.mean(all_vals):.4f}")
        else:
            overall_row.append("-")
    rows.append(overall_row)

    # Print table
    col_widths = [max(len(header[i]), max(len(r[i]) for r in rows)) for i in range(len(header))]
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)

    print()
    print(fmt.format(*header))
    print("-" * (sum(col_widths) + 2 * (len(col_widths) - 1)))
    for row in rows:
        if row[0].startswith("ABRBench") or row[0].startswith("Overall"):
            print("-" * (sum(col_widths) + 2 * (len(col_widths) - 1)))
        print(fmt.format(*row))
    print()

    # Write canonical CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"CSV saved to {output_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate comparison plots for all datasets across all methods.

Produces per-dataset:
  1. Reward line plot (per-trace total rewards)
  2. CDF plot of per-trace rewards
  3. Bar chart of mean QoE

And a summary bar chart across all datasets.

Usage:
    python plot_results.py --run-id 20260325-120000 [--schemes sim_bb,sim_bola,...]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from run_layout import build_eval_log_dir, build_eval_logs_root, build_plots_dir

# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SABR_DIR = REPO_ROOT / "env" / "SABR"

if str(SABR_DIR) not in sys.path:
    sys.path.insert(0, str(SABR_DIR))

from config import _DATASET_OPTION  # noqa: E402

# ---------------------------------------------------------------------------
VIDEO_LEN = 48
NUM_BINS = 100

DATASETS_3G = ["FCC-16", "FCC-18", "Oboe", "Puffer-21", "Puffer-22", "HSR"]
DATASETS_4G = ["Norway3G", "Lumos4G", "Lumos5G", "SolisWi-Fi", "Ghent", "Lab"]
ALL_DATASETS = DATASETS_3G + DATASETS_4G

DEFAULT_SCHEMES = [
    "sim_bb", "sim_bola", "sim_quetra", "sim_rmpc",
    "sim_bs", "sim_mfd", "sim_eoh",
]

# Pretty names for legends
SCHEME_LABELS = {
    "sim_bb": "BB",
    "sim_bola": "BOLA",
    "sim_quetra": "QUETRA",
    "sim_rmpc": "RobustMPC",
    "sim_bs": "BeamSearch",
    "sim_mfd": "MFD",
    "sim_eoh": "EoH",
}

# Distinct colors for each scheme
SCHEME_COLORS = {
    "sim_bb": "#1f77b4",
    "sim_bola": "#ff7f0e",
    "sim_quetra": "#2ca02c",
    "sim_rmpc": "#d62728",
    "sim_bs": "#9467bd",
    "sim_mfd": "#8c564b",
    "sim_eoh": "#e377c2",
}


def parse_dataset_logs(
    dataset: str,
    schemes: list[str],
    *,
    run_id: str,
):
    """Parse log files for a dataset. Returns {scheme: {trace: [rewards]}}."""
    ds = _DATASET_OPTION.get(dataset)
    if ds is None:
        return {}

    run_local_logs_enabled = build_eval_logs_root(REPO_ROOT, run_id=run_id).is_dir()
    run_local_log_dir = build_eval_log_dir(REPO_ROOT, dataset=dataset, run_id=run_id)
    shared_log_dir = Path(ds["LOG_FILE_DIR"])

    raw_rewards = {}
    for scheme in schemes:
        raw_rewards[scheme] = _load_scheme_rewards(
            scheme=scheme,
            run_local_logs_enabled=run_local_logs_enabled,
            run_local_log_dir=run_local_log_dir,
            shared_log_dir=shared_log_dir,
        )

    return raw_rewards


def _load_scheme_rewards(
    *,
    scheme: str,
    run_local_logs_enabled: bool,
    run_local_log_dir: Path,
    shared_log_dir: Path,
) -> dict[str, list[float]]:
    candidate_dirs: list[Path]
    if scheme == "sim_eoh":
        candidate_dirs = [run_local_log_dir] if run_local_logs_enabled else [shared_log_dir]
    else:
        candidate_dirs = [shared_log_dir]

    for log_dir in candidate_dirs:
        rewards = _parse_scheme_logs_from_dir(log_dir, scheme)
        if rewards:
            return rewards

    return {}


def _parse_scheme_logs_from_dir(log_dir: Path, scheme: str) -> dict[str, list[float]]:
    if not log_dir.is_dir():
        return {}

    prefix = f"log_{scheme}_"
    raw_rewards: dict[str, list[float]] = {}
    for log_file in os.listdir(log_dir):
        if not log_file.startswith(prefix):
            continue

        full_path = log_dir / log_file
        if full_path.is_dir():
            continue

        trace_name = log_file[len(prefix):]
        rewards: list[float] = []
        try:
            with open(full_path, "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) <= 1:
                        break
                    rewards.append(float(parts[-1]))
        except Exception:
            continue

        if len(rewards) >= VIDEO_LEN:
            raw_rewards[trace_name] = rewards

    return raw_rewards


def compute_per_video_rewards(raw_rewards, schemes):
    """Compute per-video total reward (sum of chunks 1..VIDEO_LEN)."""
    result = {}
    for scheme in schemes:
        if not raw_rewards.get(scheme):
            result[scheme] = []
            continue
        per_video = []
        for trace, rews in raw_rewards[scheme].items():
            per_video.append(np.sum(rews[1:VIDEO_LEN]))
        result[scheme] = per_video
    return result


def plot_reward_line(per_video, schemes, dataset, output_dir):
    """Line plot: per-trace total reward."""
    fig, ax = plt.subplots(figsize=(12, 5))
    for scheme in schemes:
        if per_video.get(scheme):
            label = SCHEME_LABELS.get(scheme, scheme)
            color = SCHEME_COLORS.get(scheme, None)
            ax.plot(per_video[scheme], label=label, color=color, alpha=0.8, linewidth=1)
    ax.set_xlabel("Trace Index")
    ax.set_ylabel("Total QoE Reward")
    ax.set_title(f"{dataset} — Per-Trace QoE Reward")
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{dataset}_reward_line.png"), dpi=150)
    plt.close()


def plot_reward_cdf(per_video, schemes, dataset, output_dir):
    """CDF plot of per-trace total rewards."""
    fig, ax = plt.subplots(figsize=(8, 5))
    for scheme in schemes:
        vals = per_video.get(scheme, [])
        if not vals:
            continue
        sorted_vals = np.sort(vals)
        cdf = np.arange(1, len(sorted_vals) + 1) / len(sorted_vals)
        label = SCHEME_LABELS.get(scheme, scheme)
        color = SCHEME_COLORS.get(scheme, None)
        ax.plot(sorted_vals, cdf, label=label, color=color, linewidth=1.5)
    ax.set_xlabel("Total QoE Reward")
    ax.set_ylabel("CDF")
    ax.set_title(f"{dataset} — CDF of Per-Trace QoE")
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{dataset}_reward_cdf.png"), dpi=150)
    plt.close()


def plot_mean_bar(per_video, schemes, dataset, output_dir):
    """Bar chart of mean QoE per scheme."""
    means = []
    labels = []
    colors = []
    for scheme in schemes:
        vals = per_video.get(scheme, [])
        if vals:
            means.append(np.mean(vals))
            labels.append(SCHEME_LABELS.get(scheme, scheme))
            colors.append(SCHEME_COLORS.get(scheme, "#999999"))

    if not means:
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(labels))
    bars = ax.bar(x, means, color=colors, edgecolor="black", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Mean QoE Reward")
    ax.set_title(f"{dataset} — Mean QoE by Method")
    ax.grid(True, axis="y", alpha=0.3)

    # Add value labels on bars
    for bar, val in zip(bars, means):
        y_pos = bar.get_height()
        va = "bottom" if y_pos >= 0 else "top"
        ax.text(bar.get_x() + bar.get_width() / 2, y_pos, f"{val:.1f}",
                ha="center", va=va, fontsize=7)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{dataset}_mean_bar.png"), dpi=150)
    plt.close()


def plot_summary_bar(all_means, schemes, datasets, output_dir):
    """Grouped bar chart: all datasets x all schemes."""
    n_datasets = len(datasets)
    n_schemes = len(schemes)
    bar_width = 0.8 / n_schemes
    x = np.arange(n_datasets)

    fig, ax = plt.subplots(figsize=(16, 6))
    for i, scheme in enumerate(schemes):
        vals = [all_means.get(ds, {}).get(scheme, 0) for ds in datasets]
        label = SCHEME_LABELS.get(scheme, scheme)
        color = SCHEME_COLORS.get(scheme, None)
        offset = (i - n_schemes / 2 + 0.5) * bar_width
        ax.bar(x + offset, vals, bar_width, label=label, color=color,
               edgecolor="black", linewidth=0.3)

    ax.set_xticks(x)
    ax.set_xticklabels(datasets, rotation=45, ha="right")
    ax.set_ylabel("Mean QoE Reward")
    ax.set_title("Mean QoE Across All Datasets")
    ax.legend(loc="best", fontsize=8, ncol=n_schemes)
    ax.grid(True, axis="y", alpha=0.3)
    ax.axhline(y=0, color="black", linewidth=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "summary_all_datasets.png"), dpi=150)
    plt.close()


def plot_suite_summary(all_means, schemes, output_dir):
    """Bar chart: suite-level averages (3G, 4G+, Overall)."""
    suites = {
        "ABRBench-3G": DATASETS_3G,
        "ABRBench-4G+": DATASETS_4G,
        "Overall": ALL_DATASETS,
    }

    suite_names = list(suites.keys())
    n_schemes = len(schemes)
    bar_width = 0.8 / n_schemes
    x = np.arange(len(suite_names))

    fig, ax = plt.subplots(figsize=(10, 5))
    for i, scheme in enumerate(schemes):
        vals = []
        for suite_name in suite_names:
            ds_list = suites[suite_name]
            suite_vals = [all_means[ds][scheme] for ds in ds_list
                          if ds in all_means and scheme in all_means[ds]]
            vals.append(np.mean(suite_vals) if suite_vals else 0)
        label = SCHEME_LABELS.get(scheme, scheme)
        color = SCHEME_COLORS.get(scheme, None)
        offset = (i - n_schemes / 2 + 0.5) * bar_width
        ax.bar(x + offset, vals, bar_width, label=label, color=color,
               edgecolor="black", linewidth=0.3)

    ax.set_xticks(x)
    ax.set_xticklabels(suite_names, fontsize=11)
    ax.set_ylabel("Mean QoE Reward")
    ax.set_title("Suite-Level Average QoE")
    ax.legend(loc="best", fontsize=8, ncol=n_schemes)
    ax.grid(True, axis="y", alpha=0.3)
    ax.axhline(y=0, color="black", linewidth=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "summary_suites.png"), dpi=150)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Plot ABR experiment results")
    parser.add_argument(
        "--run-id",
        default=os.environ.get("ABR_RUN_ID"),
        help="Canonical run id under experiments/results/ (or set ABR_RUN_ID)",
    )
    parser.add_argument("--schemes", default=None,
                        help="Comma-separated scheme names")
    args = parser.parse_args()

    if not args.run_id:
        parser.error("--run-id or ABR_RUN_ID is required")

    schemes = args.schemes.split(",") if args.schemes else DEFAULT_SCHEMES
    output_dir = str(build_plots_dir(REPO_ROOT, run_id=args.run_id))
    os.makedirs(output_dir, exist_ok=True)

    all_means = {}

    for dataset in ALL_DATASETS:
        print(f"Processing {dataset}...")
        raw = parse_dataset_logs(dataset, schemes, run_id=args.run_id)
        per_video = compute_per_video_rewards(raw, schemes)

        # Store means
        all_means[dataset] = {}
        for scheme in schemes:
            if per_video.get(scheme):
                all_means[dataset][scheme] = np.mean(per_video[scheme])

        # Per-dataset plots
        active_schemes = [s for s in schemes if per_video.get(s)]
        if active_schemes:
            plot_reward_line(per_video, active_schemes, dataset, output_dir)
            plot_reward_cdf(per_video, active_schemes, dataset, output_dir)
            plot_mean_bar(per_video, active_schemes, dataset, output_dir)

    # Summary plots
    print("Generating summary plots...")
    plot_summary_bar(all_means, schemes, ALL_DATASETS, output_dir)
    plot_suite_summary(all_means, schemes, output_dir)

    print(f"All plots saved to {output_dir}/")


if __name__ == "__main__":
    main()

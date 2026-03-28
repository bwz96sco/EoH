#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# EoH vs SABR Baselines — Full Experiment Pipeline
#
# Phases:
#   1) EoH evolution (ABRBench-3G and ABRBench-4G+)
#   2) SABR rule-based baselines on each individual dataset
#   3) EoH heuristic evaluation via bridge script on each dataset
#   4) Analysis — collect results + plots + per-run report
#
# Prerequisites:
#   - SABR cloned and built: env/SABR/ with ABRBench data
#   - EoH installed: uv sync
#   - LLM env vars set (LLM_API_ENDPOINT, LLM_API_KEY, LLM_MODEL)
#     or local LLM running (LLM_USE_LOCAL=1, LLM_LOCAL_URL=...)
# =============================================================================

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SABR_DIR="${REPO_ROOT}/env/SABR"
ABR_EXAMPLE_DIR="${REPO_ROOT}/examples/user_abr"
BRIDGE_SCRIPT="${SABR_DIR}/eval_eoh_in_sabr.py"
COLLECT_SCRIPT="${REPO_ROOT}/experiments/collect_results.py"
PLOT_SCRIPT="${REPO_ROOT}/experiments/plot_results.py"
REPORT_SCRIPT="${REPO_ROOT}/experiments/generate_run_report.py"
TRACKER_SCRIPT="${REPO_ROOT}/experiments/update_experiment_tracker.py"
TRACKER_PATH="${REPO_ROOT}/experiments/private/experiment_index.md"
BACKUP_CONFIG="${REPO_ROOT}/experiments/private/backup.env"
CONFIG_PY="${SABR_DIR}/config.py"
CONFIG_H="${SABR_DIR}/build_env_c_plus/config.h"

if [[ -f "$BACKUP_CONFIG" ]]; then
    # shellcheck source=/dev/null
    source "$BACKUP_CONFIG"
fi

# EoH parameters (override via env vars)
EC_N_POP="${EC_N_POP:-10}"
EXP_N_PROC="${EXP_N_PROC:-4}"
EVA_TIMEOUT="${EVA_TIMEOUT:-120}"
ABR_BACKUP_REMOTE="${ABR_BACKUP_REMOTE:-${ABR_BACKUP_REMOTE_DEFAULT:-}}"
ABR_BACKUP_SEED_CACHE="${ABR_BACKUP_SEED_CACHE:-${ABR_BACKUP_SEED_CACHE_DEFAULT:-0}}"
ABR_SKIP_TRACKER_UPDATE="${ABR_SKIP_TRACKER_UPDATE:-0}"

# Dataset groups
DATASETS_3G=("FCC-16" "FCC-18" "Oboe" "Puffer-21" "Puffer-22" "HSR")
DATASETS_4G=("Norway3G" "Lumos4G" "Lumos5G" "SolisWi-Fi" "Ghent" "Lab")

# Track which C++ bitrate group is currently built
CURRENT_CPP_GROUP=""

# Phase selection (set SKIP_PHASE_N=1 to skip)
SKIP_PHASE_1="${SKIP_PHASE_1:-0}"
SKIP_PHASE_2="${SKIP_PHASE_2:-0}"
SKIP_PHASE_3="${SKIP_PHASE_3:-0}"
SKIP_PHASE_4="${SKIP_PHASE_4:-0}"

# ---- Helpers ----------------------------------------------------------------

log_info()  { echo ">>> [$(date '+%H:%M:%S')] $*"; }
log_phase() { echo ""; echo "========== $* =========="; echo ""; }

backup_path_if_present() {
    local local_path="$1"
    local remote_path="$2"

    if [[ ! -e "$local_path" ]]; then
        log_info "Backup skip: ${local_path} does not exist"
        return 0
    fi

    if [[ -d "$local_path" ]]; then
        log_info "Backing up directory ${local_path} -> ${remote_path}"
        rclone copy "$local_path" "$remote_path" --progress --create-empty-src-dirs
        return
    fi

    log_info "Backing up file ${local_path} -> ${remote_path}"
    rclone copyto "$local_path" "$remote_path" --progress
}

backup_run_artifacts() {
    if [[ -z "$ABR_BACKUP_REMOTE" ]]; then
        return 0
    fi

    log_phase "BACKUP"

    if ! command -v rclone >/dev/null 2>&1; then
        log_info "WARNING: ABR_BACKUP_REMOTE is set but rclone is not installed"
        return 0
    fi

    backup_path_if_present "$RUN_ROOT" "${ABR_BACKUP_REMOTE%/}/experiments/results/${ABR_RUN_ID}" || \
        log_info "WARNING: failed to back up canonical run root"
    backup_path_if_present "$TRACKER_PATH" "${ABR_BACKUP_REMOTE%/}/experiments/private/experiment_index.md" || \
        log_info "WARNING: failed to back up private tracker"

    if [[ "$ABR_BACKUP_SEED_CACHE" == "1" ]]; then
        backup_path_if_present "$ABR_EXAMPLE_DIR/seed_cache" "${ABR_BACKUP_REMOTE%/}/examples/user_abr/seed_cache" || \
            log_info "WARNING: failed to back up seed cache"
    fi
}

resolve_run_layout() {
    local repo_root="$1"
    python3 - "$repo_root" <<'PY'
from pathlib import Path
import os
import sys

repo_root = Path(sys.argv[1])
sys.path.insert(0, str(repo_root / "experiments"))

from run_layout import (
    build_analysis_csv_path,
    build_eval_log_dir,
    build_log_path,
    build_plots_dir,
    build_run_layout,
    sanitize_component,
)

layout = build_run_layout(
    repo_root,
    run_id=os.environ.get("ABR_RUN_ID"),
    run_label=os.environ.get("ABR_RUN_LABEL"),
)

print(layout.run_id)
print(layout.run_root)
print(layout.raw_root)
print(layout.analysis_root)
print(layout.logs_root)
print(layout.raw_root / "eoh" / sanitize_component("ABRBench-3G", "eoh"))
print(layout.raw_root / "eoh" / sanitize_component("ABRBench-4G+", "eoh"))
print(build_analysis_csv_path(repo_root, run_id=layout.run_id))
print(build_plots_dir(repo_root, run_id=layout.run_id))
print(build_log_path(repo_root, log_name="full_pipeline", run_id=layout.run_id))
PY
}

resolve_eval_log_dir() {
    local repo_root="$1"
    local dataset="$2"
    python3 - "$repo_root" "$dataset" <<'PY'
from pathlib import Path
import os
import sys

repo_root = Path(sys.argv[1])
dataset = sys.argv[2]
sys.path.insert(0, str(repo_root / "experiments"))

from run_layout import build_eval_log_dir

print(
    build_eval_log_dir(
        repo_root,
        dataset=dataset,
        run_id=os.environ.get("ABR_RUN_ID"),
        run_label=os.environ.get("ABR_RUN_LABEL"),
    )
)
PY
}

cpp_option_for_dataset() {
    case "$1" in
        "FCC-16") echo 1 ;;
        "FCC-18") echo 2 ;;
        "Oboe") echo 3 ;;
        "Puffer-21") echo 4 ;;
        "Puffer-22") echo 5 ;;
        "Norway3G") echo 6 ;;
        "Lumos4G") echo 7 ;;
        "Lumos5G") echo 8 ;;
        "SolisWi-Fi") echo 9 ;;
        "HSR") echo 15 ;;
        "Ghent") echo 16 ;;
        "Lab") echo 17 ;;
        *)
            echo "Unknown dataset: $1" >&2
            return 1
            ;;
    esac
}

set_python_dataset() {
    # Set _DATASET in config.py
    local ds="$1"
    sed -i '' "s/^_DATASET = .*/_DATASET = '${ds}'/" "$CONFIG_PY"
    log_info "Python config.py → _DATASET = '${ds}'"
}

set_cpp_dataset_and_rebuild() {
    # Set DATASET_OPTION in config.h and rebuild C++ env
    local opt="$1"
    sed -i '' "s/^#define DATASET_OPTION .*/#define DATASET_OPTION ${opt}/" "$CONFIG_H"
    log_info "C++ config.h → DATASET_OPTION = ${opt}, rebuilding..."
    (cd "${SABR_DIR}/build_env_c_plus" && bash build_all.sh)
    log_info "C++ rebuild complete"
}

ensure_cpp_group() {
    # Rebuild C++ only when switching between 3G ↔ 4G+ groups
    local group="$1"  # "3G" or "4G+"
    local representative_opt="$2"  # any option in that group
    if [[ "$CURRENT_CPP_GROUP" != "$group" ]]; then
        set_cpp_dataset_and_rebuild "$representative_opt"
        CURRENT_CPP_GROUP="$group"
    fi
}

run_python_baselines() {
    # Run the three Python-only baselines: bb, bola, quetra
    local ds="$1"
    set_python_dataset "$ds"

    log_info "Running BB on ${ds}..."
    (cd "$SABR_DIR" && uv run python bb.py)

    log_info "Running BOLA on ${ds}..."
    (cd "$SABR_DIR" && uv run python bola.py)

    log_info "Running QUETRA on ${ds}..."
    (cd "$SABR_DIR" && uv run python quetra.py)
}

run_cpp_baselines() {
    # Run the three C++-dependent baselines: RobustMPC, BeamSearch, MFD
    local ds="$1"
    local cpp_opt
    cpp_opt="$(cpp_option_for_dataset "$ds")"
    local group="$2"  # "3G" or "4G+"

    set_python_dataset "$ds"
    ensure_cpp_group "$group" "$cpp_opt"
    # Also set per-dataset C++ option for trace path correctness
    set_cpp_dataset_and_rebuild "$cpp_opt"

    log_info "Running RobustMPC on ${ds}..."
    (cd "$SABR_DIR" && uv run python run_rmpc_c_version.py)

    log_info "Running BeamSearch on ${ds}..."
    (cd "$SABR_DIR" && uv run python run_bs_mpc.py bs)

    log_info "Running MFD on ${ds}..."
    (cd "$SABR_DIR" && uv run python run_bs_mpc.py mfd)
}

find_best_population() {
    # Find the latest (highest generation) population JSON under a canonical raw
    # EoH output root:
    #   {root}/eoh_<Problem>_<timestamp>/results/pops_best/population_generation_<N>.json
    local results_dir="$1"
    if [[ ! -d "$results_dir" ]]; then
        echo ""
        return
    fi

    find "$results_dir" -path '*/results/pops_best/population_generation_*.json' 2>/dev/null \
        | sed -E 's#^(.*population_generation_)([0-9]+)(\.json)$#\2 \1\2\3#' \
        | sort -n \
        | tail -1 \
        | cut -d' ' -f2-
}

RUN_LAYOUT_OUTPUT="$(resolve_run_layout "$REPO_ROOT")"
OLD_IFS="$IFS"
IFS=$'\n'
set -- $RUN_LAYOUT_OUTPUT
IFS="$OLD_IFS"

if [[ "$#" -ne 10 ]]; then
    echo "Failed to resolve canonical ABR run layout" >&2
    exit 1
fi

ABR_RUN_ID="$1"
RUN_ROOT="$2"
RAW_ROOT="$3"
ANALYSIS_ROOT="$4"
LOGS_ROOT="$5"
EOH_3G_ROOT="$6"
EOH_4G_ROOT="$7"
SUMMARY_CSV="$8"
PLOTS_DIR="$9"
PIPELINE_LOG="${10}"
export ABR_RUN_ID

mkdir -p "$RAW_ROOT" "$ANALYSIS_ROOT" "$LOGS_ROOT"
exec > >(tee -a "$PIPELINE_LOG") 2>&1

log_info "ABR run id: ${ABR_RUN_ID}"
log_info "Canonical run root: ${RUN_ROOT}"
log_info "Raw outputs: ${RAW_ROOT}"
log_info "Analysis outputs: ${ANALYSIS_ROOT}"
log_info "Pipeline log: ${PIPELINE_LOG}"

finalize_run() {
    local exit_code=$?
    trap - EXIT

    log_phase "TRACKER UPDATE"
    if [[ "$ABR_SKIP_TRACKER_UPDATE" == "1" ]]; then
        log_info "Skipping tracker update because ABR_SKIP_TRACKER_UPDATE=1"
    elif (cd "$REPO_ROOT" && python3 "$TRACKER_SCRIPT"); then
        log_info "Experiment tracker saved to ${TRACKER_PATH}"
    else
        log_info "WARNING: experiment tracker update failed"
    fi

    backup_run_artifacts

    exit "$exit_code"
}

trap finalize_run EXIT


# =============================================================================
# PHASE 1: EoH Evolution
# =============================================================================

if [[ "$SKIP_PHASE_1" != "1" ]]; then
    log_phase "PHASE 1: EoH Evolution"

    # --- 3G evolution ---
    log_info "Starting EoH evolution on ABRBench-3G..."
    (
        cd "$ABR_EXAMPLE_DIR"
        DATASET="ABRBench-3G" \
        ABR_OUTPUT_NAME="ABRBench-3G" \
        EC_N_POP="$EC_N_POP" \
        EXP_N_PROC="$EXP_N_PROC" \
        EVA_TIMEOUT="$EVA_TIMEOUT" \
        uv run python runEoH.py
    )
    log_info "3G evolution results available under ${EOH_3G_ROOT}"

    # --- 4G+ evolution ---
    log_info "Starting EoH evolution on ABRBench-4G+..."
    (
        cd "$ABR_EXAMPLE_DIR"
        DATASET="ABRBench-4G+" \
        ABR_OUTPUT_NAME="ABRBench-4G+" \
        EC_N_POP="$EC_N_POP" \
        EXP_N_PROC="$EXP_N_PROC" \
        EVA_TIMEOUT="$EVA_TIMEOUT" \
        uv run python runEoH.py
    )
    log_info "4G+ evolution results available under ${EOH_4G_ROOT}"
else
    log_phase "PHASE 1: SKIPPED (SKIP_PHASE_1=1)"
fi


# =============================================================================
# PHASE 2: SABR Rule-Based Baselines
# =============================================================================

if [[ "$SKIP_PHASE_2" != "1" ]]; then
    log_phase "PHASE 2: SABR Rule-Based Baselines"

    # --- 3G datasets ---
    for ds in "${DATASETS_3G[@]}"; do
        log_info "=== Dataset: ${ds} (3G) ==="
        run_python_baselines "$ds"
        run_cpp_baselines "$ds" "3G"
    done

    # --- 4G+ datasets ---
    for ds in "${DATASETS_4G[@]}"; do
        log_info "=== Dataset: ${ds} (4G+) ==="
        run_python_baselines "$ds"
        run_cpp_baselines "$ds" "4G+"
    done
else
    log_phase "PHASE 2: SKIPPED (SKIP_PHASE_2=1)"
fi


# =============================================================================
# PHASE 3: EoH Heuristic Evaluation
# =============================================================================

if [[ "$SKIP_PHASE_3" != "1" ]]; then
    log_phase "PHASE 3: EoH Heuristic Evaluation"

    # Locate best population files
    BEST_3G_JSON="$(find_best_population "$EOH_3G_ROOT")"
    BEST_4G_JSON="$(find_best_population "$EOH_4G_ROOT")"

    if [[ -z "$BEST_3G_JSON" ]]; then
        log_info "WARNING: No 3G population found — skipping 3G EoH eval"
    else
        log_info "Using 3G heuristic: ${BEST_3G_JSON}"
        for ds in "${DATASETS_3G[@]}"; do
            log_info "Evaluating EoH on ${ds}..."
            EOH_LOG_DIR="$(resolve_eval_log_dir "$REPO_ROOT" "$ds")"
            (cd "$SABR_DIR" && uv run python "$BRIDGE_SCRIPT" \
                --json "$BEST_3G_JSON" --index 0 --dataset "$ds" --log-dir "$EOH_LOG_DIR")
        done
    fi

    if [[ -z "$BEST_4G_JSON" ]]; then
        log_info "WARNING: No 4G+ population found — skipping 4G+ EoH eval"
    else
        log_info "Using 4G+ heuristic: ${BEST_4G_JSON}"
        for ds in "${DATASETS_4G[@]}"; do
            log_info "Evaluating EoH on ${ds}..."
            EOH_LOG_DIR="$(resolve_eval_log_dir "$REPO_ROOT" "$ds")"
            (cd "$SABR_DIR" && uv run python "$BRIDGE_SCRIPT" \
                --json "$BEST_4G_JSON" --index 0 --dataset "$ds" --log-dir "$EOH_LOG_DIR")
        done
    fi
else
    log_phase "PHASE 3: SKIPPED (SKIP_PHASE_3=1)"
fi


# =============================================================================
# PHASE 4: Analysis
# =============================================================================

if [[ "$SKIP_PHASE_4" != "1" ]]; then
    log_phase "PHASE 4: Analysis"

    log_info "Collecting results..."
    (cd "$SABR_DIR" && uv run python "$COLLECT_SCRIPT" \
        --run-id "$ABR_RUN_ID")

    log_info "Generating plots..."
    (cd "$SABR_DIR" && uv run python "$PLOT_SCRIPT" \
        --run-id "$ABR_RUN_ID")

    log_info "Generating run report..."
    (cd "$REPO_ROOT" && python3 "$REPORT_SCRIPT" \
        --run-id "$ABR_RUN_ID")

    log_info "Results saved to ${SUMMARY_CSV}"
    log_info "Plots saved to ${PLOTS_DIR}"
    log_info "Run report saved to ${ANALYSIS_ROOT}/run_report.md"
    log_info "Done!"
else
    log_phase "PHASE 4: SKIPPED (SKIP_PHASE_4=1)"
fi

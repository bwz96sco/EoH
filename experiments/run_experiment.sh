#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# EoH vs SABR Baselines — Full Experiment Pipeline
#
# Phases:
#   1) EoH evolution (ABRBench-3G and ABRBench-4G+)
#   2) SABR rule-based baselines on each individual dataset
#   3) EoH heuristic evaluation via bridge script on each dataset
#   4) Analysis — collect results + plots
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
CONFIG_PY="${SABR_DIR}/config.py"
CONFIG_H="${SABR_DIR}/build_env_c_plus/config.h"

# EoH parameters (override via env vars)
EC_N_POP="${EC_N_POP:-10}"
EXP_N_PROC="${EXP_N_PROC:-4}"
EVA_TIMEOUT="${EVA_TIMEOUT:-120}"

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
    # Find the latest (highest generation) population JSON from archived EoH results.
    # The archived tree mirrors the EoH run folder:
    #   {archive}/config.json
    #   {archive}/results/pops_best/population_generation_<N>.json
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
        EC_N_POP="$EC_N_POP" \
        EXP_N_PROC="$EXP_N_PROC" \
        EVA_TIMEOUT="$EVA_TIMEOUT" \
        uv run python runEoH.py
    )
    # Copy results to a named directory
    EOH_3G_RESULTS="${ABR_EXAMPLE_DIR}/results"
    EOH_3G_ARCHIVE="${REPO_ROOT}/experiments/results/eoh_results_3G"
    if [[ -d "$EOH_3G_RESULTS" ]]; then
        rm -rf "$EOH_3G_ARCHIVE"
        cp -r "$EOH_3G_RESULTS" "$EOH_3G_ARCHIVE"
        log_info "3G evolution results archived to ${EOH_3G_ARCHIVE}"
    fi

    # --- 4G+ evolution ---
    log_info "Starting EoH evolution on ABRBench-4G+..."
    (
        cd "$ABR_EXAMPLE_DIR"
        DATASET="ABRBench-4G+" \
        EC_N_POP="$EC_N_POP" \
        EXP_N_PROC="$EXP_N_PROC" \
        EVA_TIMEOUT="$EVA_TIMEOUT" \
        uv run python runEoH.py
    )
    EOH_4G_RESULTS="${ABR_EXAMPLE_DIR}/results"
    EOH_4G_ARCHIVE="${REPO_ROOT}/experiments/results/eoh_results_4G+"
    if [[ -d "$EOH_4G_RESULTS" ]]; then
        rm -rf "$EOH_4G_ARCHIVE"
        cp -r "$EOH_4G_RESULTS" "$EOH_4G_ARCHIVE"
        log_info "4G+ evolution results archived to ${EOH_4G_ARCHIVE}"
    fi
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
    EOH_3G_ARCHIVE="${REPO_ROOT}/experiments/results/eoh_results_3G"
    EOH_4G_ARCHIVE="${REPO_ROOT}/experiments/results/eoh_results_4G+"
    BEST_3G_JSON="$(find_best_population "$EOH_3G_ARCHIVE")"
    BEST_4G_JSON="$(find_best_population "$EOH_4G_ARCHIVE")"

    if [[ -z "$BEST_3G_JSON" ]]; then
        log_info "WARNING: No 3G population found — skipping 3G EoH eval"
    else
        log_info "Using 3G heuristic: ${BEST_3G_JSON}"
        for ds in "${DATASETS_3G[@]}"; do
            log_info "Evaluating EoH on ${ds}..."
            (cd "$SABR_DIR" && uv run python "$BRIDGE_SCRIPT" \
                --json "$BEST_3G_JSON" --index 0 --dataset "$ds")
        done
    fi

    if [[ -z "$BEST_4G_JSON" ]]; then
        log_info "WARNING: No 4G+ population found — skipping 4G+ EoH eval"
    else
        log_info "Using 4G+ heuristic: ${BEST_4G_JSON}"
        for ds in "${DATASETS_4G[@]}"; do
            log_info "Evaluating EoH on ${ds}..."
            (cd "$SABR_DIR" && uv run python "$BRIDGE_SCRIPT" \
                --json "$BEST_4G_JSON" --index 0 --dataset "$ds")
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
        --output "${REPO_ROOT}/experiments/results/results_summary.csv")

    log_info "Generating plots..."
    (cd "$SABR_DIR" && uv run python "$PLOT_SCRIPT" \
        --output-dir "${REPO_ROOT}/experiments/results/plots")

    log_info "Results saved to experiments/results/results_summary.csv"
    log_info "Plots saved to experiments/results/plots"
    log_info "Done!"
else
    log_phase "PHASE 4: SKIPPED (SKIP_PHASE_4=1)"
fi

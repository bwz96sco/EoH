#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Single-target ABR experiment runner
#
# Runs one EoH evolution target and evaluates the resulting heuristic on a
# configurable dataset list. Baseline logs are reused from env/SABR/test_results;
# only sim_eoh logs are written into the canonical run-local tree.
#
# Required env:
#   ABR_EOH_DATASET      Evolution dataset, e.g. FCC-18 or ABRBench-3G
#
# Optional env:
#   ABR_EVAL_DATASETS    Comma-separated eval datasets. Defaults to the target's suite.
#   ABR_OUTPUT_NAME      Output name under experiments/results/<run-id>/raw/eoh/
#   ABR_SEED_NAME        Comma-separated seed name(s) passed through to examples/user_abr/runEoH.py
#   ABR_SEED_INDEX       Comma-separated seed index(es) passed through to examples/user_abr/runEoH.py
#   ABR_RUN_LABEL        Canonical run label if ABR_RUN_ID is unset
#   ABR_SKIP_TRACKER_UPDATE=1
#   SKIP_PHASE_1=1 | SKIP_PHASE_3=1 | SKIP_PHASE_4=1
# =============================================================================

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SABR_DIR="${REPO_ROOT}/env/SABR"
ABR_EXAMPLE_DIR="${REPO_ROOT}/examples/user_abr"
BRIDGE_SCRIPT="${SABR_DIR}/eval_eoh_in_sabr.py"
COLLECT_SCRIPT="${REPO_ROOT}/experiments/collect_results.py"
PLOT_SCRIPT="${REPO_ROOT}/experiments/plot_results.py"
REPORT_SCRIPT="${REPO_ROOT}/experiments/generate_run_report.py"
GLOBAL_TRACKER_SCRIPT="${REPO_ROOT}/experiments/update_global_tracker.py"
BACKUP_CONFIG="${REPO_ROOT}/experiments/private/backup.env"

if [[ -f "$BACKUP_CONFIG" ]]; then
    # shellcheck source=/dev/null
    source "$BACKUP_CONFIG"
fi

ABR_EOH_DATASET="${ABR_EOH_DATASET:-}"
ABR_OUTPUT_NAME="${ABR_OUTPUT_NAME:-${ABR_EOH_DATASET}}"
ABR_SKIP_TRACKER_UPDATE="${ABR_SKIP_TRACKER_UPDATE:-0}"

EC_N_POP="${EC_N_POP:-10}"
EXP_N_PROC="${EXP_N_PROC:-4}"
EVA_TIMEOUT="${EVA_TIMEOUT:-120}"
ABR_BACKUP_REMOTE="${ABR_BACKUP_REMOTE:-${ABR_BACKUP_REMOTE_DEFAULT:-}}"
ABR_BACKUP_SEED_CACHE="${ABR_BACKUP_SEED_CACHE:-${ABR_BACKUP_SEED_CACHE_DEFAULT:-0}}"
ABR_RECORD_EXPERIMENT="${ABR_RECORD_EXPERIMENT:-1}"

SKIP_PHASE_1="${SKIP_PHASE_1:-0}"
SKIP_PHASE_3="${SKIP_PHASE_3:-0}"
SKIP_PHASE_4="${SKIP_PHASE_4:-0}"

DATASETS_3G=("FCC-16" "FCC-18" "Oboe" "Puffer-21" "Puffer-22" "HSR")
DATASETS_4G=("Norway3G" "Lumos4G" "Lumos5G" "SolisWi-Fi" "Ghent" "Lab")

log_info()  { echo ">>> [$(date '+%H:%M:%S')] $*"; }
log_phase() { echo ""; echo "========== $* =========="; echo ""; }

if [[ -z "$ABR_EOH_DATASET" ]]; then
    echo "ABR_EOH_DATASET is required" >&2
    exit 1
fi

dataset_suite_name() {
    case "$1" in
        "FCC-16"|"FCC-18"|"Oboe"|"Puffer-21"|"Puffer-22"|"HSR"|"ABRBench-3G")
            echo "ABRBench-3G"
            ;;
        "Norway3G"|"Lumos4G"|"Lumos5G"|"SolisWi-Fi"|"Ghent"|"Lab"|"ABRBench-4G+")
            echo "ABRBench-4G+"
            ;;
        *)
            echo "Unknown dataset: $1" >&2
            return 1
            ;;
    esac
}

default_eval_datasets() {
    local dataset="$1"
    local suite
    suite="$(dataset_suite_name "$dataset")"

    if [[ "$suite" == "ABRBench-3G" ]]; then
        printf '%s\n' "${DATASETS_3G[@]}"
    else
        printf '%s\n' "${DATASETS_4G[@]}"
    fi
}

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

should_backup_run_artifacts() {
    local run_name
    run_name="$(basename "$RUN_ROOT")"

    if [[ "$ABR_RECORD_EXPERIMENT" != "1" ]]; then
        log_info "Backup skip: ABR_RECORD_EXPERIMENT=${ABR_RECORD_EXPERIMENT}"
        return 1
    fi

    if [[ "$SKIP_PHASE_3" == "1" || "$SKIP_PHASE_4" == "1" ]]; then
        log_info "Backup skip: partial run (SKIP_PHASE_3=${SKIP_PHASE_3}, SKIP_PHASE_4=${SKIP_PHASE_4})"
        return 1
    fi

    if printf '%s\n' "$run_name" | tr '[:upper:]' '[:lower:]' | grep -Eq '(^|[-_])(smoke|probe)([-_]|$)'; then
        log_info "Backup skip: non-canonical smoke/probe run (${run_name})"
        return 1
    fi

    return 0
}

backup_run_artifacts() {
    if [[ -z "$ABR_BACKUP_REMOTE" ]]; then
        return 0
    fi

    if ! should_backup_run_artifacts; then
        return 0
    fi

    log_phase "BACKUP"

    if ! command -v rclone >/dev/null 2>&1; then
        log_info "WARNING: ABR_BACKUP_REMOTE is set but rclone is not installed"
        return 0
    fi

    backup_path_if_present "$RUN_ROOT" "${ABR_BACKUP_REMOTE%/}/experiments/results/${ABR_RUN_ID}" || \
        log_info "WARNING: failed to back up canonical run root"

    if [[ "$ABR_BACKUP_SEED_CACHE" == "1" ]]; then
        backup_path_if_present "$ABR_EXAMPLE_DIR/seed_cache" "${ABR_BACKUP_REMOTE%/}/examples/user_abr/seed_cache" || \
            log_info "WARNING: failed to back up seed cache"
    fi
}

resolve_run_layout() {
    local repo_root="$1"
    python3 - "$repo_root" "$ABR_OUTPUT_NAME" <<'PY'
from pathlib import Path
import os
import sys

repo_root = Path(sys.argv[1])
output_name = sys.argv[2]
sys.path.insert(0, str(repo_root / "experiments"))

from run_layout import (
    build_analysis_csv_path,
    build_eoh_output_root,
    build_log_path,
    build_plots_dir,
    build_run_layout,
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
print(build_eoh_output_root(repo_root, output_name=output_name, run_id=layout.run_id))
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

find_best_population() {
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

if [[ "$#" -ne 9 ]]; then
    echo "Failed to resolve canonical ABR run layout" >&2
    exit 1
fi

ABR_RUN_ID="$1"
RUN_ROOT="$2"
RAW_ROOT="$3"
ANALYSIS_ROOT="$4"
LOGS_ROOT="$5"
EOH_TARGET_ROOT="$6"
SUMMARY_CSV="$7"
PLOTS_DIR="$8"
PIPELINE_LOG="$9"
export ABR_RUN_ID

if [[ -n "${ABR_EVAL_DATASETS:-}" ]]; then
    IFS=',' read -r -a EVAL_DATASETS <<< "$ABR_EVAL_DATASETS"
else
    OLD_IFS="$IFS"
    IFS=$'\n'
    EVAL_DATASETS=($(default_eval_datasets "$ABR_EOH_DATASET"))
    IFS="$OLD_IFS"
fi

mkdir -p "$RAW_ROOT" "$ANALYSIS_ROOT" "$LOGS_ROOT"
exec > >(tee -a "$PIPELINE_LOG") 2>&1

log_info "ABR run id: ${ABR_RUN_ID}"
log_info "Canonical run root: ${RUN_ROOT}"
log_info "EoH dataset: ${ABR_EOH_DATASET}"
if [[ -n "${ABR_SEED_NAME:-}" ]]; then
    log_info "Seed name filter: ${ABR_SEED_NAME}"
fi
if [[ -n "${ABR_SEED_INDEX:-}" ]]; then
    log_info "Seed index filter: ${ABR_SEED_INDEX}"
fi
log_info "Output name: ${ABR_OUTPUT_NAME}"
log_info "Eval datasets: ${EVAL_DATASETS[*]}"
log_info "Raw outputs: ${RAW_ROOT}"
log_info "Analysis outputs: ${ANALYSIS_ROOT}"
log_info "Pipeline log: ${PIPELINE_LOG}"

# Register experiment in global tracker
ABR_CAMPAIGN="${ABR_CAMPAIGN:-}"
python3 "$GLOBAL_TRACKER_SCRIPT" \
    --register "$ABR_RUN_ID" \
    --target "$ABR_EOH_DATASET" \
    --campaign "$ABR_CAMPAIGN" \
    --status running 2>/dev/null || true

finalize_run() {
    local exit_code=$?
    trap - EXIT

    log_phase "TRACKER UPDATE"
    if [[ "$ABR_SKIP_TRACKER_UPDATE" == "1" ]]; then
        log_info "Skipping tracker update because ABR_SKIP_TRACKER_UPDATE=1"
    else
        if (cd "$REPO_ROOT" && python3 "$GLOBAL_TRACKER_SCRIPT" --complete "$ABR_RUN_ID"); then
            log_info "Global tracker updated for ${ABR_RUN_ID}"
        else
            log_info "WARNING: global tracker update failed"
        fi
    fi

    backup_run_artifacts

    exit "$exit_code"
}

trap finalize_run EXIT

if [[ "$SKIP_PHASE_1" != "1" ]]; then
    log_phase "PHASE 1: EoH Evolution"
    log_info "Starting EoH evolution on ${ABR_EOH_DATASET}..."
    (
        cd "$ABR_EXAMPLE_DIR"
        DATASET="$ABR_EOH_DATASET" \
        ABR_OUTPUT_NAME="$ABR_OUTPUT_NAME" \
        EC_N_POP="$EC_N_POP" \
        EXP_N_PROC="$EXP_N_PROC" \
        EVA_TIMEOUT="$EVA_TIMEOUT" \
        uv run python runEoH.py
    )
    log_info "Evolution results available under ${EOH_TARGET_ROOT}"
else
    log_phase "PHASE 1: SKIPPED (SKIP_PHASE_1=1)"
fi

if [[ "$SKIP_PHASE_3" != "1" ]]; then
    log_phase "PHASE 3: EoH Heuristic Evaluation"

    BEST_JSON="$(find_best_population "$EOH_TARGET_ROOT")"
    if [[ -z "$BEST_JSON" ]]; then
        log_info "WARNING: No population found for ${ABR_EOH_DATASET} — skipping EoH eval"
    else
        log_info "Using heuristic: ${BEST_JSON}"
        for ds in "${EVAL_DATASETS[@]}"; do
            log_info "Evaluating EoH on ${ds}..."
            EOH_LOG_DIR="$(resolve_eval_log_dir "$REPO_ROOT" "$ds")"
            (cd "$SABR_DIR" && uv run python "$BRIDGE_SCRIPT" \
                --json "$BEST_JSON" --index 0 --dataset "$ds" --log-dir "$EOH_LOG_DIR")
        done
    fi
else
    log_phase "PHASE 3: SKIPPED (SKIP_PHASE_3=1)"
fi

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

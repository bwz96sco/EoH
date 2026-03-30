#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Full ABR impact wave runner
#
# Runs the combined dataset-impact and seed-impact study using the canonical
# single-target runner. Stage A performs phase-1-only evolution. Stage B resumes
# the same run ids for evaluation and analysis.
#
# Usage:
#   bash experiments/run_full_impact_wave.sh [wave-id]
#
# Optional env:
#   MAX_PARALLEL            Concurrent jobs across the wave. Default: 2
#   DATASET_TARGETS_CSV     Override dataset-impact target list
#   SEED_TARGETS_CSV        Override seed-impact target list
#   SEEDS_CSV               Override seed names
#   ABR_WAVE_BACKUP_REMOTE  Override backup destination for child runs
# =============================================================================

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

WAVE_ID="${1:-$(date +%Y%m%d-%H%M%S)-full-impact}"
MAX_PARALLEL="${MAX_PARALLEL:-2}"
ABR_WAVE_BACKUP_REMOTE="${ABR_WAVE_BACKUP_REMOTE:-$REPO_ROOT/_backup/$WAVE_ID}"

WAVE_ROOT="$REPO_ROOT/experiments/results/_waves/$WAVE_ID"
LOG_DIR="$WAVE_ROOT/logs"
mkdir -p "$LOG_DIR"

ORCH_LOG="$LOG_DIR/orchestrator.log"
STAGEA_QUEUE="$WAVE_ROOT/stageA.queue"
STAGEA_OK="$WAVE_ROOT/stageA.ok"
STAGEA_FAIL="$WAVE_ROOT/stageA.fail"
STAGEB_QUEUE="$WAVE_ROOT/stageB.queue"
STAGEB_OK="$WAVE_ROOT/stageB.ok"
STAGEB_FAIL="$WAVE_ROOT/stageB.fail"
TRACKER_LOG="$LOG_DIR/tracker.log"

: > "$ORCH_LOG"
: > "$STAGEA_QUEUE"
: > "$STAGEA_OK"
: > "$STAGEA_FAIL"
: > "$STAGEB_QUEUE"
: > "$STAGEB_OK"
: > "$STAGEB_FAIL"
: > "$TRACKER_LOG"

timestamp() {
    date '+%F %T'
}

log() {
    echo "[$(timestamp)] $*" | tee -a "$ORCH_LOG"
}

slug() {
    printf '%s' "$1" \
        | tr '[:upper:]' '[:lower:]' \
        | sed -e 's/+/-plus/g' -e 's#[^a-z0-9._-]#-#g' -e 's/--*/-/g' -e 's/^-//' -e 's/-$//'
}

split_csv_into_array() {
    local value="$1"
    local -n out_ref="$2"
    local old_ifs="$IFS"
    IFS=','
    read -r -a out_ref <<< "$value"
    IFS="$old_ifs"
}

suite_csv_for_target() {
    case "$1" in
        FCC-16|FCC-18|Oboe|Puffer-21|Puffer-22|HSR|ABRBench-3G)
            printf '%s' 'FCC-16,FCC-18,Oboe,Puffer-21,Puffer-22,HSR'
            ;;
        Norway3G|Lumos4G|Lumos5G|SolisWi-Fi|Ghent|Lab|ABRBench-4G+)
            printf '%s' 'Norway3G,Lumos4G,Lumos5G,SolisWi-Fi,Ghent,Lab'
            ;;
        *)
            echo "Unknown target: $1" >&2
            return 1
            ;;
    esac
}

has_best_population() {
    local run_id="$1"
    find "$REPO_ROOT/experiments/results/$run_id/raw/eoh" \
        -path '*/results/pops_best/population_generation_*.json' \
        -type f -print -quit 2>/dev/null | grep -q .
}

stage_b_complete() {
    local run_id="$1"
    [[ -f "$REPO_ROOT/experiments/results/$run_id/analysis/results_summary.csv" ]] \
        && [[ -f "$REPO_ROOT/experiments/results/$run_id/analysis/run_report.md" ]]
}

run_stage_a() {
    local kind="$1"
    local run_id="$2"
    local target="$3"
    local output_name="$4"
    local eval_csv="$5"
    local seed_name="$6"
    local job_log="$LOG_DIR/$run_id.stage1.log"

    log "STAGE A start kind=$kind run=$run_id target=$target seed=${seed_name:-all}"

    local status=0
    if (
        set -euo pipefail
        cd "$REPO_ROOT"
        export PYTHONUNBUFFERED=1
        export ABR_SKIP_TRACKER_UPDATE=1
        export ABR_BACKUP_REMOTE="$ABR_WAVE_BACKUP_REMOTE"
        export ABR_BACKUP_SEED_CACHE=0
        export ABR_RUN_ID="$run_id"
        export ABR_EOH_DATASET="$target"
        export ABR_OUTPUT_NAME="$output_name"
        export ABR_EVAL_DATASETS="$eval_csv"
        if [[ -n "$seed_name" ]]; then
            export ABR_SEED_NAME="$seed_name"
        fi
        export SKIP_PHASE_3=1
        export SKIP_PHASE_4=1
        bash experiments/run_eoh_target_experiment.sh
    ) >> "$job_log" 2>&1; then
        status=0
    else
        status=$?
    fi

    if [[ $status -eq 0 ]] && has_best_population "$run_id"; then
        printf '%s|%s|%s|%s|%s|%s\n' "$kind" "$run_id" "$target" "$output_name" "$eval_csv" "$seed_name" >> "$STAGEA_OK"
        printf '%s|%s|%s|%s|%s|%s\n' "$kind" "$run_id" "$target" "$output_name" "$eval_csv" "$seed_name" >> "$STAGEB_QUEUE"
        log "STAGE A ok run=$run_id"
    else
        printf '%s|%s|%s|%s|%s|%s\n' "$kind" "$run_id" "$target" "$output_name" "$eval_csv" "$seed_name" >> "$STAGEA_FAIL"
        log "STAGE A fail run=$run_id status=$status"
    fi
}

run_stage_b() {
    local kind="$1"
    local run_id="$2"
    local target="$3"
    local output_name="$4"
    local eval_csv="$5"
    local seed_name="$6"
    local job_log="$LOG_DIR/$run_id.stage2.log"

    log "STAGE B start kind=$kind run=$run_id target=$target seed=${seed_name:-all}"

    local status=0
    if (
        set -euo pipefail
        cd "$REPO_ROOT"
        export PYTHONUNBUFFERED=1
        export ABR_SKIP_TRACKER_UPDATE=1
        export ABR_BACKUP_REMOTE="$ABR_WAVE_BACKUP_REMOTE"
        export ABR_BACKUP_SEED_CACHE=0
        export ABR_RUN_ID="$run_id"
        export ABR_EOH_DATASET="$target"
        export ABR_OUTPUT_NAME="$output_name"
        export ABR_EVAL_DATASETS="$eval_csv"
        if [[ -n "$seed_name" ]]; then
            export ABR_SEED_NAME="$seed_name"
        fi
        export SKIP_PHASE_1=1
        bash experiments/run_eoh_target_experiment.sh
    ) >> "$job_log" 2>&1; then
        status=0
    else
        status=$?
    fi

    if [[ $status -eq 0 ]] && stage_b_complete "$run_id"; then
        printf '%s|%s|%s|%s|%s|%s\n' "$kind" "$run_id" "$target" "$output_name" "$eval_csv" "$seed_name" >> "$STAGEB_OK"
        log "STAGE B ok run=$run_id"
    else
        printf '%s|%s|%s|%s|%s|%s\n' "$kind" "$run_id" "$target" "$output_name" "$eval_csv" "$seed_name" >> "$STAGEB_FAIL"
        log "STAGE B fail run=$run_id status=$status"
    fi
}

wait_for_slot() {
    while [[ "$(jobs -rp | wc -l | tr -d ' ')" -ge "$MAX_PARALLEL" ]]; do
        sleep 10
    done
}

launch_queue() {
    local stage="$1"
    local queue_file="$2"
    while IFS='|' read -r kind run_id target output_name eval_csv seed_name; do
        [[ -z "$run_id" ]] && continue
        wait_for_slot
        if [[ "$stage" == "A" ]]; then
            run_stage_a "$kind" "$run_id" "$target" "$output_name" "$eval_csv" "$seed_name" &
        else
            run_stage_b "$kind" "$run_id" "$target" "$output_name" "$eval_csv" "$seed_name" &
        fi
    done < "$queue_file"
    wait
}

DATASET_TARGETS_CSV="${DATASET_TARGETS_CSV:-FCC-16,FCC-18,Oboe,Puffer-21,Puffer-22,Norway3G,Lumos4G,Lumos5G,SolisWi-Fi}"
SEED_TARGETS_CSV="${SEED_TARGETS_CSV:-ABRBench-3G,ABRBench-4G+}"
SEEDS_CSV="${SEEDS_CSV:-bb,bola,quetra,robust_mpc,rate_based}"

split_csv_into_array "$DATASET_TARGETS_CSV" DATASET_TARGETS
split_csv_into_array "$SEED_TARGETS_CSV" SEED_TARGETS
split_csv_into_array "$SEEDS_CSV" SEEDS

for target in "${DATASET_TARGETS[@]}"; do
    run_id="$WAVE_ID-dataset-$(slug "$target")"
    eval_csv="$(suite_csv_for_target "$target")"
    printf 'dataset|%s|%s|%s|%s|\n' "$run_id" "$target" "$target" "$eval_csv" >> "$STAGEA_QUEUE"
done

for target in "${SEED_TARGETS[@]}"; do
    eval_csv="$(suite_csv_for_target "$target")"
    for seed in "${SEEDS[@]}"; do
        run_id="$WAVE_ID-seed-$(slug "$target")-$seed"
        printf 'seed|%s|%s|%s|%s|%s\n' "$run_id" "$target" "$target" "$eval_csv" "$seed" >> "$STAGEA_QUEUE"
    done
done

log "Wave $WAVE_ID prepared"
log "Stage A queue size: $(wc -l < "$STAGEA_QUEUE" | tr -d ' ')"
log "Max parallel jobs: $MAX_PARALLEL"
log "Stage A begin"
launch_queue A "$STAGEA_QUEUE"
log "Stage A complete: ok=$(wc -l < "$STAGEA_OK" | tr -d ' ') fail=$(wc -l < "$STAGEA_FAIL" | tr -d ' ')"

if [[ ! -s "$STAGEB_QUEUE" ]]; then
    log "No Stage B jobs queued because all Stage A jobs failed"
    exit 1
fi

log "Stage B begin"
launch_queue B "$STAGEB_QUEUE"
log "Stage B complete: ok=$(wc -l < "$STAGEB_OK" | tr -d ' ') fail=$(wc -l < "$STAGEB_FAIL" | tr -d ' ')"

log "Final tracker update begin"
if python3 experiments/update_experiment_tracker.py >> "$TRACKER_LOG" 2>&1; then
    log "Final tracker update ok"
else
    log "Final tracker update failed"
fi

log "Wave $WAVE_ID finished"

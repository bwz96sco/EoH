#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Improvement experiments for ABR 3G performance — v2
#
# Based on analysis findings:
#   - pop_size=1 + single seed dramatically outperforms pop_size=5 + all seeds
#   - rate_based seed is the best single-seed performer (QoE ~54 on 3G)
#   - CVaR fitness can help but requires seed re-evaluation (fixed in runEoH.py)
#   - Server pop5 experiments already running; local experiments focus on
#     fitness modes with the proven best config (pop1 + rate_based)
#
# Track A: Pop-size sweep with rate_based seed (pop2, pop3)
# Track B: Fitness mode experiments on the best config (pop1 + rate_based)
# Track C: CVaR with pop5 + all seeds (tests the seed re-eval fix)
#
# Usage:
#   bash experiments/run_improvement_experiments.sh [wave-id]
#
# Optional env:
#   MAX_PARALLEL   Concurrent jobs. Default: 2
#   TRACK          "A", "B", "C", or any combination (default: "ABC")
# =============================================================================

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

WAVE_ID="${1:-$(date +%Y%m%d-%H%M%S)-improvement}"
MAX_PARALLEL="${MAX_PARALLEL:-2}"
TRACK="${TRACK:-ABC}"

LOG_DIR="$REPO_ROOT/experiments/results/_waves/$WAVE_ID/logs"
mkdir -p "$LOG_DIR"
ORCH_LOG="$LOG_DIR/orchestrator.log"
: > "$ORCH_LOG"

log() { echo "[$(date '+%F %T')] $*" | tee -a "$ORCH_LOG"; }

PIDS=()
LABELS=()

wait_for_slot() {
    while true; do
        local running=0
        for pid in "${PIDS[@]+"${PIDS[@]}"}"; do
            [[ -z "$pid" ]] && continue
            kill -0 "$pid" 2>/dev/null && ((running++)) || true
        done
        [[ "$running" -lt "$MAX_PARALLEL" ]] && break
        sleep 15
    done
}

launch() {
    local label="$1"; shift
    local job_log="$LOG_DIR/${label}.log"
    wait_for_slot
    log "LAUNCH $label"
    (
        set -euo pipefail
        cd "$REPO_ROOT"
        "$@"
    ) > "$job_log" 2>&1 &
    PIDS+=($!)
    LABELS+=("$label")
}

run_target() {
    local run_id="$1"
    local dataset="$2"
    local pop_size="$3"
    local seed_name="${4:-}"
    local fitness_mode="${5:-mean}"
    local std_weight="${6:-1.0}"

    export ABR_RUN_ID="$run_id"
    export ABR_EOH_DATASET="$dataset"
    export ABR_OUTPUT_NAME="$dataset"
    export ABR_SKIP_TRACKER_UPDATE=1
    export ABR_RECORD_EXPERIMENT=1
    export EC_POP_SIZE="$pop_size"
    export ABR_FITNESS_MODE="$fitness_mode"
    export ABR_FITNESS_STD_WEIGHT="$std_weight"

    if [[ -n "$seed_name" ]]; then
        export ABR_SEED_NAME="$seed_name"
    else
        unset ABR_SEED_NAME 2>/dev/null || true
    fi

    bash experiments/run_eoh_target_experiment.sh
}

# ============ Track A: Pop-size sweep (rate_based seed) ============
if [[ "$TRACK" == *A* ]]; then
    log "=== TRACK A: Pop-size sweep with rate_based seed ==="

    # pop_size=2 with rate_based seed
    launch "pop2-rate_based-3g" \
        run_target "${WAVE_ID}-pop2-rate_based-3g" "ABRBench-3G" 2 "rate_based" "mean"

    # pop_size=3 with rate_based seed
    launch "pop3-rate_based-3g" \
        run_target "${WAVE_ID}-pop3-rate_based-3g" "ABRBench-3G" 3 "rate_based" "mean"
fi

# ============ Track B: Fitness mode with best config (pop1+rate_based) ============
if [[ "$TRACK" == *B* ]]; then
    log "=== TRACK B: Fitness mode experiments (pop1 + rate_based) ==="

    # CVaR-25% with pop_size=1, rate_based seed
    launch "cvar25-pop1-rate_based-3g" \
        run_target "${WAVE_ID}-cvar25-pop1-rate_based-3g" "ABRBench-3G" 1 "rate_based" "cvar_25"

    # CVaR-10% with pop_size=1, rate_based seed
    launch "cvar10-pop1-rate_based-3g" \
        run_target "${WAVE_ID}-cvar10-pop1-rate_based-3g" "ABRBench-3G" 1 "rate_based" "cvar_10"

    # mean-std with pop_size=1, rate_based seed
    launch "meanstd-pop1-rate_based-3g" \
        run_target "${WAVE_ID}-meanstd-pop1-rate_based-3g" "ABRBench-3G" 1 "rate_based" "mean_std" "1.0"
fi

# ============ Track C: CVaR with pop5+all seeds (test seed re-eval fix) ============
if [[ "$TRACK" == *C* ]]; then
    log "=== TRACK C: CVaR with pop5 + all seeds (seed re-eval fix test) ==="

    # CVaR-25% with pop_size=5, all seeds — tests that seed re-evaluation fix works
    launch "cvar25-pop5-all-3g" \
        run_target "${WAVE_ID}-cvar25-pop5-all-3g" "ABRBench-3G" 5 "" "cvar_25"
fi

# ============ Wait for all ============
log "Waiting for all jobs to complete..."
FAILED=0
for i in "${!PIDS[@]+"${!PIDS[@]}"}"; do
    [[ -z "$i" ]] && continue
    if wait "${PIDS[$i]}"; then
        log "OK ${LABELS[$i]}"
    else
        log "FAIL ${LABELS[$i]} (exit=$?)"
        ((FAILED++))
    fi
done

# ============ Tracker update ============
log "Final tracker update..."
python3 experiments/update_global_tracker.py --scan || log "WARNING: tracker update failed"

log "Wave $WAVE_ID complete. Failed: $FAILED / ${#PIDS[@]+"${#PIDS[@]}"}"

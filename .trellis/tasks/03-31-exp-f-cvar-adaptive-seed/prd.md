# Experiment F: CVaR Fitness + Adaptive Seed Heuristic for 3G ABR

## Background

Previous round of 3 experiments all failed to improve 3G QoE beyond the baseline of 87.0. Key findings:

- Training fitness improved but test QoE decreased -> overfitting
- The evolved heuristic uses extreme conservatism (`safety * 0.5` scaling predicted throughput to 5% of harmonic mean)
- The LLM lacks understanding of 3G bandwidth distribution and tends toward uniform pessimism
- CVaR fitness modes exist in `prob.py` but were never tested

This is the **lightweight control experiment** for Experiment D. Same CVaR fitness, but with small population (5) and focus on better seed + prompt guidance.

## Objective

1. **CVaR-25 fitness**: Same as Experiment D, optimize worst 25% of per-video QoEs
2. **Adaptive seed heuristic**: Hand-crafted heuristic that demonstrates bandwidth-regime-aware behavior (the pattern evolution fails to discover on its own)
3. **Enhanced prompt guidance**: Tell the LLM specifically about 3G challenges and the importance of being adaptive rather than uniformly conservative

## Changes Required

### 1. Configure CVaR-25 fitness mode via `.env`

```
ABR_FITNESS_MODE=cvar_25
```

Same mechanism as Experiment D. The existing `_aggregate_qoe()` in `prob.py` handles this.

### 2. Add adaptive bandwidth-regime seed heuristic

Add to `seed_heuristics.py` a new seed named `"adaptive_regime"` that implements:

```python
def score(state, ctx):
    """Adaptive regime: detect bandwidth conditions and adjust strategy accordingly."""
    bitrates = np.asarray(ctx.get("bitrates_kbps", []), dtype=float).reshape(-1)
    k = int(bitrates.size)
    if k == 0:
        return np.array([], dtype=float)

    # Throughput estimation: EWMA with alpha=0.3
    hist_mbps = np.asarray(state.get("throughput_hist_mbps", []), dtype=float)
    hist_mbps = hist_mbps[np.isfinite(hist_mbps)]
    if hist_mbps.size == 0:
        pred_kbps = float(bitrates[0])  # fallback to lowest
    elif hist_mbps.size == 1:
        pred_kbps = float(hist_mbps[0]) * 1000.0
    else:
        alpha = 0.3
        ewma = float(hist_mbps[0])
        for val in hist_mbps[1:]:
            ewma = alpha * float(val) + (1 - alpha) * ewma
        pred_kbps = ewma * 1000.0

    buffer_s = float(state.get("buffer_s", 0.0))
    buffer_max_s = float(ctx.get("buffer_max_s", 60.0))
    buffer_ratio = buffer_s / max(buffer_max_s, 1.0)

    max_bitrate = float(bitrates[-1])
    bw_ratio = pred_kbps / max(max_bitrate, 1.0)

    # Regime detection
    if bw_ratio > 1.5:
        # HIGH bandwidth: buffer is healthy relative to demand -> be aggressive
        safety = 0.9
    elif bw_ratio > 0.8:
        # MEDIUM bandwidth: can sustain mid-range bitrates -> moderate
        safety = 0.75 if buffer_ratio > 0.3 else 0.6
    else:
        # LOW bandwidth: tight margin -> buffer-adaptive conservatism
        if buffer_ratio > 0.5:
            safety = 0.7  # buffer is healthy, can risk a bit
        elif buffer_ratio > 0.2:
            safety = 0.5  # moderate buffer, be careful
        else:
            safety = 0.3  # low buffer, be very conservative

    safe_bw = pred_kbps * safety

    # Score: prefer highest bitrate under safe bandwidth, penalize overshoot
    excess = np.maximum(bitrates - safe_bw, 0.0)
    return bitrates / 1000.0 - 10.0 * (excess / max(safe_bw, 1.0)) ** 2
```

This seed demonstrates the key pattern:
- Detect bandwidth regime (high/medium/low relative to max bitrate)
- Use buffer level as confidence signal
- Be aggressive when conditions allow, conservative only when necessary
- Never uniformly pessimistic

### 3. Enhanced prompt guidance in `prompts.py`

Add to `prompt_other_inf`:

```python
"IMPORTANT: For low-bandwidth scenarios (3G networks where bandwidth is similar to max bitrate), "
"avoid being uniformly conservative. A good heuristic should be ADAPTIVE: "
"- When buffer is healthy (>30% of max), it's safe to pick higher bitrates even with uncertain bandwidth. "
"- When buffer is low (<15% of max), be conservative to avoid rebuffering. "
"- The worst strategy is always picking the lowest bitrate — it wastes bandwidth and scores poorly on easier traces. "
"- Think of it as a risk-reward tradeoff: the buffer is your safety margin. "
"This optimization focuses on WORST-CASE trace performance (CVaR), not just average. "
"A heuristic that performs decently on ALL traces beats one that's great on easy traces but terrible on hard ones."
```

### 4. Keep population size at 5

Standard `EC_POP_SIZE=5` (default). This is the control group — comparing whether CVaR + good seed is enough, or whether larger population (Experiment D) is also needed.

### 5. Ensure no file hardlink issues

Same prevention as Experiment D:
- Break hardlinks on `.env` and seed cache after worktree creation
- Verify inode independence with `ls -i`

## Files to Modify

| File | Change |
|------|--------|
| `examples/user_abr/.env` | Add `ABR_FITNESS_MODE=cvar_25`, ensure `EC_N_POP=10` |
| `examples/user_abr/seed_heuristics.py` | Add `adaptive_regime` seed heuristic |
| `examples/user_abr/prompts.py` | Add 3G-specific adaptive strategy guidance + CVaR note |

## .env Configuration (complete)

```
DATASET=ABRBench-3G
ABR_FITNESS_MODE=cvar_25
EC_N_POP=10
EXP_N_PROC=4
EVA_TIMEOUT=300
LLM_REQUEST_TIMEOUT_S=300
LLM_TOTAL_TIMEOUT_S=600
```

(EC_POP_SIZE not set -> defaults to len(seeds) = 6 after adding adaptive_regime)

## Acceptance Criteria

1. `seed_heuristics.py` has a new `adaptive_regime` seed that demonstrates bandwidth-regime-aware behavior
2. `.env` is configured with `ABR_FITNESS_MODE=cvar_25`
3. `prompts.py` includes guidance about adaptive strategy, buffer-as-confidence, and CVaR optimization
4. The code runs correctly with `uv run python examples/user_abr/runEoH.py` (seed evaluation phase)
5. No hardlinked files in the worktree
6. Pop size is 6 (5 original + 1 adaptive_regime)

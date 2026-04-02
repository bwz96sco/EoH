# Anti-Conservatism Fitness Constraint for 3G ABR

## Background

EoH evolves ABR heuristics by minimizing negative QoE. On ABRBench-3G, the evolution often converges to overly conservative strategies that always pick the lowest bitrate to avoid rebuffering. While this avoids catastrophic rebuffering on the worst training traces, it severely under-utilizes bandwidth on moderate/good traces, losing ~4 QoE points per chunk.

Current fitness in `prob.py` is purely `_aggregate_qoe()` which is mean (or CVaR/mean_std) of per-video total QoE. There's no explicit penalty for bandwidth under-utilization. A heuristic that picks 300 kbps on every chunk achieves zero rebuffering but loses massively on bitrate reward.

Baseline performance: EoH best = 87.0 QoE on 3G (vs RobustMPC 78.2, BeamSearch oracle 97.0).

## Objective

Add an anti-conservatism component to the fitness function that penalizes severe bandwidth under-utilization, pushing evolution toward adaptive strategies that use higher bitrates when conditions allow.

## Requirements

### 1. Bandwidth utilization penalty in fitness

Modify `prob.py` `_simulate()` to compute and optionally apply a utilization penalty:

- **Compute per-video utilization**: For each video, `utilization = mean_bitrate_chosen / max_bitrate_available`. Track this alongside per-video QoE.

- **Add new fitness mode `"mean_util"`**:
  ```python
  if mode == "mean_util":
      base_qoe = float(np.mean(per_video_qoes))
      mean_util = float(np.mean(per_video_utilizations))
      # Penalize only when utilization is extremely low
      util_penalty = max(0, ABR_UTIL_THRESHOLD - mean_util) * ABR_UTIL_WEIGHT
      return base_qoe - util_penalty
  ```

- **Env vars**:
  - `ABR_FITNESS_MODE="mean_util"` to activate
  - `ABR_UTIL_THRESHOLD` (default: 0.25) — below this utilization, penalty kicks in
  - `ABR_UTIL_WEIGHT` (default: 50.0) — penalty strength. With max_bitrate=4300 kbps and 48 chunks, the total QoE range is roughly -200 to +200, so a penalty of 50 when utilization=0 is significant but not dominant.

### 2. Variance-aware fitness refinement

Enhance the existing `mean_std` mode:

- **Make it work well for 3G**: Currently `mean_std` mode does `mean - weight * std`. For 3G where all videos have negative QoE, this can produce extremely negative fitness. Add a normalization: `mean - weight * (std / max(abs(mean), 1.0))` so the penalty is relative to the mean magnitude.

- **Add `"mean_std_util"` combined mode**: Combines both variance penalty and utilization penalty.

### 3. Pass fitness mode info to feedback

Modify `prob.py` to include the active fitness mode and any penalty values in the metrics dict:

- Add `fitness_mode`, `utilization_mean`, `utilization_penalty` to metrics so `feedback.py` can inform the LLM about what's being optimized.

### 4. Track utilization in simulation

Modify `_simulate()` to track per-video mean utilization:

```python
video_bitrate_sum = 0.0  # sum of chosen bitrates within current video
# ... in the chunk loop:
video_bitrate_sum += float(self.video_bit_rates[bit_rate])
# ... at end_of_video:
video_util = video_bitrate_sum / (video_steps * float(np.max(self.video_bit_rates)))
per_video_utilizations.append(video_util)
video_bitrate_sum = 0.0
```

## Files to Modify

| File | Changes |
|------|---------|
| `examples/user_abr/prob.py` | Add utilization tracking, `mean_util` and `mean_std_util` modes, utilization penalty logic |

## Acceptance Criteria

1. New fitness mode `mean_util` is available via `ABR_FITNESS_MODE=mean_util`.
2. Utilization penalty only activates when mean utilization drops below `ABR_UTIL_THRESHOLD`.
3. The penalty is smooth (no discontinuities) and tunable via env vars.
4. Existing fitness modes (`mean`, `cvar_25`, `cvar_10`, `mean_std`) are NOT modified — only new modes are added.
5. Per-video utilization is tracked and included in metrics dict.
6. No syntax errors, all existing code paths still work.

## Constraints

- Do NOT modify the `score(state, ctx)` function signature.
- Do NOT modify seed heuristics or prompts (that's Task A).
- Do NOT modify population management (that's Task C).
- Keep the penalty lightweight — it should not significantly increase simulation time.
- The default behavior (`ABR_FITNESS_MODE=mean`) must be completely unchanged.

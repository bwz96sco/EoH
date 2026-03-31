# Enhanced Feedback & Prompt for 3G ABR Performance

## Background

EoH evolves ABR heuristics by combining LLMs with evolutionary computation. On ABRBench-3G, the best evolved heuristic achieves QoE ~87.0 (vs RobustMPC 78.2, BeamSearch oracle 97.0). The remaining ~10-point gap to the oracle is partly due to:

1. **Coarse feedback**: `feedback.py` uses only 3 fixed thresholds (rebuffer>0.5s, bitrate<35%*max, switch>1200kbps) with generic advice. The LLM gets no information about per-trace QoE distribution, bandwidth utilization, or 3G-specific challenges.

2. **Feedback only reaches m1 operator**: The `eoh_evolution.py` `get_prompt_m1()` method injects `other_inf` (feedback string) into the prompt, but `e1`, `e2`, `m2`, `m3` operators are completely blind to evaluation results.

3. **No 3G-specific guidance in prompts**: `prompts.py` describes the generic ABR problem but doesn't mention that 3G datasets have extremely low bandwidth (300-4300 kbps bitrates, rebuf_penalty=4.3), where conservative strategies dominate but over-conservatism loses ~4 QoE/chunk.

## Objective

Improve the feedback quality and prompt guidance so the LLM generates better ABR heuristics for low-bandwidth (3G) scenarios, without regressing 4G+ performance.

## Requirements

### 1. Enhanced `feedback.py` diagnostics

Modify `diagnose_failure_mode()` and `format_feedback()` in `examples/user_abr/feedback.py`:

- **Add per-trace QoE distribution info**: Include QoE std, worst-10% QoE, and QoE range in the feedback string. The metrics dict already contains `qoe_std` and `qoe_worst_10pct` when `ABR_FITNESS_MODE != "mean"` — make these always available by passing them from `prob.py`.

- **Add bandwidth utilization metric**: `utilization = mean_bitrate / max_bitrate`. When utilization < 0.2, flag as "severely under-utilizing available bandwidth". When utilization < 0.4, flag as "moderately conservative".

- **Make thresholds adaptive to dataset characteristics**: Instead of fixed `mean_rebuffer > 0.5`, use `mean_rebuffer > 0.1 * rebuf_penalty` (adapts to 3G's 4.3 vs 4G+'s 40). Instead of fixed `mean_bitrate < 0.35 * max_bitrate`, use a sliding scale based on rebuf_penalty.

- **Add per-component QoE breakdown**: Show how much QoE is lost to rebuffering vs how much is lost to low bitrate vs switching penalty. This helps the LLM understand the dominant loss source.

### 2. Inject feedback into ALL operators

Modify `eoh_evolution.py` methods:

- **`get_prompt_e1()`**: After listing the parent algorithms, add: "The following evaluation feedback shows the current performance characteristics:" + best parent's `other_inf`.

- **`get_prompt_e2()`**: Same as e1 — inject best parent's feedback after algorithm listings.

- **`get_prompt_m2()`**: After showing the parent algorithm, add the feedback. m2 does parameter tuning — knowing that "bitrate utilization is only 15%" directly tells the LLM which parameters to adjust.

- **`get_prompt_m3()`**: m3 does simplification for generalization. Add feedback to help the LLM understand what components may be causing overfitting (e.g., "95% of QoE loss comes from over-conservative bitrate selection").

### 3. 3G-specific prompt guidance

Modify `prompts.py` `GetPrompts.__init__()`:

- **Add to `prompt_other_inf`**: A paragraph about low-bandwidth challenges:
  ```
  "When rebuf_penalty is high relative to max bitrate (e.g., 3G networks where rebuf_penalty=4.3 and max bitrate=4.3 Mbps), "
  "a single rebuffer second costs as much as choosing max bitrate for one chunk. "
  "In this regime, avoid extreme conservatism (always picking lowest bitrate) — instead, use buffer level as a confidence signal: "
  "when buffer is healthy (>10s), it's safe to pick higher bitrates; when buffer is low (<4s), be conservative. "
  "A good heuristic should be adaptive to network conditions, not uniformly pessimistic."
  ```

### 4. Pass richer metrics from `prob.py` to feedback

Modify `prob.py` `_simulate()`:

- **Always include** `qoe_std`, `qoe_worst_10pct`, and `qoe_best_10pct` in the metrics dict (currently only included when `_FITNESS_MODE != "mean"`).

- **Add `mean_utilization`**: `mean_bitrate_kbps / max_bitrate_kbps` as a float 0-1.

- **Add `qoe_breakdown`**: dict with `bitrate_component`, `rebuffer_component`, `switch_component` showing average per-chunk contribution of each term.

## Files to Modify

| File | Changes |
|------|---------|
| `examples/user_abr/feedback.py` | Enhanced diagnostics, adaptive thresholds, utilization metric, QoE breakdown |
| `examples/user_abr/prob.py` | Always pass qoe_std, worst_10pct, utilization, QoE breakdown in metrics |
| `examples/user_abr/prompts.py` | Add 3G-specific guidance to `prompt_other_inf` |
| `eoh/src/eoh/methods/eoh/eoh_evolution.py` | Inject feedback into e1, e2, m2, m3 prompts |

## Acceptance Criteria

1. `feedback.py` produces richer, adaptive feedback that includes QoE distribution, utilization, and per-component breakdown.
2. All 5 operators (m1, m2, m3, e1, e2) include evaluation feedback in their prompts when available.
3. `prompts.py` includes guidance about low-bandwidth regime behavior.
4. `prob.py` always returns the full metrics set (qoe_std, worst_10pct, utilization, breakdown).
5. All existing tests pass (if any). No syntax errors.
6. Changes are backward-compatible — when feedback is empty/None, operators behave as before.

## Constraints

- Do NOT modify the `score(state, ctx)` function signature or the seed heuristics.
- Do NOT change the evolutionary loop in `eoh_interface_EC.py` — only modify the prompt-generation methods in `eoh_evolution.py`.
- Do NOT change the fitness aggregation logic (CVaR, mean_std, etc.) — that's handled by Task B.
- Keep feedback strings concise (< 500 chars) to avoid exceeding LLM context limits.

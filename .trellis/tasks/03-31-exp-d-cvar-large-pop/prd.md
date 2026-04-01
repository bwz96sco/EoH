# Experiment D: CVaR Fitness + Large Population for 3G ABR

## Background

Previous round of 3 experiments (Enhanced Feedback, Fitness Constraint, Pop Diversity) all failed to improve 3G QoE beyond the baseline of 87.0. Key findings:

- Training fitness improved (-53 -> -55) but test QoE decreased (87.0 -> 86.5), indicating **overfitting to training distribution**
- Population diversity collapsed by generation 4 (all 5 individuals converged to conservative strategies)
- `prob.py` already has CVaR fitness modes (`cvar_25`, `cvar_10`) implemented but **never tested**
- Current `ec_pop_size=5` is far below standard EC practice (20-100)

## Objective

Combine two key improvements:
1. **CVaR-25 fitness**: Optimize the worst 25% of per-video QoEs instead of mean, preventing overfitting to easy traces
2. **Larger population (15)**: Maintain more diversity across generations, preventing premature convergence

## Changes Required

### 1. Configure CVaR-25 fitness mode via `.env`

Add to `.env`:
```
ABR_FITNESS_MODE=cvar_25
```

The `_aggregate_qoe()` function in `prob.py` already supports this mode (from Experiment B's branch `experiment/3g-fitness-constraint`). However, this experiment should be based on the **main branch** (`abr-remote-repro-20260328`), NOT on Experiment B's branch, since:
- Experiment B added `_aggregate_qoe()` as an instance method on `ABRProblem`, but the main branch already has a standalone `_aggregate_qoe()` function at module level that supports `cvar_25`
- We want a clean experiment without Experiment B's other changes (util tracking, mean_util mode, etc.)

The main branch's `prob.py` already has:
```python
_FITNESS_MODE = os.environ.get("ABR_FITNESS_MODE", "mean").strip().lower()
```
and `_aggregate_qoe()` supports `cvar_25` natively. Just set the env var.

### 2. Increase population size to 15

In `.env` add:
```
EC_POP_SIZE=15
```

The `runEoH.py` already reads `EC_POP_SIZE` via `_resolve_target_pop_size()` and handles seed expansion via `_expand_seed_population()`. The 5 base seeds (BB, BOLA, QUETRA, RobustMPC, RateBased) will be cycled 3 times to fill 15 slots.

### 3. Add best evolved heuristic as a 6th seed

Add a new seed to `seed_heuristics.py` based on the best heuristic from Experiment A (QoE = -55.10, test QoE = 86.51). This gives the evolution a strong starting point.

The best evolved heuristic from Experiment A used an exponentially-recency-weighted multi-horizon QoE forecaster. Its key pattern was:
- Harmonic mean throughput prediction with EWMA smoothing
- Buffer-adaptive safety factor: `safety = max(0.1, buffer/buffer_max) * 0.5`
- MPC-style horizon search with conservative bandwidth scaling

Add this as seed named `"evolved_best"` in `seed_heuristics.py`. The exact code should be extracted from the experiment results on the server. For now, create a placeholder that implements a buffer-adaptive MPC variant:

```python
def score(state, ctx):
    """Evolved best: buffer-adaptive conservative MPC with EWMA throughput."""
    # ... (see implementation section below)
```

**IMPORTANT**: Since we don't have the exact evolved code locally, create an improved variant of RobustMPC that incorporates the key insight (buffer-adaptive safety factor):
- When buffer > 50% of max: use standard harmonic mean prediction (aggressive)
- When buffer 20-50% of max: scale prediction by 0.7 (moderate)
- When buffer < 20% of max: scale prediction by 0.4 (conservative)
- Use EWMA (alpha=0.3) on recent throughputs instead of pure harmonic mean

With 6 seeds and `EC_POP_SIZE=15`, each seed gets 2-3 copies (15/6 = 2.5).

### 4. Increase generations to 12

In `.env`:
```
EC_N_POP=12
```

Larger population needs more generations to converge. 12 generations * 5 operators * 5 offspring/operator = 300 LLM calls per generation * 12 = 3600 total. At ~2 min/call this is ~120 hours, which is too long. Instead, keep it practical:

Actually, reconsidering: EoH evaluates `ec_pop_size * len(operators)` offspring per generation. With pop_size=15 and 5 operators, that's 75 evaluations per generation. But the LLM calls are the bottleneck (one per offspring). With 300s timeout, 75 calls * 300s = 6.25 hours per generation. 12 generations = 75 hours. This is too long.

**Revised: Use `EC_N_POP=10`** (same as before). 10 generations * 75 calls = 750 LLM calls total. At ~2 min average per call = 25 hours. Acceptable.

### 5. Ensure no file hardlink issues

**CRITICAL**: Previous experiments had a bug where git worktrees shared file inodes for untracked files (`.env`, seed cache). This caused one experiment to overwrite another's data.

**Prevention measures:**
- The worktree agent must NOT rely on files that might be hardlinked
- After worktree creation, explicitly check and break hardlinks on `.env` and any seed cache files:
  ```bash
  # Break hardlinks: copy, remove original, rename
  for f in .env seed_cache; do
    if [ -e "$f" ]; then
      cp "$f" "$f.tmp" && rm "$f" && mv "$f.tmp" "$f"
    fi
  done
  ```
- Use `ls -i` to verify inode independence before starting experiments

## Files to Modify

| File | Change |
|------|--------|
| `examples/user_abr/.env` | Add `ABR_FITNESS_MODE=cvar_25`, `EC_POP_SIZE=15`, `EC_N_POP=10` |
| `examples/user_abr/seed_heuristics.py` | Add `evolved_best` adaptive MPC seed heuristic |
| `examples/user_abr/prompts.py` | Add note about CVaR optimization goal in `prompt_other_inf` |

## .env Configuration (complete)

```
DATASET=ABRBench-3G
ABR_FITNESS_MODE=cvar_25
EC_POP_SIZE=15
EC_N_POP=10
EXP_N_PROC=4
EVA_TIMEOUT=300
LLM_REQUEST_TIMEOUT_S=300
LLM_TOTAL_TIMEOUT_S=600
```

(LLM_API_ENDPOINT, LLM_API_KEY, LLM_MODEL will be configured on the server.)

## Acceptance Criteria

1. `seed_heuristics.py` has a 6th seed (`evolved_best`) that implements buffer-adaptive MPC
2. `.env` is configured with `ABR_FITNESS_MODE=cvar_25` and `EC_POP_SIZE=15`
3. `prompts.py` mentions that optimization focuses on worst-case trace performance
4. The code runs correctly with `uv run python examples/user_abr/runEoH.py` (seed evaluation phase)
5. No hardlinked files in the worktree

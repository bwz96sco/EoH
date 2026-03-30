# Analysis: EoH 3G Performance Gap & Improvement Plan

## Context

Across 3 experiment runs (grok-4.20-beta, grok-4.1-expert, grok-4.1-thinking), EoH consistently performs well on ABRBench-4G+ but catastrophically poorly on ABRBench-3G:

| Suite | EoH | RobustMPC (best online) | BeamSearch (oracle, ref only) |
|-------|-----|------------------------|-------------------------------|
| ABRBench-3G (avg) | **-122** | +78 | +97 |
| ABRBench-4G+ (avg) | **+1027** | +976 | +1098 |

> **Note:** BeamSearch and MFD are **oracle/reference baselines** — they use `net_env.get_optimal()` which has access to future bandwidth. They are NOT valid comparison targets for online algorithms. The fair comparison is EoH vs RobustMPC.

Per-dataset breakdown (3G group, EoH vs RobustMPC):
- FCC-16: **-218** vs +37
- FCC-18: +41 vs +143
- Oboe: **-56** vs +96
- Puffer-21: **-200** vs +34
- Puffer-22: **-347** vs +37
- HSR (OOD): +48 vs +122

## Root Cause: Reward Hacking via Over-Conservatism

### The mechanism

1. **All seed heuristics have negative QoE on 3G training traces** (best seed RobustMPC: QoE = -162). The 3G training distribution is dominated by extremely low-bandwidth traces where rebuffering penalty (4.3x/second) dwarfs bitrate reward (~0.3-4.3/chunk).

2. **Evolution converges to "never rebuffer" strategy**: The best evolved heuristic uses `predict_tput *= safety * 0.5` where `safety = max(0.1, buffer/buffer_max)`. This scales predicted throughput down to **5% of harmonic mean** when buffer is low, causing it to always pick the lowest bitrate.

3. **This improves training fitness** (157.5 vs seed-best 162.4) because avoiding catastrophic rebuffering on the hardest training traces matters more than gaining bitrate reward.

4. **But fails on test evaluation** because:
   - On easier test traces (FCC-16, Puffer-21/22), bandwidth easily supports higher bitrates. Always picking 300 kbps when 4300 kbps is achievable loses ~4.0 QoE points per chunk (= ~192 over 48 chunks).
   - BeamSearch adapts per-trace; the evolved heuristic cannot.

5. **Population diversity collapses by generation 4**: All 5 individuals converge to conservative MPC variants within 0.8 fitness of each other. Names like "PessimisticMinMPC", "SuperPessimisticMinMPC" confirm the trend.

### Why 4G+ doesn't have this problem

- 4G+ bitrates span 1000-40000 kbps with rebuf_penalty=40. The higher bandwidth makes it possible to achieve positive QoE on training traces.
- The evolved heuristic uses arithmetic mean with fixed safety margin (÷1.8) — much less extreme than the 3G heuristic's ×0.05 factor.
- There's more room for the evolution to explore productive strategies rather than converging to "always lowest bitrate."

## Diagnosis Steps (what to investigate)

### Step 1: Verify the overfitting hypothesis
- Compare the evolved 3G heuristic's behavior on individual training vs test traces
- Check if it literally always picks bitrate index 0 on test traces
- Run: evaluate the seed RobustMPC on the same test datasets to confirm seeds actually perform better

### Step 2: Understand training trace distribution
- Profile the bandwidth distribution in ABRBench-3G training traces
- Check if certain datasets (e.g., Puffer) dominate the trace count and skew the fitness signal

## Improvement Strategies (ranked by expected impact)

### Strategy 1: Multi-objective / per-dataset fitness (HIGH impact)

**Problem**: Single averaged fitness across all training traces rewards "least bad everywhere" instead of "adaptive to conditions."

**Options**:
- A) **Worst-case aware fitness**: `fitness = mean_qoe - alpha * std_qoe` (penalize high variance across traces)
- B) **Per-dataset percentile**: Compute QoE per dataset, use the worst percentile as fitness
- C) **Pareto-based selection**: Track per-dataset QoE as a multi-objective vector, use NSGA-II style dominance

**Implementation**: Modify `prob.py:_simulate()` to return per-dataset breakdown, modify fitness aggregation in `prob.py:evaluate_with_details()`.

### Strategy 2: Train/validation split during evolution (HIGH impact)

**Problem**: Fitness is only on training traces; no overfitting detection.

**Options**:
- A) **Validation-gated selection**: Evaluate on held-out validation traces; only accept offspring that improve on both train and validation
- B) **Periodic validation check**: Every N generations, evaluate the population on validation traces; discard individuals that overfit

**Implementation**: Split `TRAIN_TRACES` into train_inner/validation in `config.py`, add validation evaluation in `eoh_interface_EC.py`.

### Strategy 3: Diversity maintenance (MEDIUM impact)

**Problem**: Population of 5 converges to a single strategy archetype by generation 4.

**Options**:
- A) **Increase pop_size** to 10-15 (more diverse gene pool)
- B) **Niching/crowding**: Prevent population from collapsing by maintaining behavior-diverse individuals (e.g., keep one high-bitrate, one conservative, one adaptive)
- C) **Island model**: Run 2-3 independent populations on different trace subsets, exchange migrants periodically

**Implementation**: Change `ec_pop_size` parameter; or modify `pop_greedy.py` to use behavior-based diversity metric.

### Strategy 4: Better feedback / anti-conservatism pressure (MEDIUM impact)

**Problem**: The feedback mechanism (`feedback.py`) detects "too conservative" but the threshold (`mean_bitrate < 0.35 * max_bitrate`) is easily evaded.

**Options**:
- A) **Adaptive conservatism threshold**: Compare against baseline performance, not just absolute bitrate
- B) **Explicit bitrate utilization reward**: Add `utilization = mean_bitrate / max_achievable_bitrate` to fitness
- C) **Constrained optimization**: Minimum bitrate utilization constraint

**Implementation**: Modify `feedback.py` thresholds and `prob.py` fitness function.

### Strategy 5: Add stronger seed heuristics (LOW-MEDIUM impact)

**Problem**: All 5 seeds perform poorly on 3G (QoE range -162 to -1748). Evolution has no good starting point.

> **BeamSearch/MFD are NOT usable as seeds** — they rely on `net_env.get_optimal()` which uses future bandwidth (oracle). The EoH `score(state, ctx)` interface only has access to historical throughput.

**Options**:
- A) **Hand-craft a "safe adaptive" seed**: A heuristic that detects bandwidth regime (low/medium/high) and adjusts conservatism accordingly — conservative on bad traces, aggressive on good traces. This is the strategy the evolution fails to discover on its own.
- B) **Port RobustMPC with better defaults**: The current RobustMPC seed uses exhaustive K^H search but a naive throughput estimator. Add a variant with EWMA + buffer-aware safety margin that's less extreme than the evolved 0.05x factor.

**Implementation**: Add new entries to `seed_heuristics.py`, regenerate seed cache.

### Strategy 6: Condition-aware heuristic architecture (LOW impact, longer term)

**Problem**: A single `score()` function must handle all network conditions.

**Options**:
- A) **Network condition classifier + strategy selector**: Detect bandwidth regime, apply different logic
- B) **Prompt engineering**: Better describe the 3G challenges in `prompts.py` to guide LLM toward adaptive strategies

## Recommended Action Plan

**Quick wins (can test immediately):**
1. Increase `ec_pop_size` to 10 (Strategy 3A)
2. Tighten feedback conservatism threshold in `feedback.py` (Strategy 4A)
3. Hand-craft a bandwidth-adaptive seed heuristic (Strategy 5A)

**Medium-term (requires code changes):**
4. Implement per-dataset percentile fitness (Strategy 1B) — modify `prob.py`
5. Add train/validation split (Strategy 2A) — modify `config.py` + evaluation pipeline

**Longer-term:**
6. Multi-objective selection (Strategy 1C) — requires changes to EoH population management

## Files to Modify

| File | Change |
|------|--------|
| `examples/user_abr/seed_heuristics.py` | Add BeamSearch/MFD as seeds |
| `examples/user_abr/prob.py` | Per-dataset fitness aggregation, validation split |
| `examples/user_abr/feedback.py` | Tighter conservatism detection |
| `examples/user_abr/runEoH.py` | Increase ec_pop_size |
| `env/SABR/config.py` | Train/validation split definitions |
| `eoh/src/eoh/methods/management/pop_greedy.py` | Diversity-aware selection (optional) |

## Verification

- Run a quick experiment with just strategies 1+3+5 and compare 3G test performance
- Check that 4G+ performance doesn't regress
- Monitor population diversity across generations (algorithm name variety, fitness spread)

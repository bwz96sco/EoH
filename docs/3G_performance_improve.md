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

## Progress Since This Note Was Written

The original diagnosis above was based on the early `~ -122` 3G runs. Since then, several focused campaigns have been executed.

### What has already been tested

| Campaign / run | Main change | 3G result | Interpretation |
|------|------|------:|------|
| `20260330-140417-seed-impact-pop5-seed-abrbench-3g-quetra` | Single-seed (`QUETRA`), `pop=5`, `mean` | `86.9527` | Strong evidence that seed choice matters a lot. |
| `20260331-085304-3g-improve-enhanced-feedback-r2` | Stronger feedback injection | `86.5` | Helpful, but not enough to beat the best single-seed baseline. |
| `20260331-085318-3g-improve-fitness-constraint-r2` | Fitness shaping (`mean_util`) | `86.0` | Some improvement, but weaker than the best seed-only route. |
| `20260331-085334-3g-improve-pop-diversity-r2` | Diversity maintenance / behavior descriptors | `85.5` | Did not beat the best seed-only baseline. |
| `20260331-121909-exp-d-cvar-large-pop` | CVaR-25 + larger population | `83.2` | Larger population alone inside this setup was not enough; CVaR likely hurt. |
| `20260331-121909-exp-f-cvar-adaptive-seed` | CVaR-25 + adaptive seed variant | `54.7` | Clear negative result. |
| `20260401-132132-mixed-pop25-exp12` | Mixed seeds, `pop=25`, `mean` | `87.5768` | Larger population can rescue mixed-seed runs. |
| `20260402-3g-hardset-round2-a1-r1` | `QUETRA + pop25 + mean` | `88.8697` | Current best result. Best evidence that **single-seed + larger population** works. |
| `20260402-3g-hardset-round2-a2-r1` | `QUETRA + pop5 + dataset_balanced_mean` | `84.7306` | `dataset_balanced_mean` alone did not help. |
| `20260402-3g-hardset-round2-a3-r1` | `QUETRA + pop25 + dataset_balanced_mean` | `86.6136` | New objective underperformed `A1`; also regressed on `HSR`. |
| `20260402-3g-hardset-round2-a4-r1` | Mixed seeds + `pop25` + `dataset_balanced_mean` | `87.2202` | Better than early mixed runs, still below `A1`. |
| `20260406-3g-validation-round1-v1-r1` | `train_validation_mean`, `QUETRA + pop25` | `87.3073` | Validation-aware objective regularized a bit, but did not beat `A1`. |
| `20260406-3g-validation-round1-v2-r1` | `train_validation_min`, `QUETRA + pop25` | `87.1743` | Even more conservative than `V1`; also below `A1`. |
| `20260412-3g-seed-round2-s1-r1` | New seed `quetra_regime`, `pop=5`, `mean` | `86.5915` | New seed idea did not beat `QUETRA pop5`. |
| `20260412-3g-seed-round2-s2-r1` | New seed `rmpc_blend`, `pop=5`, `mean` | `87.2151` | Closest new seed. Slightly better than `QUETRA pop5`, but still below `A1`. |
| `20260412-3g-seed-round2-s3-r1` | New seed `a1_distilled`, `pop=5`, `mean` | `86.4146` | Distillation idea did not transfer cleanly into a stronger seed. |
| `20260416-3g-island-round1-localhost-r2-fast-stageb-combined` | 5 single-seed islands, then merge winners and continue | `87.5384` | Stronger than online baselines, but still below `A1`; broad island orchestration did not beat best single-seed. |
| `20260417-3g-exploit-round1-f1-r1` | Family-local exploitation around `QUETRA` / `rmpc_blend`, `pop=25`, `mean` | `87.9839` | Best post-`A1` exploit attempt so far; improved `hard_mean`, but still below `A1` and missed `Oboe` / `HSR` gates. |

### What these completed experiments tell us

1. **The 3G problem is no longer "EoH fundamentally fails on 3G".** The pipeline already improved from `~ -122` to `88.8697`.
2. **The most reliable improvement so far is not fancy objective design; it is better seed organization plus larger population.**
   - Current best method: `QUETRA + pop25 + mean`
3. **`dataset_balanced_mean` is not supported by the current evidence.**
   - It was the main hypothesis in round 2, but both `A2` and `A3` underperformed `A1`.
4. **Mixed-seed remains weaker than the best single-seed route.**
   - `mixed pop25 mean = 87.5768`
   - `mixed pop25 dataset_balanced_mean = 87.2202`
   - both are below `QUETRA pop25 mean = 88.8697`
5. **Held-out validation during evolution is not supported by the current evidence.**
   - `train_validation_mean = 87.3073`
   - `train_validation_min = 87.1743`
   - both underperformed `A1 = 88.8697`
6. **Broad new-seed screening also did not produce a clear winner.**
   - `rmpc_blend = 87.2151` was the only new seed that beat `QUETRA pop5 = 86.9527`
   - but it still did not beat `A1`, and it missed the `hard_mean` gate
7. **Broader reorganization around the winning family also has not beaten `A1`.**
   - `island mode = 87.5384`
   - `family-local F1 exploit = 87.9839`
   - both are strong results, but neither surpassed `QUETRA + pop25 + mean`
8. **Feedback likely helps, but it is not the dominant factor.**
   - A small isolated ablation (`20260403-3g-feedback-on-small` vs `20260403-3g-feedback-off-small`) showed:
     - feedback on: `86.9368`
     - feedback off: `85.9539`
     - delta: `+0.9829`
   - So removing `m1` feedback hurts, but only modestly in this small-budget setting.

## Remaining Untried Or Under-Tested Directions

The 3G space is no longer wide open. Most broad hypothesis families have already been exercised at least once. The main directions still **not directly tested** are:

### 1. Budget scaling around the winning `A1` route

This is still the cleanest untried direction:

- `QUETRA + pop25 + mean + more generations`
- `QUETRA + larger population + matched budget`

Examples:

- `QUETRA + pop25 + mean + gen15`
- `QUETRA + pop35 + mean + gen10`

This stays on the only route that has already proven it can reach `88.8697`.

### 2. Narrow hard-case-aware tie-breaks on top of plain `mean`

This is **not** the same as `dataset_balanced_mean` or full multi-objective replacement.

The still-open variant is:

- keep `mean` as the only training objective
- use `hard_mean` floors or hard-dataset gates only as selection tie-breaks / acceptance filters
- maintain an explicit `HSR` regression bound

This remains untested in a clean matched-budget form.

### 3. Selection-fidelity upgrades inside the current loop

The `S1` idea from `3g-exploit-round1` was planned but not launched:

- first-pass fast evaluation for all candidates
- shared-trace or larger-slice reevaluation for top-K
- final ranking by reevaluated `mean`

This is still open if the main suspected bottleneck is ranking noise rather than search-space quality.

### 4. Behavior study of `A1` and motif extraction

Also still untried as a dedicated series:

- inspect where `A1` wins on `FCC-16`, `Puffer-21`, `Puffer-22`
- inspect where it loses on `HSR`
- turn those motifs into:
  - a tighter hand-crafted seed
  - or prompt / operator constraints that bias evolution toward the useful pattern

This is more targeted than another broad seed sweep.

### 5. Early temporary curriculum with late return to `mean`

The `C1` idea from `3g-exploit-round1` was planned but not launched:

- oversample the hardest 3G traces for the first `20%-30%` of generations
- return to plain `mean` afterward

This remains open, but lower priority than direct `A1` budget scaling.

### 6. Narrow island revisit

Broad island mode has already been tried and did not beat `A1`. The only plausible island follow-up still untested is:

- restrict islands to the strongest families only (`QUETRA` / `rmpc_blend`)
- add better Stage-B reevaluation or tie-breaks

This is a low-priority niche follow-up, not a mainline bet.

## Deprioritized Or Effectively Tested Already

The following directions have enough negative evidence that they should not be the default next bet:

- `dataset_balanced_mean` as the main route forward
- held-out train/validation objectives as primary selectors
- another broad new-seed screening wave
- broad island-mode orchestration with many seed families
- CVaR-style objectives as the main axis
- diversity / niching as the main axis
- feedback-only or prompt-only tweaks as the main axis
- any oracle / future-bandwidth seed or deployable target

## Updated Action Plan

**Current practical baseline:**
1. Keep `20260402-3g-hardset-round2-a1-r1` (`QUETRA + pop25 + mean = 88.8697`) as the main internal 3G baseline.

**Highest-priority untried directions:**
2. Spend the next 3G budget on `A1` scaling first, before opening a new objective family.
3. If a second line is needed, test a **narrow hard-case-aware tie-break / gate** on top of plain `mean`.
4. Only then consider:
   - `S1` selection-fidelity upgrades
   - or a targeted behavior-study-to-seed / prompt conversion loop

**Lower-priority but still open:**
5. `C1` temporary curriculum
6. narrow two-family island revisit

**Not recommended as the next default move:**
7. another validation-objective round
8. another broad seed-screening round
9. another broad island round
10. CVaR / diversity / feedback redesign as the primary hypothesis

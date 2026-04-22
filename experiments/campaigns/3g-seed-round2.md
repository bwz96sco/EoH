# Series: 3G Seed Round 2

## Objective
Design and screen stronger online seed heuristics for `ABRBench-3G`, then test whether any seed can beat the current best seed-driven baseline:

- `20260402-3g-hardset-round2-a1-r1`
- `ABRBench-3G (avg) = 88.8697`
- `hard_mean = 46.4957`

## Primary Metric
- `ABRBench-3G (avg)` from `collect_results.py` / `results_summary.csv`

## Key Secondary Metrics
- `hard_mean = mean(FCC-16, Puffer-21, Puffer-22)`
- Regression guard: `FCC-18`, `Oboe`, `HSR`

## Baseline Reference
- Best current seed route: `QUETRA + pop25 + mean = 88.8697`
- Seed screening baseline: `QUETRA + pop5 + mean = 86.9527`

## Changed Factor
- Replace the starting seed heuristic while keeping the objective, evaluation scope, and runner path fixed.

## Fixed Settings
- Model: `grok-4.20-beta`
- Evolution target: `ABRBench-3G`
- Eval datasets: `FCC-16,FCC-18,Oboe,Puffer-21,Puffer-22,HSR`
- Fitness mode: `mean`
- Screening pop size: `5`
- Screening generations: `10`
- `EXP_N_PROC=4`
- `EVA_TIMEOUT=120`
- `LLM_REQUEST_TIMEOUT_S=120`
- `LLM_TOTAL_TIMEOUT_S=360`
- Runner: `experiments/run_eoh_target_experiment.sh`
- Phase 2: reuse existing SABR baselines

## Screening Matrix

| Label | Key Change | Planned run id |
|-------|------------|----------------|
| S1 | `quetra_regime`: QUETRA-style slack matching with buffer-regime-dependent throughput prediction and safety margins | `20260412-3g-seed-round2-s1-r1` |
| S2 | `rmpc_blend`: RobustMPC-style short-horizon search with blended conservative/nominal throughput rollout | `20260412-3g-seed-round2-s2-r1` |
| S3 | `a1_distilled`: distilled online seed inspired by the A1 evolved motif using conservative low-percentile future-sustainable scoring | `20260412-3g-seed-round2-s3-r1` |

## Gate For Follow-up
Only continue to larger-pop or confirmatory runs if a screening seed satisfies:

- `ABRBench-3G (avg) > 86.9527` (beats `QUETRA pop5`)
- `hard_mean >= 45.3105`
- `HSR` regression vs `QUETRA pop5` is no worse than `-2.0`

If one seed clearly wins, promote only that seed to `pop25 + mean` and compare against `88.8697`.

## Analysis

- Campaign design is complete and the screening matrix is fixed to three new seeds: `quetra_regime`, `rmpc_blend`, and `a1_distilled`.
- Code changes are isolated in the worktree `experiment/3g-seed-round2`, and the same files are synced to the remote experiment checkout `/root/code/exp-3g-seed-round2`.
- Local smoke validation already passed:
  - all three seed names are exported through `SEED_HEURISTICS`
  - `ABR_SEED_NAME` resolves them correctly in `runEoH.py`
  - each seed evaluates successfully through `ABRProblem.evaluate()` on a small `FCC-18` smoke sample
- `heyun` SSH recovered and the screening wave completed in the isolated remote checkout `/root/code/exp-3g-seed-round2`.
- Remote startup exposed a missing root-level Python environment. That was fixed by wiring the runner through the existing SABR `.venv` and installing the missing EoH-side dependencies plus editable `eoh` from the isolated checkout.

## Final Screening Results

| Label | 3G QoE | hard_mean | FCC-18 | Oboe | HSR | Gate result |
|-------|--------:|----------:|-------:|-----:|----:|-------------|
| S1 `quetra_regime` | `86.5915` | `44.6925` | `144.6240` | `97.0093` | `143.8383` | Missed `3G` and `hard_mean` |
| S2 `rmpc_blend` | `87.2151` | `45.2236` | `146.1473` | `99.1763` | `142.2961` | Best run; beat `QUETRA pop5` on `3G`, but missed `hard_mean` gate |
| S3 `a1_distilled` | `86.4146` | `45.3458` | `144.6497` | `97.7458` | `140.0545` | Missed `3G`; `HSR` regressed too much |

- Baseline comparison:
  - `QUETRA pop5 = 86.9527`
  - `A1 = QUETRA pop25 = 88.8697`
- No new seed beat `A1`.
- Only `S2 = rmpc_blend` exceeded `QUETRA pop5`, and the margin was small (`+0.2624`).
- This campaign is a **negative screening result overall**: broad hand-designed seed replacement did not produce a clear new baseline.

## Next Steps

- Keep `A1 = QUETRA + pop25 + mean = 88.8697` as the main 3G baseline.
- If seed work continues, refine only `rmpc_blend`; do not open another broad multi-seed screening wave yet.
- Prefer next experiments that operate around the proven `A1` setup:
  - more search budget near `A1`
  - targeted hard-dataset tie-break or gated selection
  - direct analysis/distillation of the `A1` behavior on `FCC-16`, `Puffer-21`, and `Puffer-22`

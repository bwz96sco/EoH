# Series: 3G Hardset Round 2

## Objective
突破当前 3G plateau，验证提升是否来自更大的种群、single-seed 组织方式，以及面向 hard datasets 的更均衡训练目标。

## Primary Metric
- `ABRBench-3G (avg)` from `collect_results.py` / `results_summary.csv`

## Key Secondary Metrics
- `hard_mean = mean(FCC-16, Puffer-21, Puffer-22)`
- Regression guard: `FCC-18`, `Oboe`, `HSR`

## Fixed Settings
- Model: `grok-4.20-beta`
- Evolution target: `ABRBench-3G`
- Eval datasets: `FCC-16,FCC-18,Oboe,Puffer-21,Puffer-22,HSR`
- `EC_N_POP=10`
- `EXP_N_PROC=4`
- `EVA_TIMEOUT=120`
- `LLM_REQUEST_TIMEOUT_S=120`
- `LLM_TOTAL_TIMEOUT_S=360`
- Runner: `experiments/run_eoh_target_experiment.sh`
- Phase 2: reuse existing SABR baselines; do not rerun unless missing

## Baselines
- External online baseline: `RobustMPC = 78.2371`
- External overall best baseline: `BeamSearch = 96.9909`
- Current best mixed internal baseline:
  - run: `20260401-132132-mixed-pop25-exp12`
  - `ABRBench-3G (avg) = 87.5768`
  - `hard_mean = 45.4736`
- Current best single-seed baseline:
  - run: `20260330-140417-seed-impact-pop5-seed-abrbench-3g-quetra`
  - `ABRBench-3G (avg) = 86.9527`
  - `hard_mean = 45.3105`

## Planned Runs

### Stage 1: Screening
- `A1`: `QUETRA + pop25 + mean`
- `A2`: `QUETRA + pop5 + dataset_balanced_mean`
- `A3`: `QUETRA + pop25 + dataset_balanced_mean`
- `A4`: `mixed-seed + pop25 + dataset_balanced_mean`

Current Stage 1 run ids:
- `20260402-3g-hardset-round2-a1-r1`
- `20260402-3g-hardset-round2-a2-r1`
- `20260402-3g-hardset-round2-a3-r1`
- `20260402-3g-hardset-round2-a4-r1`

### Stage 2: Confirmatory Repeats
Only continue if `A3-r1` satisfies:
- `ABRBench-3G (avg) > 87.5768`
- `hard_mean > 45.4736`
- each of `FCC-18`, `Oboe`, `HSR` regresses by no more than `2.0` vs `20260401-132132-mixed-pop25-exp12`

Then run:
- `A1-r2`, `A1-r3`
- `A3-r2`, `A3-r3`
- `B1-r2`, `B1-r3` where `B1 = mixed-seed + pop25 + mean`

## Notes On The New Fitness Mode
- `dataset_balanced_mean` uses the datasets present in the current split with equal weight.
- For `ABRBench-3G` training, that means the five in-distribution train datasets:
  - `FCC-16`, `FCC-18`, `Oboe`, `Puffer-21`, `Puffer-22`
- `HSR` remains eval-only and is **not** pulled into training fitness.
- Feedback should expose per-dataset means and `hard_mean` so mutation prompts can target the weak datasets directly.

## Analysis
<!-- Fill after Stage 1 / Stage 2 complete -->

## Next Steps
<!-- Fill after results are available -->

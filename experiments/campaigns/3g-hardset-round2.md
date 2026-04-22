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

## Stage 1 Results

| Label | Config | 3G QoE | hard_mean | FCC-18 | Oboe | HSR | vs 87.5768 baseline |
|-------|--------|--------|-----------|--------|------|-----|---------------------|
| A1 | QUETRA + pop25 + mean | 88.8697 | 46.4957 | 146.8578 | 100.1812 | 146.6925 | +1.2929 |
| A2 | QUETRA + pop5 + dataset_balanced_mean | 84.7306 | 43.0522 | 144.9716 | 98.2505 | 136.0049 | -2.8462 |
| A3 | QUETRA + pop25 + dataset_balanced_mean | 86.6136 | 45.9329 | 145.7399 | 98.2335 | 137.9092 | -0.9632 |
| A4 | mixed-seed + pop25 + dataset_balanced_mean | 87.2202 | 45.4094 | 145.5290 | 99.1669 | 142.3971 | -0.3566 |

## Analysis

- **Stage 1 finished with 4/4 completed runs**, and all four runs produced `results_summary.csv`, plots, and `run_report.md`.
- **A1 is the best result of the campaign**: `88.8697`, which exceeds the previous mixed baseline `87.5768` by `+1.2929`. `hard_mean` also improved from `45.4736` to `46.4957`.
- **The large-population change is clearly effective**. Comparing `A1` against the previous best single-seed baseline (`QUETRA pop5 mean = 86.9527`) shows that `pop25` improves single-seed performance.
- **`dataset_balanced_mean` did not help in this round**. `A3` underperformed `A1` on the primary metric (`86.6136` vs `88.8697`) and also regressed on `FCC-18`, `Oboe`, and especially `HSR`.
- **Mixed-seed was still not best under the new objective**. `A4` recovered to `87.2202`, but it remained below `A1`.
- The original Stage 2 gate was tied to **`A3`**. `A3` failed the gate because:
  - `ABRBench-3G (avg)` did not exceed `87.5768`
  - `HSR` regressed by more than `2.0` vs `20260401-132132-mixed-pop25-exp12`
- Therefore, **Stage 2 confirmatory repeats were intentionally not launched**.

## Conclusion

- This campaign **did break the previous 3G plateau**, but not by the hypothesized `dataset_balanced_mean` route.
- The supported conclusion is:
  - **single-seed + larger population works**
  - **dataset_balanced_mean did not add value in this round**
- The best round-2 method is **`QUETRA + pop25 + mean`** (`A1`), not the planned `A3` main method.

## Next Steps

- Use `A1` as the new practical 3G baseline for follow-up work.
- If we still want to test objective redesign, do it in a new campaign with a narrower hypothesis:
  - rebalance hard datasets without sacrificing `HSR`
  - or try objective shaping that preserves in-distribution gains while keeping OOD regression bounded
- Keep `dataset_balanced_mean` as a negative-result reference unless a revised version is proposed and tested in a new campaign.

# Series: 3G QoE Improvement Round 1

## Objective
解决 EoH 在 ABRBench-3G 上 QoE 未能稳定超过 baseline 的问题。测试 CVaR-25 fitness（优化 worst 25% traces）配合更大种群和 adaptive seed 是否有效。

## Baseline Reference
- Best previous: **87.0** (Quetra seed, seed-impact study, collect_results.py metric)
- RobustMPC baseline: 78.2

## Experiments

| Label | Key Change | 3G QoE | vs Best (87.0) | Run ID | Checkout |
|-------|-----------|--------|----------------|--------|----------|
| D: CVaR + Large Pop 15 | ABR_FITNESS_MODE=cvar_25, pop=15, 6 seeds (含 evolved_best) | 83.2 | -3.8 | 20260331-121909 | exp-d-cvar-large-pop |
| F: CVaR + Adaptive Seed | ABR_FITNESS_MODE=cvar_25, pop=6, 6 seeds (含 adaptive_regime) | 54.7 | -32.3 | 20260331-121909 | exp-f-cvar-adaptive-seed |

## Per-Dataset Breakdown

| Dataset | Baseline (RMPC) | D | F |
|---------|----------------|-----|-----|
| FCC-16 | 36.6 | 37.7 | 33.2 |
| FCC-18 | 143.3 | 136.3 | 81.4 |
| Oboe | 96.1 | 91.1 | 60.3 |
| Puffer-21 | 34.1 | 52.5 | 39.6 |
| Puffer-22 | 36.9 | 47.2 | 36.7 |
| HSR | 122.4 | 134.2 | 77.0 |

## Run Details

### Experiment D
- Run root: `exp-d-cvar-large-pop/experiments/results/20260331-121909/`
- Model: grok-4.20-beta, pop_size=15, n_pop=10
- Seeds: BB, BOLA, QUETRA, RobustMPC, RateBased, evolved_best (buffer-adaptive MPC)
- Training fitness (CVaR-25): 42.5 (best generation 10)
- CSV: `analysis/results_summary.csv`
- Report: `analysis/run_report.md`

### Experiment F
- Run root: `exp-f-cvar-adaptive-seed/experiments/results/20260331-121909/`
- Model: grok-4.20-beta, pop_size=6, n_pop=10
- Seeds: BB, BOLA, QUETRA, RobustMPC, RateBased, adaptive_regime (bandwidth-regime-aware)
- Training fitness (CVaR-25): 44.0 (best generation 10)
- CSV: `analysis/results_summary.csv`
- Report: `analysis/run_report.md`

## Analysis
<!-- 手动填写 -->

## Next Steps
<!-- 手动填写 -->

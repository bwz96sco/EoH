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
| E: Enhanced Feedback | 增强反馈诊断 + 所有算子注入 feedback, pop=5, quetra | 86.5 | -0.5 | 20260331-085304-3g-improve-enhanced-feedback-r2 | exp-enhanced-feedback |
| F: CVaR + Adaptive Seed | ABR_FITNESS_MODE=cvar_25, pop=6, 6 seeds (含 adaptive_regime) | 54.7 | -32.3 | 20260331-121909 | exp-f-cvar-adaptive-seed |
| Fitness Constraint | mean_util fitness + 反保守惩罚, pop=5, quetra | 86.0 | -1.0 | 20260331-085318-3g-improve-fitness-constraint-r2 | exp-fitness-constraint |
| Pop Diversity | NSGA-II crowding + 行为描述符多样性, pop=5, quetra | 85.5 | -1.5 | 20260331-085334-3g-improve-pop-diversity-r2 | exp-pop-diversity |

## Per-Dataset Breakdown

| Dataset | Baseline (RMPC) | D | E | F | Fitness | Diversity |
|---------|----------------|-----|------|-----|---------|-----------|
| FCC-16 | 36.6 | 37.7 | 38.4 | 33.2 | 37.9 | 37.8 |
| FCC-18 | 143.3 | 136.3 | 146.4 | 81.4 | 144.9 | 145.7 |
| Oboe | 96.1 | 91.1 | 99.6 | 60.3 | 97.6 | 99.0 |
| Puffer-21 | 34.1 | 52.5 | 49.8 | 39.6 | 51.2 | 48.5 |
| Puffer-22 | 36.9 | 47.2 | 44.5 | 36.7 | 46.5 | 46.4 |
| HSR | 122.4 | 134.2 | 140.4 | 77.0 | 138.1 | 135.7 |

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

### Experiment E: Enhanced Feedback
- Run root: `exp-enhanced-feedback/experiments/results/20260331-085304-3g-improve-enhanced-feedback-r2/`
- Model: grok-4.20-beta, pop_size=5, n_pop=10, quetra single-seed
- Key code changes:
  - `prob.py`: compute qoe_std, worst-10%, best-10%, mean_utilization, per-component QoE breakdown
  - `feedback.py`: adaptive thresholds, utilization diagnosis, per-trace QoE distribution
  - `prompts.py`: 3G-specific prompt guidance (buffer-as-confidence-signal)
  - `eoh_evolution.py`: inject feedback into ALL EC operators (e1, e2, m2, m3), not just m1
- Training fitness (mean): continued from checkpoint
- CSV: `analysis/results_summary.csv`
- Report: `analysis/run_report.md`

### Fitness Constraint
- Run root: `exp-fitness-constraint/experiments/results/20260331-085318-3g-improve-fitness-constraint-r2/`
- Model: grok-4.20-beta, pop_size=5, n_pop=10, quetra single-seed
- Key code changes:
  - `prob.py`: track bandwidth utilization (chosen/available), new fitness modes
  - New fitness mode `mean_util`: mean QoE minus utilization penalty when below threshold
  - Env vars: ABR_UTIL_THRESHOLD=0.25, ABR_UTIL_WEIGHT=50.0
- Training fitness (mean_util): continued from checkpoint
- CSV: `analysis/results_summary.csv`
- Report: `analysis/run_report.md`

### Pop Diversity
- Run root: `exp-pop-diversity/experiments/results/20260331-085334-3g-improve-pop-diversity-r2/`
- Model: grok-4.20-beta, pop_size=5, n_pop=10, quetra single-seed
- Key code changes:
  - `prob.py`: compute 4D behavior vector (utilization, rebuffer_rate, switch_rate, min_bitrate_frac)
  - `pop_diverse.py` (new): behavior-based dedup + NSGA-II crowding distance selection
  - `eoh_interface_EC.py`: extract behavior dict, store in individual['behavior']
  - Controlled by EC_DIVERSITY_WEIGHT env var
- Training fitness (mean with diversity): continued from checkpoint
- CSV: `analysis/results_summary.csv`
- Report: `analysis/run_report.md`

## Analysis

- **D 和 F 均退步**：CVaR-25 fitness + mixed seeds (6 seeds) 导致 D=83.2 (-3.8), F=54.7 (-32.3)，重复了 baseline 实验中 mixed-seed 干扰的问题
- **E (Enhanced Feedback) 表现最接近 baseline**：86.5 (-0.5)，说明让所有 EC 算子都能看到反馈是有价值的方向
- **Fitness Constraint 和 Pop Diversity 也轻微退步**：86.0 (-1.0) 和 85.5 (-1.5)，可能因为 single-seed 下保守性问题已不严重，反保守惩罚和多样性管理边际效果有限
- **关键发现**：CVaR 从未在 single-seed 下被干净测试；所有 single-seed 实验（E/Fitness/Diversity）表现都在 85.5-86.5 范围，接近但未超过 87.0
- **注意**：E/Fitness/Diversity 三个实验都从 checkpoint 继续进化，不是从头开始，可能影响公平比较

## Next Steps

→ CVaR + single-seed 需要干净测试（无 checkpoint、无 mixed-seed）
→ Enhanced Feedback 的改进值得在更大种群下验证
→ 启动 Hardset Round 2 系列（pop=25, dataset_balanced_mean fitness）

# Series: 3G Seed Impact Study

## Objective
逐 seed 分析 EoH 在 ABRBench-3G 上的表现差异，确定哪个 seed 作为起点能产生最好的进化结果。

## Configuration
- EC: pop_size=5, n_pop=10, single seed per run
- Fitness: mean (default)
- Model: grok-4.20-beta
- Server: EoH-repro checkout

## Experiments

| Seed | 3G QoE | vs RobustMPC (78.2) | Run ID |
|------|--------|---------------------|--------|
| bb | 85.9 | +7.7 | 20260330-140417-seed-impact-pop5-seed-abrbench-3g-bb |
| bola | 85.0 | +6.8 | 20260330-140417-seed-impact-pop5-seed-abrbench-3g-bola |
| **quetra** | **87.0** | **+8.8** | 20260330-140417-seed-impact-pop5-seed-abrbench-3g-quetra |
| rate_based | 86.2 | +8.0 | 20260330-140417-seed-impact-pop5-seed-abrbench-3g-rate_based |
| robust_mpc | 84.8 | +6.6 | 20260330-140417-seed-impact-pop5-seed-abrbench-3g-robust_mpc |

## Baselines (collect_results.py metric)

| Scheme | 3G avg |
|--------|--------|
| RobustMPC | 78.2 |
| BeamSearch (oracle) | 97.0 |

## Analysis

- **所有 seed 都成功超过 RobustMPC**（84.8 ~ 87.0 vs 78.2），说明 single-seed 进化在 3G 上是可行的
- **seed 间差异较小**（~2 QoE），但 Quetra seed 略优（87.0）
- **与 baseline model 实验形成鲜明对比**：model 实验用 5 seeds 混合 pop=5 得到 -122，seed impact 用 single seed pop=5 得到 85+
- **关键发现**：mixed-seed population 不如 single-seed population，可能因为不同 seed 风格的代码互相干扰进化方向

## Next Steps

→ 以 single-seed 为基础设计改进实验（3G Improve Round 1）
→ 探索 CVaR fitness 和更大种群是否能进一步提升

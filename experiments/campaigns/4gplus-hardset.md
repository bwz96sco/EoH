# Series: 4G+ Hardset

## Objective
在 ABRBench-4G+ 上用 A1 最佳配置（quetra seed, pop=25, mean fitness, 10 gen）进行 in-domain evolution，
验证 EoH 能否在 4G+ 环境下产生与 SABR 竞争的启发式算法。

## Research Context
- A1 (grok-4.20-beta) 在 3G 上 6/6 胜过 SABR
- A1 在 4G+ 零样本迁移中 6/6 输给 SABR（avg 1027.4 vs 1188.6, -13.6%）
- 本系列旨在回答：EoH 在 4G+ in-domain evolution 后能否缩小甚至消除与 SABR 的差距

## Baseline Reference
- SABR 4G+ avg: 1188.6
- A1 零样本迁移 4G+ avg: 1027.4
- A1 3G avg: 88.9

## Fixed Factors
- Seed: quetra, expanded to pop=25
- Fitness: mean
- Generations: 10
- EXP_N_PROC: 1 (Vertex AI rate limit)

## Variable Factors
- LLM model: gemini-2.5-flash (via Vertex AI) vs A1 original grok-4.20-beta (proxy unavailable)

## Planned Runs
1. r1: gemini-2.5-flash via Vertex AI, quetra pop=25, 10 gen
2. r2-r3: repeat for statistical significance (if r1 shows promise)

## Experiments

| Label | Key Change | 4G+ QoE (avg) | Delta vs SABR | Run ID | Status |
|-------|-----------|---------------|---------------|--------|--------|
| r1 | first 4G+ in-domain evolution, gemini-2.5-flash | pending | pending | `20260427-081532-4gplus-a1-config-vertexflash-r1` | evolution-only completed |

## Analysis
- `20260427-081532-4gplus-a1-config-vertexflash-r1` completed 10/10 EoH generations on `ABRBench-4G+`, but Phase 3/4 were skipped, so there is no `analysis/results_summary.csv` and no final QoE comparison yet.

## Next Steps
- Run Phase 3/4 evaluation before treating the evolved heuristic as a completed 4G+ result.

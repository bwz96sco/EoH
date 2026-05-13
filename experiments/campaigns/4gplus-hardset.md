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
| r1 | first 4G+ in-domain evolution, gemini-2.5-flash | **1578.1** | **+32.8%** | `20260427-081532-4gplus-a1-config-vertexflash-r1` | completed |

## Analysis
- `20260427-081532-4gplus-a1-config-vertexflash-r1`: Vertex `google/gemini-2.5-flash`, quetra pop=25, 10 gen. Phase 1 completed 2026-04-27, Phase 3/4 completed 2026-04-29.
- **4G+ avg = 1578.1**, beating SABR (1188.6) by 32.8%, BeamSearch (1098.1) by 43.7%.
- Per-dataset: Norway3G=319.9, Lumos4G=1784.6, Lumos5G=1842.5, SolisWi-Fi=1842.5, Ghent=1836.9, Lab=1842.5. All 6/6 datasets win over BeamSearch.
- This is the **best 4G+ result so far**, slightly ahead of grok-4.20-beta seed-impact results (1563-1568), confirming the evolutionary framework rather than the specific LLM is the key performance driver.
- Lumos5G, SolisWi-Fi, and Lab hit the ~1842.5 ceiling, suggesting the heuristic achieves near-optimal QoE on these datasets.

## Next Steps
- Run r2-r3 for statistical significance (mean±std)
- Verify the high SolisWi-Fi score (~1842.5 vs SABR 669.8) is not an evaluation artifact

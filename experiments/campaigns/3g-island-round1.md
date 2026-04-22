# Series: 3G Island Round 1

## Objective
测试一种两阶段岛屿模式是否能减少 mixed-seed 在 `ABRBench-3G` 上的早期相互干扰：先让 5 个 seed 各自独立演化，再把每个岛屿的最优个体汇合后继续进化。

## Baseline Reference
- Single-seed baseline: `20260402-3g-hardset-round2-a1-r1`, `ABRBench-3G = 88.9`
- Seed-impact references: `bb / bola / quetra / robust_mpc / rate_based`

## Fixed Factors
- Target dataset: `ABRBench-3G`
- Eval scope: default 3G suite
- Stage A seeds: `bb`, `bola`, `quetra`, `robust_mpc`, `rate_based`
- Stage A per-island population: 5 copies of the same seed
- Stage A generations: 5
- Stage B combined population: each island best × 5 individuals total
- Stage B continued generations: 5
- Default reliability knobs: `EXP_N_PROC=1`, extended LLM timeouts

## Planned Runs

| Label | Key Change | Status | Planned Run ID | Notes |
|-------|------------|--------|----------------|-------|
| I-A-bb | island stage A, bb duplicated to pop=5 | completed | `20260416-3g-island-round1-localhost-r2-fast-stagea-bb` | 5 generations, best objective `-54.17958` |
| I-A-bola | island stage A, bola duplicated to pop=5 | completed | `20260416-3g-island-round1-localhost-r2-fast-stagea-bola` | 5 generations, best objective `-55.42652` |
| I-A-quetra | island stage A, quetra duplicated to pop=5 | completed | `20260416-3g-island-round1-localhost-r2-fast-stagea-quetra` | 5 generations, best objective `-54.31625` |
| I-A-robust_mpc | island stage A, robust_mpc duplicated to pop=5 | completed | `20260416-3g-island-round1-localhost-r2-fast-stagea-robust_mpc` | 5 generations, best objective `-54.88605` |
| I-A-rate_based | island stage A, rate_based duplicated to pop=5 | completed | `20260416-3g-island-round1-localhost-r2-fast-stagea-rate_based` | 5 generations, best objective `-54.30468` |
| I-B-combined | merge 5 island winners, continue evolution | completed | `20260416-3g-island-round1-localhost-r2-fast-stageb-combined` | 5 continued generations, final `ABRBench-3G = 87.5384` |

## Analysis

- 本轮 island mode 已完整跑通：5 个 Stage A 岛全部完成，没有 `stageA.fail`，随后 Stage B 合并 winner 后继续演化并完成 eval/analysis。
- 最终结果：
  - `ABRBench-3G (avg) = 87.5384`
  - 相比当前最佳 baseline `A1 = 88.8697`，差 `-1.3313`
  - 相比在线 baseline `RobustMPC = 78.2371`，高 `+9.3013`
- 6 个 3G 数据集上，最终 island heuristic 都超过了在线 baselines `BB / BOLA / QUETRA / RobustMPC`，但没有在任何单个数据集上超过 oracle/reference best。
- Stage A 的内部 best objective 以 `bola` 岛最高（`-55.42652`）；Stage B 最终 best individual 的 stored objective 进一步到 `-56.05917`，但这一内部目标改善没有转化成超过 `A1` 的最终 3G eval。
- 这说明“两阶段 island 组织方式”本身是可行的，且能得到强于在线 baseline 的结果，但在当前 budget 和 selection 设定下，仍然不如最强单 seed 路线 `QUETRA + pop25 + mean`。
- 本地同步产物：
  - `experiments/campaign_data/3g-island-round1/I-B-combined_results_summary.csv`

## Next Steps

1. 将本轮作为 completed negative result 收束，不把当前 island 配置提升为新的 3G 主线。
2. 如果继续做 island 方向，优先只改变一个维度复测：
   - 提高单岛内部吞吐（例如 `EXP_N_PROC=2`）
   - 或减少 Stage A/Stage B 代数，先做更快 screening
   - 或把 Stage B 的 selection / tie-break 改成更偏 hard-dataset-aware
3. 继续以 `A1 = 88.8697` 作为当前 3G baseline，并把 island 结果当作“强于在线 baseline，但未超过 best single-seed”的参考点。

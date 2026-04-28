# Series: 3G Advanced Architectures Round 1

## Objective
把 [docs/eoh_abr_advanced_strategies.md](/Users/zhangbowen/Projects/EoH/docs/eoh_abr_advanced_strategies.md) 里最值得先落地的两个方向压成**最小可跑的结构化 seed family**，先验证它们在 `ABRBench-3G` 上是否有信号：

- `virtual_sensor`: 固定 controller，只把若干虚拟指标封装进 heuristic scaffold
- `rmpc_predictor`: 固定 MPC rollout，只替换 bandwidth predictor scaffold

这轮不是最终形态研究框架；目标只是先回答：**结构化架构种子是否值得继续投资**。

## Primary Metric
- `ABRBench-3G (avg)` from `results_summary.csv`

## Baseline Reference
- `20260330-140417-seed-impact-pop5-seed-abrbench-3g-quetra`
- Config: `QUETRA + pop5 + mean`
- Reference result: `ABRBench-3G (avg) = 86.9527`

Secondary reference:
- `20260402-3g-hardset-round2-a1-r1`
- Config: `QUETRA + pop25 + mean`
- Best known result: `88.8697`

## Fixed Settings
- Runner: `experiments/run_eoh_target_experiment.sh`
- Evolution dataset: `ABRBench-3G`
- Eval datasets: `FCC-16,FCC-18,Oboe,Puffer-21,Puffer-22,HSR`
- Population size: `EC_POP_SIZE=5`
- Generations: `EC_N_POP=10`
- Fitness: plain `mean`
- Remote execution profile: `grok2api workers=1`, `EXP_N_PROC=1`
- DeepSeek rerun profile: `deepseek-v4-flash`, hard-timeout LLM client, `EXP_N_PROC=2`

## Run Matrix

| Label | Key Change | Status | Run ID | Result |
|-------|------------|--------|--------|--------|
| V1 | New seed family `virtual_sensor`: fixed indicator scaffold + fixed conservative controller | failed | `20260421-3g-advanced-architectures-round1-v1-r1` | unhealthy launch; reached `e1` but hit repeated `BrokenPipeError` / upstream `429` before a valid first generation formed |
| P1 | New seed family `rmpc_predictor`: fixed exact MPC rollout + new regime-aware predictor scaffold | failed | `20260421-3g-advanced-architectures-round1-p1-r1` | reached `5/10` populations, but repeated `BrokenPipeError` / upstream `429` kept the run dirty, so no trustworthy result was produced |
| V2-local-deepseek-r1 | Rerun `virtual_sensor` locally through the current `.env` DeepSeek route from the experiment worktree | failed | `20260427-3g-advanced-architectures-v2-deepseek-local-r1` | invalid health run: old experiment-branch LLM client hung at `e1 [1/5]` after `population_generation_0`; stopped before `generation_1` |
| V2-local-deepseek-r2 | Rerun `virtual_sensor` locally through DeepSeek after syncing the hard-timeout LLM client into the experiment worktree | stopped | `20260427-3g-advanced-architectures-v2-deepseek-local-r2` | stopped intentionally before completion when switching to heyun `EXP_N_PROC=2`; partial generations are not a final result |
| V2-heyun-deepseek-n2-r3 | Rerun `virtual_sensor` on heyun through DeepSeek with the synced experiment branch and `EXP_N_PROC=2` | completed | `20260427-3g-advanced-architectures-v2-deepseek-heyun-n2-r3` | `ABRBench-3G avg = 85.8634`; completed 10/10 generations and full evaluation, no API/timeout failures, but produced 22 invalid offspring and stayed below `QUETRA pop5 = 86.9527` and `A1 = 88.8697` |

## Analysis Plan

1. First compare each run only against `QUETRA pop5 = 86.9527`.
2. Only if one of them clearly beats the `QUETRA pop5` reference, consider a follow-up round with larger population / budget.
3. Do not treat failure to beat `A1 = 88.8697` in this round as a decisive negative result; this round is only a low-budget signal check.

## Current Interpretation

- `virtual_sensor` is the lower-risk way to test “structured architecture” without changing the evaluator contract.
- `rmpc_predictor` is the most direct continuation of the existing `RobustMPC / rmpc_blend` signal.
- Both are intentionally implemented as **seed families**, not new EoH problem types, so they can be tested inside the current pipeline with minimal cross-layer drift.
- `V1` did not fail in a way that says much about the seed idea itself; it mainly reproduced the current grok transport instability (`BrokenPipe` + upstream `429`) under formal launch conditions.
- `P1` made real evolutionary progress, unlike `V1`, but it still remained dirty throughout the run: repeated `BrokenPipeError` and upstream `429` were common deep into the population loop, so it also fails the health-gate standard for trustworthy evidence.
- `V2-local-deepseek-r2` shows the local DeepSeek route is viable for at least the first full `virtual_sensor` generation once the hard-timeout LLM client is present in the experiment worktree. Early invalid offspring still appear (`Obj: None`), but the failure shape is parsing/quality noise rather than provider transport instability.
- `V2-heyun-deepseek-n2-r3` is the first completed clean DeepSeek run for this campaign. It confirms the provider path and `EXP_N_PROC=2` are operational, but the `virtual_sensor` seed family did not beat the low-budget `QUETRA pop5` reference. Treat this as a negative quality signal for `virtual_sensor` under this budget, not as a provider failure.

## Next Steps

1. Do not scale `virtual_sensor` further unless there is a specific diagnostic reason; the completed DeepSeek run is below the `QUETRA pop5` reference.
2. If continuing this campaign, use the synced DeepSeek/heyun profile for `rmpc_predictor` next, because the original `P1` grok result was provider-contaminated but showed more evolutionary progress than `V1`.
3. Keep treating the original `V1` / `P1` grok attempts as provider-contaminated, not clean negative evidence about the seed families.

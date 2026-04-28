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

`rmpc_predictor` reference:
- `20260330-140417-seed-impact-pop5-seed-abrbench-3g-robust_mpc`
- Config: `robust_mpc + pop5 + mean`
- Reference result: `ABRBench-3G (avg) = 84.8`

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
| P1 | New seed family `rmpc_predictor`: fixed exact MPC rollout + new regime-aware predictor scaffold | failed | `20260421-3g-advanced-architectures-round1-p1-r1` | saved `8/10` populations, but repeated `BrokenPipeError` / upstream `429` kept the run dirty, so no trustworthy result was produced |
| V2-local-deepseek-r1 | Rerun `virtual_sensor` locally through the current `.env` DeepSeek route from the experiment worktree | failed | `20260427-3g-advanced-architectures-v2-deepseek-local-r1` | invalid health run: old experiment-branch LLM client hung at `e1 [1/5]` after `population_generation_0`; stopped before `generation_1` |
| V2-local-deepseek-r2 | Rerun `virtual_sensor` locally through DeepSeek after syncing the hard-timeout LLM client into the experiment worktree | stopped | `20260427-3g-advanced-architectures-v2-deepseek-local-r2` | stopped intentionally before completion when switching to heyun `EXP_N_PROC=2`; partial generations are not a final result |
| V2-heyun-deepseek-n2-r3 | Rerun `virtual_sensor` on heyun through DeepSeek with the synced experiment branch and `EXP_N_PROC=2` | completed | `20260427-3g-advanced-architectures-v2-deepseek-heyun-n2-r3` | `ABRBench-3G avg = 85.8634`; completed 10/10 generations and full evaluation, no API/timeout failures, but produced 22 invalid offspring and stayed below `QUETRA pop5 = 86.9527` and `A1 = 88.8697` |
| Control-main-deepseek-quetra-n2-r1 | Main checkout control without `virtual_sensor`: standard `quetra` seed through DeepSeek with `EXP_N_PROC=2` | completed | `20260428-3g-main-deepseek-quetra-n2-r1` | `ABRBench-3G avg = 83.9349`; clean full run with 0 API errors and 14 invalid offspring; this is the same-provider control for judging `virtual_sensor` |
| P2-grok2api-rmpc_predictor-r1 | Retry `rmpc_predictor` on grok2api with hard-timeout client and `EXP_N_PROC=1` | stopped | `20260428-3g-advanced-rmpc-predictor-grok2api-r1` | stopped after ~10 minutes because `SEED_NO_CACHE=1` repeated the expensive RMPC initial seed evaluation and never reached `population_generation_0`; not a grok2api quality signal |
| P2-grok2api-rmpc_predictor-cache-r2 | Retry `rmpc_predictor` on grok2api using the P1 `population_generation_0` seed cache | completed | `20260428-3g-advanced-rmpc-predictor-grok2api-cache-r2` | `ABRBench-3G avg = 82.3470`; completed full pipeline, but the run is transport-contaminated (`BrokenPipeError=107`, 27 invalid offspring), so it is weak evidence against `rmpc_predictor` rather than a clean quality result |
| P2-grok2api-rmpc_predictor-close-probe | Probe per-request connection close for grok2api without changing the default keep-alive behavior for other providers | completed | `20260428-grok2api-close-rmpc-predictor-probe-r2` | evolution-only probe on branch `experiment/grok2api-close-connection-probe`; one generation completed with `BrokenPipeError=0`, `HTTP429=0`, and 3 invalid offspring, strongly suggesting reused connections were causing the grok2api BrokenPipe noise |
| P2-grok2api-rmpc_predictor-close-r1 | Full cache-backed `rmpc_predictor` rerun with `LLM_API_CONNECTION_CLOSE=1` on the same grok2api branch | running | `20260428-3g-advanced-rmpc-predictor-grok2api-close-r1` | launched from heyun `/root/code/exp-grok2api-close-connection-probe` with `EC_N_POP=10`, `EXP_N_PROC=1`; passed cached-seed startup and entered `OP: e1 [1/5]` with no early API/BrokenPipe/429 errors |

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
- `Control-main-deepseek-quetra-n2-r1` is now the clean same-provider control: standard `quetra` through DeepSeek scored `83.9349`, while `virtual_sensor` through the same provider scored `85.8634`. That means `virtual_sensor` improved over the DeepSeek `quetra` control by `+1.9285`, but still missed the historical `QUETRA pop5 = 86.9527` reference by `-1.0893`.
- `P2-grok2api-rmpc_predictor-cache-r2` finished and scored `82.3470`, below the prior `robust_mpc` seed reference `84.8`. Because it accumulated `107` `BrokenPipeError` retries and `27` invalid offspring, treat it as provider-contaminated and not as a clean architectural negative.
- The connection-close probe changed only the grok2api connection behavior (`Connection: close` after each request) and completed a one-generation `rmpc_predictor` smoke with `0` BrokenPipe errors. This is a strong transport-layer signal: if `rmpc_predictor` remains interesting, rerun it with `LLM_API_CONNECTION_CLOSE=1` before making a final quality judgment.

## Next Steps

1. Do not scale `virtual_sensor` as a headline follow-up yet: it beat the DeepSeek `quetra` control, but still did not beat the historical `QUETRA pop5` reference.
2. If continuing `rmpc_predictor`, rerun the full cache-backed comparison with `LLM_API_CONNECTION_CLOSE=1`; the completed keep-alive run is too noisy to settle the seed-family question.
3. Keep treating the original `V1` / `P1` grok attempts and the keep-alive `P2` run as provider-contaminated, not clean negative evidence about the seed families.

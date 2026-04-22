# Series: 3G Model Refresh Round 1

## Objective
在不改 seed、population、fitness、evaluation scope 的前提下，只替换 [examples/user_abr/.env](/Users/zhangbowen/Projects/EoH/examples/user_abr/.env) 中的 API provider / model，观察 `QUETRA + pop5 + mean` 在 `ABRBench-3G` 上是否会出现明显变化。

## Primary Metric
- `ABRBench-3G (avg)` from `results_summary.csv`

## Baseline Reference
- `20260330-140417-seed-impact-pop5-seed-abrbench-3g-quetra`
- Config: `QUETRA + pop5 + mean`
- Prior result: `ABRBench-3G (avg) = 86.9527`
- Historical model route: `grok-4.20-beta`

## Fixed Settings
- Runner: `experiments/run_eoh_target_experiment.sh`
- Evolution dataset: `ABRBench-3G`
- Eval datasets: `FCC-16,FCC-18,Oboe,Puffer-21,Puffer-22,HSR`
- Seed filter: `ABR_SEED_NAME=quetra`
- Population size: `EC_POP_SIZE=5`
- Generations: `EC_N_POP=10`
- Fitness: plain `mean`

## Run Matrix

| Label | Key Change | Status | Run ID | Result |
|-------|------------|--------|--------|--------|
| Q1 | Keep `QUETRA + pop5 + mean`, replace only the `.env` API/model route with the current user-selected provider | completed | `20260421-3g-model-refresh-round1-q1-r1` | `ABRBench-3G = 75.6869`; `-11.2658` vs old `QUETRA pop5 = 86.9527` |
| Q2 | Keep the same current code/worktree and switch the `.env` route back to `grok` for an apples-to-apples control run | failed | `20260421-3g-model-refresh-round1-q2-r1` | stopped in Phase 1 after repeated `RemoteDisconnected`; no valid `population_generation_1` or `results_summary.csv` |
| Q2b | Retry the `grok` control on `heyun` with a gentler stable profile (`EXP_N_PROC=2`, `LLM_REQUEST_TIMEOUT_S=240`, `LLM_TOTAL_TIMEOUT_S=480`) and active log health gating | failed | `20260421-3g-model-refresh-round1-q2b-r1` | still hit repeated `RemoteDisconnected` / `BrokenPipeError` in `OP: e1`; no valid `population_generation_1` |
| Q3 | Retry the NVIDIA route on `heyun` with `EXP_N_PROC=1`, `LLM_REQUEST_TIMEOUT_S=300`, `LLM_TOTAL_TIMEOUT_S=600`, while monitoring `full_pipeline.log` for healthy startup | failed | `20260421-3g-model-refresh-round1-q3-r2` | Phase 1 log stopped growing after startup for >140s; no `population_generation_1` or analysis outputs |
| T1 | Probe the local `grok2api` path with a realistic long `e1` prompt using the same `InterfaceAPI` client and keep-alive settings as EoH | completed | `api-smoke` | `10/10` calls returned, but `6/10` responses had empty content; latency ranged from `0.866s` to `31.868s` |
| T2 | Run a true serial EoH smoke on `grok` with `SEED_NO_CACHE=1`, `EC_N_POP=1`, `EXP_N_PROC=1`, `SKIP_PHASE_3=1`, `SKIP_PHASE_4=1` | failed | `20260421-3g-model-refresh-round1-grok-smoke-r2` | progressed through all `e1` offspring and into `e2`, but required retries and then hit `parse_error` on `e2` offspring `3` |
| Q2c | Switch `grok2api.service` to `workers=1`, then rerun the `grok` control as a formal single-process run (`EXP_N_PROC=1`) | completed | `20260421-3g-model-refresh-round1-q2c-r1` | `ABRBench-3G = 84.4463`; healthier than `Q2/Q2b`, but still below old `QUETRA pop5 = 86.9527` |
| Q3b | After switching `grok2api` to `workers=1`, rerun the NVIDIA route as a formal single-process run (`EXP_N_PROC=1`) | failed | `20260421-3g-model-refresh-round1-q3b-r1` | still did not advance beyond wrapper startup; no first-generation progress visible before shutdown |
| T3 | After upgrading `grok2api` to the latest `origin/main`, rerun a minimal `QUETRA pop5` grok smoke with `EXP_N_PROC=1` | failed | `20260422-grok-recovery-smoke-n1-r2` | post-upgrade single-process smoke still died inside `check LLM API` after repeated upstream `429/403`; no usable generation artifact formed |
| T4 | On the same upgraded local `grok2api`, repeat the same minimal smoke with only `EXP_N_PROC=4` changed | failed | `20260422-grok-recovery-smoke-n4-r1` | reached `population_generation_0`, but never advanced to `generation_1`; repeated `429` plus `RemoteDisconnected` made the run unhealthy |
| K1 | Source the current remote `examples/user_abr/.env` as-is (`https://ai.hybgzs.com`, `moonshotai/kimi-k2-thinking`, `EXP_N_PROC=5`) and run a minimal `QUETRA pop5` smoke | failed | `20260422-kimi-env-smoke-r1` | failed immediately in `check LLM API` with repeated upstream `404`; no usable generation artifact formed |
| K2 | Keep the same provider endpoint but switch to `moonshotai/kimi-k2.5`, then run a cache-reuse `QUETRA pop5` smoke with `EXP_N_PROC=1` | failed | `20260422-kimi25-smoke-n1-r1` | formed `population_generation_0.json` but then showed no healthy phase progress; separate direct long-prompt probe on the same model returned immediate `403` |
| K3 | Run the full intended comparison config on `moonshotai/kimi-k2.5`: `QUETRA + pop5 + gen10 + EXP_N_PROC=1` | failed | `20260422-kimi25-full-r1` | stopped as unhealthy; no meaningful evolution progress appeared before a direct long-prompt probe confirmed the provider rejects EoH-scale prompts with `403` |

## Analysis

`Q1` is a clear negative result for this exact 3G recipe.

Key outcome:

- `ABRBench-3G (avg) = 75.6869`
- vs old `QUETRA + pop5 + mean` reference `86.9527`, delta is `-11.2658`
- vs `RobustMPC = 78.2371`, delta is `-2.5502`
- against online baselines inside the same summary, EoH beat:
  - `BB` on `4/6` datasets
  - `BOLA` on `5/6`
  - `QUETRA` on `3/6`
  - `RobustMPC` on only `2/6`

Interpretation:

1. Under the fixed `QUETRA pop5 mean` recipe, the new `.env` route (`z-ai/glm-5.1` via NVIDIA integrate) is materially worse than the historical route that produced `86.9527`.
2. This is not just “failed to improve”; it dropped below `RobustMPC`, so it should not be treated as a viable replacement for the old 3G baseline path.
3. The best evolved heuristic still converged to a `QUETRA`-style description by generation `10`, which suggests the gap is not from a totally different search family, but from lower-quality edits / mutations under this model route.
4. Two health-gated reruns on `heyun` still did not produce a clean control:
   - `Q2b` (`grok`, `EXP_N_PROC=2`, `240/480`) again failed in `Phase 1` with repeated `RemoteDisconnected` / `BrokenPipeError`
   - `Q3` (NVIDIA, `EXP_N_PROC=1`, `300/600`) did not report any first-generation progress; the log stayed frozen after startup for more than two minutes
5. A narrower troubleshooting wave clarified the `grok` path:
   - `T1` showed the local `grok2api` route is not dead; a realistic `~15.6k`-character `e1` prompt returned `10/10` times
   - but `6/10` of those “successful” responses had empty content, which is enough to trigger EoH parse retries or parse failures
   - `T2` proved a true serial EoH smoke can progress on the same path when forced to `EXP_N_PROC=1` and `SEED_NO_CACHE=1`
   - however, even that serial run still saw an initial `BrokenPipeError`, needed multiple prompt attempts on several offspring, and eventually hit `parse_error` inside `e2`
6. Switching `grok2api` back to `workers=1` improved the grok control path enough to finish a formal rerun, but not enough to recover the old baseline.
   - `Q2c` (formal single-process rerun) completed cleanly at `ABRBench-3G = 84.4463`
   - this is materially better evidence than `Q2/Q2b`, because the run actually finished and produced a valid summary
   - but it is still `-2.5064` below the historical `QUETRA pop5 = 86.9527`, so the current grok path is still not a clean apples-to-apples control for the old result
   - `Q3b` shows the NVIDIA path remains unhealthy even when the local grok service is simplified to one worker, so that route's issue is independent of `grok2api` worker count
7. So the “is it purely the model?” question remains unresolved.
   - `Q1` proves the current NVIDIA route can produce a much worse finished result under this recipe
   - the `grok` path is now known to be more viable under `workers=1` + serial execution, but still not clean enough for a trustworthy formal control run
   - provider / transport stability and response parseability are therefore part of the experiment risk, not just model quality
8. Ignore `20260421-3g-model-refresh-round1-q2-r2` and `20260421-3g-model-refresh-round1-q3-r1` when reasoning about this campaign.
   - those were accidental local mislaunches caused by malformed SSH quoting, not the intended remote controlled runs
9. Upgrading `grok2api` to the current upstream `main` improved the basic probe path, but did not restore formal experiment capacity.
   - after the upgrade, long-prompt probe calls against the local gateway no longer showed `empty_200` or transport failures
   - however, the first post-upgrade serial smoke `T3` still failed at the initial `check LLM API` step because the gateway was receiving a burst of upstream `429/403`
   - the post-upgrade `EXP_N_PROC=4` smoke `T4` did get far enough to write `population_generation_0.json`, but it never formed `generation_1` and repeatedly hit `429` plus `RemoteDisconnected`
   - practical takeaway: the current blocker has narrowed to upstream quota / refusal pressure under real EoH workload, not the earlier empty-content symptom and not a cleanly proven keep-alive regression
10. The newly supplied third-party `.env` route is not immediately usable as a replacement experiment backend.
   - `K1` explicitly sourced the remote `.env` and therefore did use `LLM_API_ENDPOINT=https://ai.hybgzs.com`, `LLM_MODEL=moonshotai/kimi-k2-thinking`, and `.env`'s `EXP_N_PROC=5`
   - the run still failed before real evolution because the backend returned repeated upstream `404`
   - this looks more like endpoint/model compatibility failure than simple RPM saturation, because the smoke never got far enough to make rate limiting the primary bottleneck
11. Switching the same endpoint to `moonshotai/kimi-k2.5` fixes the model-id compatibility issue, but not the workload suitability problem.
   - minimal chat requests to `moonshotai/kimi-k2.5` return `200`, so the route is alive and the model name is accepted
   - however, EoH cares about long, structured prompts, not tiny `Reply with exactly OK` probes
   - a direct probe using the same ~14k-character prompt from `experiments/grok2api_probe_sample_prompt.txt` against `moonshotai/kimi-k2.5` returned immediate upstream `403`
   - the cache-reuse smoke `K2` only reached `population_generation_0`, then stopped showing healthy progress
   - the full `gen10` formal attempt `K3` was therefore stopped early as unhealthy rather than being allowed to burn a long run with no trustworthy chance of completion

Tracked artifacts:

- local run root: [experiments/results/20260421-3g-model-refresh-round1-q1-r1](/Users/zhangbowen/Projects/EoH/experiments/results/20260421-3g-model-refresh-round1-q1-r1)
- copied summary: [Q1_results_summary.csv](/Users/zhangbowen/Projects/EoH/experiments/campaign_data/3g-model-refresh-round1/Q1_results_summary.csv)

## Next Steps

1. Do not promote this `.env` provider/model route into later 3G work as the default baseline.
2. Before drawing a model-causality conclusion, establish one clean provider-stability control path first.
3. For `grok`, the next bottleneck to isolate is not raw reachability but response quality:
   - why `200`/`success` responses can still contain empty content
   - whether `workers=1` should remain the default stable service setting
   - whether empty-content responses shrink enough under `workers=1` to justify a full formal rerun
4. For NVIDIA, treat this route as an unstable provider path until a small health-gated smoke run can advance beyond the first generation.
5. Keep the historical `QUETRA pop5` and `A1 = QUETRA + pop25 + mean` routes as the meaningful 3G references.
6. After the latest `grok2api` upgrade, keep the local service at `workers=1`, but assume only `EXP_N_PROC=1` is even eligible for recovery testing until a fresh smoke run can clear the initial API check without repeated `429/403`.
7. Do not interpret the upgraded service as “fully fixed”: the gateway probe is healthier, but the first real EoH smokes still show the experiment path is gated by upstream refusal pressure rather than local parser or empty-response bugs.
8. Treat the current remote `.env` Kimi route as incompatible until its endpoint/model pair can pass the initial API check without upstream `404`.
9. For the same endpoint, `moonshotai/kimi-k2.5` is chat-compatible but still not EoH-compatible under current prompt sizes, because long prompts are rejected with upstream `403`.

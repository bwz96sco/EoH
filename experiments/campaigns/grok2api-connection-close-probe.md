# Series: grok2api Connection Close Probe

## Objective
判断 grok2api 上反复出现的 `BrokenPipeError` 是否来自复用 HTTP keep-alive 连接，而不是上游 `429`、模型质量或 EoH evaluator 本身。

## Primary Metric
- Transport health during EoH Phase 1: `BrokenPipeError`, `HTTP429`, `API error`, and invalid offspring count.

## Baseline Reference
- `20260428-3g-advanced-rmpc-predictor-grok2api-cache-r2`
- Config: `rmpc_predictor`, `ABRBench-3G`, cached `population_generation_0`, `EC_POP_SIZE=5`, `EC_N_POP=10`, `EXP_N_PROC=1`
- Result: completed full pipeline at `ABRBench-3G = 82.3470`, but accumulated `BrokenPipeError=107` and 27 invalid offspring.

## Fixed Settings
- Runner: `experiments/run_eoh_target_experiment.sh`
- Evolution dataset: `ABRBench-3G`
- Seed filter: `ABR_SEED_NAME=rmpc_predictor`
- Population size: `EC_POP_SIZE=5`
- Provider/model: local heyun grok2api route, `grok-4.20-fast`
- Execution: `EXP_N_PROC=1`

## Run Matrix

| Label | Key Change | Status | Run ID | Result |
|-------|------------|--------|--------|--------|
| C1 | Probe branch `experiment/grok2api-close-connection-probe`; add default-off `LLM_API_CONNECTION_CLOSE` and run a one-generation cache-backed smoke with `Connection: close` | completed | `20260428-grok2api-close-rmpc-predictor-probe-r2` | completed one generation in 19.8 minutes; `BrokenPipeError=0`, `HTTP429=0`, `API error=0`, 3 invalid offspring, diagnostics `success=21 llm_timeout=0 eval_timeout=0 parse_error=0 worker_budget_timeout=0` |
| C2 | Full cache-backed `rmpc_predictor` rerun with the same connection-close switch and full evaluation/analysis enabled | completed | `20260428-3g-advanced-rmpc-predictor-grok2api-close-r1` | completed full pipeline at `ABRBench-3G = 86.3736`; `BrokenPipeError=0`, one HTTP 429 retry, 18 invalid offspring, full `results_summary.csv` and `run_report.md` generated |

## Current Interpretation

- The initial probe strongly supports a transport-layer cause for the grok2api `BrokenPipeError`: disabling connection reuse eliminated BrokenPipe in the same seed family and same gateway profile.
- This should not become a global default because Vertex and other providers can benefit from keep-alive and did not show the same failure shape.
- The safe implementation path is an opt-in environment knob, `LLM_API_CONNECTION_CLOSE=1`, used only for grok2api-style proxy routes that break reused connections.
- The full `C2` run is the quality-bearing test for this connection mode. It confirms the connection-close knob fixes the repeated BrokenPipe transport failure in a full run, not only in a short smoke.
- `C2` improved the keep-alive full run from `82.3470` to `86.3736` and reduced `BrokenPipeError` from `107` to `0`. One upstream `HTTP 429` still appeared, so the route is cleaner but not perfectly noise-free.
- `C2` still trails historical `QUETRA pop5 = 86.9527`, so the transport fix is worth keeping for reproducible grok2api runs, but the `rmpc_predictor` seed family is not a new 3G baseline yet.

## Next Steps

1. Merge the default-off `LLM_API_CONNECTION_CLOSE` switch if we want reproducible grok2api runs.
2. Keep using `LLM_API_CONNECTION_CLOSE=1` for grok2api EoH experiments unless a later gateway fix proves keep-alive safe.
3. Keep the original keep-alive `rmpc_predictor` result marked as transport-contaminated.

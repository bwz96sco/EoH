# Integrate GCP Vertex AI ADC into EoH

## Goal

Enable EoH to run ABR experiments against Google Cloud Vertex AI using Application Default Credentials (ADC), so GCP promotional credits can be used without service account key files.

## What I already know

* EoH currently expects an OpenAI-compatible remote API and static bearer token.
* Vertex AI provides an OpenAI-compatible chat completions endpoint.
* Local testing already proved:
  * `gcloud` + ADC login works on the developer machine
  * Vertex OpenAI-compatible endpoint returns valid responses for `google/gemini-2.5-flash`
  * EoH can pass API bootstrap, seed initialization, and enter the first `e1` operator
* Remote testing on `heyun` reproduced the same behavior as local:
  * `population_generation_0.json` is produced
  * the run enters `OP: e1, [1 / 5]`
  * but does not reach `generation_1` in a reasonable time window

## Assumptions

* The minimum viable integration is an adapter-level change in `InterfaceAPI` and `InterfaceLLM`, without changing the ABR evaluator contract.
* The current main blocker is not authentication failure, but latency / throughput of the first large `e1` generation request.

## Open Questions

* Is the dominant bottleneck model latency, request size, or some runner-side framing overhead?
* Which Vertex model is fast enough to make EoH evolution practical?

## Requirements

* Support Vertex AI ADC auth in EoH without requiring a static API key file.
* Keep existing OpenAI-compatible providers working unchanged.
* Support canonical experiment execution through `experiments/run_eoh_target_experiment.sh`.
* Be able to run at least a valid Phase 1 smoke test with ABR `quetra + pop5 + EXP_N_PROC=1`.

## Acceptance Criteria

* [x] EoH can authenticate to Vertex AI via ADC.
* [x] A direct OpenAI-compatible Vertex request succeeds.
* [x] An ABR smoke run reaches Phase 1 and completes seed initialization.
* [x] We have a documented conclusion on whether Vertex is practically usable for EoH evolution.

## Definition of Done

* Code changes are isolated and verified.
* Lint / compile-level verification passes for touched files.
* Experiment findings are documented.
* Any repo-specific usage notes are captured for future sessions.

## Out of Scope

* Full production hardening for every GCP auth mode.
* Multi-provider abstractions beyond the minimum needed for Vertex ADC.
* Broad campaign execution using Vertex before smoke validation is complete.

## Technical Notes

* Touched code lives under `eoh/src/eoh/llm/`.
* Experiment validation uses the repo-local ABR workflow wrapper and canonical run roots.
* Current experimental worktree: `/Users/zhangbowen/Projects/EoH-exp-gcp-vertex`

## Outcome

Vertex ADC integration is now workable for EoH without service-account key files. The OpenAI-compatible Vertex endpoint can be used through `LLM_API_AUTH_MODE=gcloud-adc`, and long-running server jobs can refresh bearer tokens via `gcloud auth application-default print-access-token`.

Practical experiment conclusion:

* `google/gemini-2.5-flash` is the best Vertex model tested for the fixed `QUETRA + pop5 + mean` 3G recipe, reaching `ABRBench-3G = 83.5658`.
* `google/gemini-2.5-pro` is slower and slightly worse at `81.6910`.
* `google/gemini-2.5-flash-lite` runs cleanly but underperforms badly at `75.6869`.
* Vertex is now a usable backend for EoH, but it still trails the historical grok/mainline 3G bests and should be treated as a viable alternative path rather than the new default winner.

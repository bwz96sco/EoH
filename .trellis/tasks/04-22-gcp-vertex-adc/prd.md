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

* [ ] EoH can authenticate to Vertex AI via ADC.
* [ ] A direct OpenAI-compatible Vertex request succeeds.
* [ ] An ABR smoke run reaches Phase 1 and completes seed initialization.
* [ ] We have a documented conclusion on whether Vertex is practically usable for EoH evolution.

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

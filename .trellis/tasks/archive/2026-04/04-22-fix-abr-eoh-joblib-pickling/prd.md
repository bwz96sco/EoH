# PRD: Fix ABR EoH Joblib Pickling Regression

## Summary

Fix the regression where ABR EoH runs fail before offspring generation when `joblib.Parallel` uses multiple workers. The current failure is:

- `Parallel worker failure (budget=...s): PicklingError: Could not pickle the task to send it to the workers.`

The failure happens during worker task serialization, not during SABR evaluation or LLM inference timeouts.

## Problem

ABR EoH now initializes the remote LLM client before submitting offspring-generation work to `joblib.Parallel`. The LLM API layer reuses a persistent HTTPS connection. Once that connection is opened by the bootstrap probe request, the `InterfaceEC` object graph includes a live connection/socket object. When `joblib` serializes the bound worker task for `n_jobs > 1`, serialization fails and the run exits before producing `population_generation_1.json`.

## Goals

- Make multi-worker ABR EoH runs pickle-safe again.
- Preserve current LLM bootstrap behavior and runtime logging clarity.
- Avoid reintroducing the regression on future multi-worker runs.

## Non-Goals

- Do not redesign the ABR evaluator or SABR environment integration.
- Do not change prompt contracts or fitness logic.
- Do not add a new experiment runner.

## Scope

Primary code paths:

- `eoh/src/eoh/llm/api_general.py`
- `eoh/src/eoh/llm/interface_LLM.py`
- `eoh/src/eoh/methods/eoh/eoh_interface_EC.py`

Potential documentation/spec sync:

- `.trellis/spec/backend/error-handling.md`
- `.trellis/spec/backend/logging-guidelines.md`

## Requirements

1. Multi-worker `joblib.Parallel` submission for `InterfaceEC.get_algorithm()` must no longer fail due to pickling of the LLM client object graph.
2. The fix must remain compatible with remote API mode.
3. Existing single-worker behavior must continue to work.
4. Logging must still surface the real worker failure if a different serialization or runtime problem occurs.

## Verification

1. Reproduce the original serialization failure path in a focused local check before the fix.
2. After the fix, verify the same serialization path succeeds.
3. Run an ABR EoH command path with `EXP_N_PROC=2` and confirm the run passes worker submission without the previous pickling error.
4. Confirm no new syntax/runtime errors in the touched files.

## Risks

- Clearing or rebuilding connection state at the wrong boundary could reduce connection reuse more than intended.
- A narrow fix might handle the current socket case but miss other non-picklable fields in the same object graph.

## Acceptance Criteria

- `EXP_N_PROC=2` no longer fails with `PicklingError: Could not pickle the task to send it to the workers.`
- A focused serialization check of the object/task sent to `joblib` succeeds.
- Touched modules compile cleanly.

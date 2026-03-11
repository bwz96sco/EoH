# Refactor ABR Heuristic Ctx Contract

## Goal
Make the `user_abr` heuristic interface explicit and consistent by limiting `ctx` to environment constants and moving heuristic-specific knobs into heuristic-owned code.

## Requirements
- `ctx` must contain only evaluator-owned environment constants used across all heuristics.
- Prompt text must describe the exact `state` and `ctx` schema seen by the evaluator.
- Seed heuristics must no longer depend on hidden algorithm-specific fields injected through `ctx`.
- Existing ABR seed smoke tests must keep passing after the refactor.

## Acceptance Criteria
- [x] `examples/user_abr/abr_api.py` exposes only environment constants in `ctx`.
- [x] `examples/user_abr/prompts.py` documents the reduced `ctx` schema and tells heuristics to keep their own tunables in code.
- [x] `examples/user_abr/seed_heuristics.py` uses internal heuristic constants instead of hidden `ctx` knobs.
- [x] `examples/user_abr/smoke_test.py` passes with the new contract.

## Verification
- `python3 examples/user_abr/smoke_test.py`

## Technical Notes
- Preserve the public scoring signature `score(state, ctx)` to avoid changing the broader EoH method interface.
- Update any local verification helpers or derived seed artifacts that would otherwise drift from the new contract.

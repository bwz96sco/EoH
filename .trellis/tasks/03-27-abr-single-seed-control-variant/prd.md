# ABR Single-Seed Control Variant

## Goal

Allow ABR EoH runs to start from one chosen seed heuristic instead of the default full seed set.

## Requirements

- Support selecting one seed heuristic by name without manual editing.
- Keep current default behavior when no seed filter is provided.
- Avoid cache collisions between full-seed and single-seed runs, especially during concurrent execution.
- Expose enough metadata so the chosen seed mode is visible in run configs/tracker output.

## Acceptance Criteria

- [ ] `runEoH.py` can run with one chosen seed.
- [ ] Cache handling does not reuse incompatible seed populations across seed modes.
- [ ] Default full-seed runs still behave as before when no seed filter is set.

## Write Scope

- `examples/user_abr/`


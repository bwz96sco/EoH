# ABR Per-Dataset Evolution Variant

## Goal

Allow ABR experiments to evolve on one dataset at a time instead of only the mixed `ABRBench-3G` and `ABRBench-4G+` targets.

## Requirements

- Support dataset-scoped EoH evolution targets such as `FCC-18`, `Oboe`, `Norway3G`, and others.
- Preserve the existing mixed-target workflow.
- Keep run outputs isolated under canonical `experiments/results/<run-id>/...`.
- Make concurrent variant runs safe with respect to experiment outputs and evaluation logs.
- Prefer reusing existing baseline results instead of forcing repeated baseline reruns when possible.

## Acceptance Criteria

- [ ] The runner can execute a single-dataset evolution target without editing code by hand.
- [ ] Analysis still completes for the variant run.
- [ ] Concurrent variant runs do not overwrite each other's EoH evaluation logs or canonical outputs.

## Write Scope

- `experiments/`
- `env/SABR/eval_eoh_in_sabr.py`


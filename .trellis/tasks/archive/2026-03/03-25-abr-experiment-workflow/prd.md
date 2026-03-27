# brainstorm: formalize abr experiment workflow

## Goal

Define one fixed, tool-obeyed workflow for ABR experiments so result paths, cache paths, analysis outputs, and cleanup rules are explicit instead of ad hoc.

## What I already know

* The repo currently has ABR-related outputs in three places:
  * `/Users/zhangbowen/Projects/EoH/results`
  * `/Users/zhangbowen/Projects/EoH/experiments/results`
  * `/Users/zhangbowen/Projects/EoH/examples/user_abr/results*`
* `examples/user_abr/seed_cache/` is already being used to cache seed population generation 0 results.
* `experiments/results/` currently holds the latest analysis bundle:
  archived EoH populations, `results_summary.csv`, plots, logs, and run report.
* `results/` at repo root contains raw EoH output directories from direct runs.
* `examples/user_abr/results*` contains interrupted retries and older run backups, which are temporary/raw rather than canonical analysis outputs.
* `examples/user_abr/runEoH.py` currently sets `exp_output_path="./results/"`, so raw EoH output location depends on the caller's current working directory.
* `experiments/run_experiment.sh` currently treats `examples/user_abr/results` as a temporary working directory, then copies selected artifacts into `experiments/results/`.

## Assumptions (temporary)

* Canonical experiment outputs should live under timestamped run directories beneath `experiments/results/`.
* `examples/user_abr/seed_cache/` should remain cache-only, not analysis output.
* `results/` and `examples/user_abr/results*` should become temporary/internal working directories or be redirected away entirely.

## Open Questions

* Should direct `examples/user_abr/runEoH.py` runs also be forced into the canonical `experiments/results/<run-id>/...` layout, or only the top-level experiment workflow script?

## Requirements (evolving)

* Document what each ABR-related directory is for.
* Make run output locations deterministic and non-overlapping.
* Preserve seed-cache reuse without mixing it with experiment results.
* Define cleanup/retention rules for temporary and backup run artifacts.
* Record the workflow in project docs so future tools follow it.
* Use timestamped run directories as the canonical experiment result layout.

## Acceptance Criteria (evolving)

* [ ] One canonical output layout is chosen and documented.
* [ ] Raw run outputs, analysis outputs, and cache outputs have separate paths.
* [ ] A future tool can run ABR experiments without inventing new result directories.
* [ ] The documented workflow explains what may be deleted, retained, or versioned.

## Definition of Done (team quality bar)

* Docs/notes updated if behavior changes
* Source scripts follow the agreed path contract
* Generated artifacts are excluded from git tracking

## Out of Scope (explicit)

* Re-running the full experiment just to rename old outputs
* Changing ABR algorithm logic

## Technical Notes

* Current relevant files:
  * `examples/user_abr/runEoH.py`
  * `experiments/run_experiment.sh`
  * `experiments/collect_results.py`
  * `experiments/plot_results.py`
  * `.trellis/spec/backend/quality-guidelines.md`
* Likely canonical layout direction:
  * `experiments/results/<run-id>/raw/eoh/...`
  * `experiments/results/<run-id>/analysis/...`
  * `experiments/results/<run-id>/logs/...`
  * `examples/user_abr/seed_cache/<dataset>/...`

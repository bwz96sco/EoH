# ABR Parallel Experiment Variants

## Goal

Add experiment workflows for two controlled ABR reruns:

1. per-dataset evolution runs to measure training-dataset impact
2. single-seed control runs on `ABRBench-3G` and `ABRBench-4G+` to measure initialization impact

The workflows must support concurrent execution without corrupting outputs or shared intermediate state.

## Requirements

- Keep the previous mixed-dataset experiment behavior available.
- Add a way to evolve on one dataset at a time for datasets such as `FCC-18`, `Oboe`, `Norway3G`, and others.
- Add a way to run the mixed `ABRBench-3G` and `ABRBench-4G+` experiments with a single initial seed instead of the current full seed set.
- Ensure each concurrent run writes to isolated result directories under `experiments/results/<run-id>/...`.
- Prevent concurrent runs from overwriting shared mutable state such as SABR config files, seed cache files, temp seed files, or SABR evaluation logs.
- Preserve analysis artifacts so the new variants can be compared against prior canonical runs.
- Document or encode the intended concurrency-safe execution pattern in the workflow.

## Acceptance Criteria

- [ ] There is a supported command path for per-dataset evolution experiments.
- [ ] There is a supported command path for single-seed control experiments.
- [ ] Running the two experiment families at the same time does not overwrite each other's outputs.
- [ ] Shared state hazards are either removed or isolated behind per-run paths/worktrees.
- [ ] Existing mixed-dataset experiments still work after the change.
- [ ] The implementation is validated with at least smoke-level command checks or dry-run verification.

## Technical Notes

- Current likely touch points:
  - `experiments/run_experiment.sh`
  - `experiments/run_layout.py`
  - `examples/user_abr/runEoH.py`
  - `examples/user_abr/prob.py`
  - `env/SABR/eval_eoh_in_sabr.py`
  - `experiments/collect_results.py`
  - `experiments/plot_results.py`
  - `experiments/generate_run_report.py`
  - `experiments/update_experiment_tracker.py`
- Known concurrency hazards from repo inspection:
  - `experiments/run_experiment.sh` edits `env/SABR/config.py` and `env/SABR/build_env_c_plus/config.h`
  - SABR baselines and EoH bridge evaluation write into fixed `env/SABR/test_results/<dataset>/` directories
  - `examples/user_abr/runEoH.py` uses shared `examples/user_abr/seed_cache/<dataset>/`
- Preferred mitigation order:
  - avoid mutating shared config when a runtime override can be used
  - route run outputs and logs through explicit per-run directories
  - if shared SABR state remains unavoidable, execute concurrent jobs in isolated worktrees

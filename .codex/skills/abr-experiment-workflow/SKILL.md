---
name: abr-experiment-workflow
description: "Use when running, rerunning, comparing, or validating ABR experiments in this repo. Chooses between the full mixed runner and the single-target EoH runner, enforces canonical outputs under experiments/results/<run-id>/..., preserves seed-cache rules, standardizes explicit run-matrix concurrency, and warns about backup.env and the nested env/SABR repo."
---

# ABR Experiment Workflow

Use this skill for any ABR experiment task in EoH. The goal is to keep every experiment on the same command path, output layout, and result-tracking flow.

## Core Rules

- Prefer wrapper scripts under `experiments/`. Do not start with ad hoc direct calls to `examples/user_abr/runEoH.py` unless the user explicitly wants low-level debugging.
- Treat `experiments/results/<run-id>/` as the canonical output root for experiment artifacts.
- Treat `examples/user_abr/seed_cache/` as cache-only state, not canonical results.
- Before launching long runs, check `experiments/private/backup.env` and tell the user if remote backup is active.
- Remember that `env/SABR` is a nested git repo. If a task changes SABR files, report that those changes live outside the top-level git index.

## Choose The Runner

There are three supported runners:

| Workflow | Use when | Command |
|----------|----------|---------|
| Standard mixed run | Full baseline + mixed `ABRBench-3G` and `ABRBench-4G+` workflow | `bash experiments/run_experiment.sh` |
| Single target run | One evolution target, optional custom eval scope, and all concurrent EoH-only studies | `ABR_EOH_DATASET=FCC-18 bash experiments/run_eoh_target_experiment.sh` |
| Full impact wave | Combined dataset-impact + seed-impact study with Stage-A/Stage-B orchestration | `bash experiments/run_full_impact_wave.sh` |

## Important Environment Knobs

### Shared knobs

- `ABR_RUN_ID`: explicit canonical run id. If unset, the workflow generates one.
- `ABR_RUN_LABEL`: label suffix used when `ABR_RUN_ID` is unset.
- `EC_N_POP`, `EXP_N_PROC`, `EVA_TIMEOUT`: evolution settings.
- `ABR_SKIP_TRACKER_UPDATE=1`: skip tracker refresh in this process.

### Single target

- `ABR_EOH_DATASET`: required evolution target.
- `ABR_EVAL_DATASETS`: optional comma-separated eval datasets.
- `ABR_OUTPUT_NAME`: optional output name under `raw/eoh/`.
- `ABR_SEED_NAME` or `ABR_SEED_INDEX`: optional seed filter passed through to `runEoH.py`.

## Canonical Output Contract

Every standard experiment flow should end up in:

```text
experiments/results/<run-id>/
├── raw/
│   ├── eoh/
│   └── eval_logs/
├── analysis/
│   ├── results_summary.csv
│   ├── plots/
│   └── run_report.md
└── logs/
    └── full_pipeline.log
```

Related non-canonical state:

- `examples/user_abr/seed_cache/<dataset>/...`: seed generation cache
- `examples/user_abr/seed_cache/<dataset>/name-<seed>/...`: seed-specific cache
- `examples/user_abr/seed_cache/_seed_specs/...`: generated seed-json specs for `runEoH.py`

## Concurrency Rules

### Safe in one checkout

These EoH-only workflows are safe to run concurrently in the same checkout when each job uses a unique `ABR_RUN_ID`:

- multiple `experiments/run_eoh_target_experiment.sh` processes

Why:

- `sim_eoh` logs are written to run-local `raw/eval_logs/<dataset>/`
- these flows do not run baseline phase 2 when you reuse existing baselines
- tracker refresh can be deferred until the end of the whole wave

### Do not parallelize in one checkout

Do not run multiple baseline-producing `experiments/run_experiment.sh` processes concurrently in the same checkout.

Reason:

- phase 2 still edits shared SABR state in `env/SABR/config.py` and `env/SABR/build_env_c_plus/config.h`
- phase 2 writes shared baseline logs under `env/SABR/test_results/<dataset>/`

For concurrent baseline-producing runs, either:

- serialize them in one checkout, or
- run them in separate worktrees/checkouts

## OOD Dataset Rule

For the default dataset-impact matrix, use only datasets with `TRAIN_TRACES` and exclude:

- `HSR`
- `Ghent`
- `Lab`

Only include those explicitly when you intentionally want OOD training fallback to test traces.

## Tracker Rule

- For a single top-level run, let the runner refresh the tracker normally.
- For multiple concurrent `run_eoh_target_experiment.sh` jobs, set `ABR_SKIP_TRACKER_UPDATE=1` on each job and run this once after all jobs complete:

```bash
python3 experiments/update_experiment_tracker.py
```

## Recommended Procedure

1. Classify the request as standard mixed or EoH-only study.
2. Check whether remote backup is active via `experiments/private/backup.env`.
3. Use `run_experiment.sh` for the legacy full pipeline, otherwise use `run_eoh_target_experiment.sh`.
4. For dataset-impact or seed-impact studies, either build an explicit run matrix over `run_eoh_target_experiment.sh` or use `run_full_impact_wave.sh` for the standard combined wave.
5. If running multiple EoH-only jobs in parallel, keep tracker refresh off during the wave and refresh once at the end.
6. After completion, report the run ids and relevant paths under `experiments/results/`.

## Explicit Run Matrices

For EoH-only studies, express the experiment as explicit jobs over `run_eoh_target_experiment.sh`.

### Dataset-impact study

- Use one job per dataset target.
- Default target matrix:
  `FCC-16`, `FCC-18`, `Oboe`, `Puffer-21`, `Puffer-22`, `Norway3G`, `Lumos4G`, `Lumos5G`, `SolisWi-Fi`
- Recommended evaluation scope is the full suite matching the target:
  - 3G targets evaluate on `FCC-16,FCC-18,Oboe,Puffer-21,Puffer-22,HSR`
  - 4G+ targets evaluate on `Norway3G,Lumos4G,Lumos5G,SolisWi-Fi,Ghent,Lab`

Command shape:

```bash
ABR_RUN_ID=<run-id> \
ABR_EOH_DATASET=<target> \
ABR_OUTPUT_NAME=<target> \
ABR_EVAL_DATASETS=<suite-csv> \
ABR_SKIP_TRACKER_UPDATE=1 \
SKIP_PHASE_3=1 \
SKIP_PHASE_4=1 \
bash experiments/run_eoh_target_experiment.sh
```

### Seed-impact study

- Use one job per `(target, seed)` pair.
- Default targets: `ABRBench-3G`, `ABRBench-4G+`
- Default seeds: `bb`, `bola`, `quetra`, `robust_mpc`, `rate_based`

Command shape:

```bash
ABR_RUN_ID=<run-id> \
ABR_EOH_DATASET=<ABRBench-3G-or-ABRBench-4G+> \
ABR_OUTPUT_NAME=<same-target> \
ABR_SEED_NAME=<seed> \
ABR_SKIP_TRACKER_UPDATE=1 \
SKIP_PHASE_3=1 \
SKIP_PHASE_4=1 \
bash experiments/run_eoh_target_experiment.sh
```

### Resume evaluation and analysis

After phase-1-only jobs finish, rerun the same job with the same `ABR_RUN_ID` and same target/seed inputs, but set:

```bash
SKIP_PHASE_1=1
```

Leave phase 3 and phase 4 enabled so the run writes evaluation logs and analysis into the existing canonical run directory.

## Avoid

- Do not invent new result directories outside `experiments/results/`.
- Do not mix canonical results with `seed_cache/`.
- Do not build new family wrapper scripts for common experiment matrices.
- Do not claim a run is recorded unless a real canonical run directory still exists under `experiments/results/`.

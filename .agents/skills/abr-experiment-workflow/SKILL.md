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
- Before starting a new experiment series, register it under `experiments/campaigns/` and record what the campaign is trying to prove, what factors will change, and what runs are planned.
- For every changed experiment attempt inside a campaign, record a short `Key Change` note so the tracker shows exactly what changed relative to the series baseline or sibling runs.
- Before launching long runs, check `experiments/private/backup.env` and tell the user if remote backup is active.
- Remember that `env/SABR` is a nested git repo. If a task changes SABR files, report that those changes live outside the top-level git index.
- Keep campaign and tracker records in sync with the primary local repo checkout. Worktrees, branches, and remote checkouts may isolate code changes and runtime artifacts, but `experiments/campaigns/` and `experiments/experiments_tracker.md` should be updated in the main checkout as the shared source of truth.

## Worktree / Branch Discipline

When exploring code changes for experiments (new fitness modes, prompt modifications, population management changes, feedback enhancements, etc.), always work in a **git worktree** or a **new branch**.

- Create the worktree or branch BEFORE making any code modifications.
- Name it after the experiment: `experiment/<campaign>-<variant>` (e.g., `experiment/3g-cvar-single-seed`).
- Run the experiment from that worktree/branch checkout.
- Only merge back to the primary branch after results confirm the change is worth keeping.
- If results show no improvement, archive or delete the worktree/branch without polluting the main checkout.

This ensures:
1. The main checkout stays clean, runnable, and reproducible.
2. Multiple experimental code variants can coexist and run in parallel.
3. Failed experiments do not leave dead code behind.
4. Each experiment's code state is reproducible from its git ref.

For remote servers: push the branch, clone or pull it on the server, and run from there. Results can be tracked via the global tracker regardless of which checkout produced them.

Important distinction:

- **Isolate code changes** in worktrees / branches / remote experiment checkouts.
- **Do not isolate bookkeeping**. Campaign registration and tracker updates belong in the primary local repo so later sessions do not lose the experiment narrative.
- Every changed run in a campaign should carry a `Key Change` summary in the series tracker. If you regenerate the tracker, preserve or re-supply those summaries rather than letting them disappear.

## Experiment Lifecycle

Every experiment follows this lifecycle:

1. **Plan**: Register campaign in `experiments/campaigns/`, define run matrix
2. **Pre-flight**: Validate environment (see Pre-flight Check)
3. **Launch**: Start runner script(s) -- auto-registers in global tracker
4. **Monitor**: Tail logs, check generation progress
5. **Collect**: Runner auto-generates analysis (CSV, plots, report)
6. **Record**: Runner auto-updates global tracker; manually update series tracker in the main local checkout
7. **Cleanup**: Remove temporary worktrees if used

## Pre-flight Check

Before launching any experiment:

1. Verify SABR build: `env/SABR/build_env_c_plus/` binary exists and matches source
2. Verify Python venv: `env/SABR/venv/bin/python` works
3. Check disk space: `experiments/results/` partition has sufficient free space
4. Validate `.env`: confirm `ABR_FITNESS_MODE`, LLM API key, and model name are correct
5. For phase 2: confirm `env/SABR/config.py` and `config.h` are not being written by another process
6. Check `experiments/private/backup.env` and tell the user if remote backup is active

## Default Workflow

For future ABR experiments, the default flow should be:

1. Campaign registration: add or update a tracker in `experiments/campaigns/` that states the objective, the experimental factor being changed, the expected comparison metric, and the planned run matrix.
2. Phase 1: run EoH evolution. If there are multiple EoH-only jobs, this is the phase that can be parallelized.
3. Phase 2: reuse existing SABR baseline logs whenever the required baseline set already exists. Only rerun phase 2 when the baselines are genuinely missing, invalid, or intentionally changed.
4. Phase 3: evaluate the EoH result on the requested datasets.
5. Phase 4: collect results, generate plots/report, and refresh trackers.

This means the normal default is not "always run the full legacy pipeline". The normal default is:

- record the campaign first
- run only the missing phases
- avoid rerunning shared baseline state when nothing baseline-related changed

## Choose The Runner

There are three supported runners:

| Workflow | Use when | Command |
|----------|----------|---------|
| Standard mixed run | Mixed `ABRBench-3G` and `ABRBench-4G+` workflow in one run id. Prefer `SKIP_PHASE_2=1` when existing baselines can be reused. | `bash experiments/run_experiment.sh` |
| Single target run | One evolution target, optional custom eval scope, and all concurrent EoH-only studies | `ABR_EOH_DATASET=FCC-18 bash experiments/run_eoh_target_experiment.sh` |
| Multi-stage wave | Multi-stage experiments with Stage-A (evolution only) + Stage-B (evaluation + analysis) orchestration | `bash experiments/run_full_impact_wave.sh` |

## Important Environment Knobs

### Shared knobs

- `ABR_RUN_ID`: explicit canonical run id. If unset, the workflow generates one.
- `ABR_RUN_LABEL`: label suffix used when `ABR_RUN_ID` is unset.
- `ABR_CAMPAIGN`: optional campaign name, auto-registered in global tracker when runner starts.
- `EC_N_POP`, `EXP_N_PROC`, `EVA_TIMEOUT`: evolution settings.
- `SKIP_PHASE_1`, `SKIP_PHASE_2`, `SKIP_PHASE_3`, `SKIP_PHASE_4`: explicit phase reuse controls for runners that support them.
- `ABR_SKIP_TRACKER_UPDATE=1`: skip tracker refresh in this process.
- `ABR_RECORD_EXPERIMENT=0`: do not back up the run to the canonical remote archive.

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

## Three-Layer Tracking

### Layer 1: Global Experiment Tracker

`experiments/experiments_tracker.md` -- git tracked, the single source of truth for all experiments.

Every experiment is registered here when it starts and updated when it completes. This file lets all agents (Claude, Codex, etc.) see the full experiment history.

**Registration rule**: Every experiment MUST be registered in the global tracker at the moment it starts, BEFORE Phase 1 begins, with `--status running`. Do NOT register experiments retroactively after completion. The runner scripts do this automatically; for manual or remote runs, call `--register` explicitly before launching.

Managed by `experiments/update_global_tracker.py`:

```bash
# Register at start (runners do this automatically)
python3 experiments/update_global_tracker.py \
    --register <run-id> --campaign <campaign> --target <dataset> --status running

# Mark complete (runners do this automatically)
python3 experiments/update_global_tracker.py --complete <run-id>

# Scan results/ for unregistered runs
python3 experiments/update_global_tracker.py --scan --campaign <campaign>
```

### Layer 2: Campaign Series Tracker

`experiments/campaigns/<series>.md` -- git tracked, one file per research series.

Before starting a new series, register it in `experiments/campaigns/README.md`.

After experiments complete, generate or update the series tracker:

```bash
python3 experiments/update_series_tracker.py \
    --name "series-name" \
    --objective "What this series aims to achieve" \
    --baseline "87.0 (Quetra seed, seed-impact study)" \
    --metric "ABRBench-3G (avg)" \
    --run /path/to/run-dir:LabelA \
    --run /path/to/another-dir:LabelB
```

The script also copies `results_summary.csv` to `experiments/campaigns/<series>/` for git tracking.

Manually fill in the **Analysis** and **Next Steps** sections. These are preserved on re-runs.

### Layer 3: Per-Run Analysis

`experiments/results/<run-id>/analysis/` -- NOT git tracked.

Contains `results_summary.csv`, `run_report.md`, and `plots/`. Generated automatically by phase 4. For full details of a specific experiment, look here.

### Campaign-First Rule

Before starting a new experiment series, create or update a campaign entry in `experiments/campaigns/README.md`.

Even when the experiment will run from a worktree or a remote clone, do this registration in the main local checkout first.

A campaign record should answer:

- What question the series is trying to answer
- Which factor is intentionally changed
- Which factors are held fixed
- Which run ids or planned run matrix belong to the series

### Tracker Update Rules

- For a single run, the runner auto-updates the global tracker.
- For multiple concurrent jobs, set `ABR_SKIP_TRACKER_UPDATE=1` on each and run once after all complete:

```bash
python3 experiments/update_global_tracker.py --scan
```

- After a series completes, run `update_series_tracker.py` to generate the campaign tracker.

## Recommended Procedure

1. Classify the request as standard mixed or EoH-only study.
2. Register or update the campaign under `experiments/campaigns/` before launching runs.
3. Run pre-flight check.
4. Decide which phases are actually missing. Reuse phase 2 by default if the needed SABR baseline logs already exist and baseline code/config did not change. `run_experiment.sh` now auto-detects this when `SKIP_PHASE_2` is not explicitly set.
5. Use `run_experiment.sh` only when you intentionally want the mixed workflow in one run id. Otherwise use `run_eoh_target_experiment.sh`.
6. For dataset-impact or seed-impact studies, either build an explicit run matrix over `run_eoh_target_experiment.sh` or use `run_full_impact_wave.sh` for the standard combined wave.
7. If running multiple EoH-only jobs in parallel, keep tracker refresh off during the wave and refresh once at the end.
8. After completion, verify global tracker is updated. Run series tracker if applicable.

## Backup Rule

- Canonical remote backup is for completed experiment records only.
- Partial runs with `SKIP_PHASE_3=1` or `SKIP_PHASE_4=1` do not back up automatically.
- Runs whose canonical run id includes `smoke` or `probe` do not back up automatically.
- For any other ad hoc or debug run, set `ABR_RECORD_EXPERIMENT=0`.

## Remote / Off-Site Experiments

When experiments run on remote servers (GPU clusters, VAST.ai, etc.) or in checkouts that are not the primary local repo:

1. **Push first**: Ensure the remote checkout has the latest `experiments/update_global_tracker.py` and `experiments/experiments_tracker.md`. Push to the shared branch before starting remote runs.
2. **Auto-tracking**: If the runner script calls `--register` and `--complete` automatically, the tracker is updated on the remote. Pull the tracker file after the run completes.
3. **Manual registration**: If the remote checkout does NOT have the tracker infrastructure, or the experiment was run ad hoc, register manually after the run:

```bash
python3 experiments/update_global_tracker.py \
    --register <run-id> \
    --campaign <campaign> --target <dataset> --status completed \
    --result "3G:XX.X" --notes "description" \
    --started YYYY-MM-DD --completed YYYY-MM-DD
```

4. **Autonomous agents**: Codex or other agents running experiments remotely MUST push tracker updates to the shared branch so other agents can see what ran. Set `ABR_CAMPAIGN` so the run is associated with the correct campaign.
5. **Result retrieval**: After remote runs complete, either copy `results_summary.csv` to the local `experiments/results/<run-id>/analysis/` or use the `--result` flag to manually record the key metric.

## Multi-Stage Experiments

For studies that require multiple evolution runs, express the experiment as explicit jobs over `run_eoh_target_experiment.sh` or use `run_full_impact_wave.sh` for standard combined waves.

The following are common patterns for multi-factor studies.

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

If the required SABR baseline logs already exist, also set:

```bash
SKIP_PHASE_2=1
```

That is the normal default for reruns that only changed the EoH side.

## Avoid

- Do not invent new result directories outside `experiments/results/`.
- Do not mix canonical results with `seed_cache/`.
- Do not build new family wrapper scripts for common experiment matrices.
- Do not claim a run is recorded unless a real canonical run directory still exists under `experiments/results/`.

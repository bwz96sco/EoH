---
name: abr-experiment-workflow
description: "Use when running, rerunning, comparing, validating, or scheduling ABR experiments in this repo. Chooses between the full mixed runner and the single-target EoH runner, enforces canonical outputs under experiments/results/<run-id>/..., uses the note-vault queue/tracker for paper campaigns, preserves seed-cache rules, standardizes explicit run-matrix concurrency, and warns about backup.env and the nested env/SABR repo."
---

# ABR Experiment Workflow

Use this skill for any ABR experiment task in EoH. The goal is to keep every experiment on the same command path, output layout, and result-tracking flow.

Project-local note paths in this skill are relative to workspace root `/Users/zhangbowen/Projects/EoABR`. Run experiment commands from `/Users/zhangbowen/Projects/EoABR/code/EoH` unless a task explicitly uses a worktree or remote checkout.

## Core Rules

- Prefer wrapper scripts under `experiments/`. Do not start with ad hoc direct calls to `examples/user_abr/runEoH.py` unless the user explicitly wants low-level debugging.
- Treat `experiments/results/<run-id>/` as the canonical output root for experiment artifacts.
- Treat `examples/user_abr/seed_cache/` as cache-only state, not canonical results.
- Run Python project scripts with `uv run python ...` from the `code/EoH` checkout.
- Before starting a new experiment series, register it under `note/EoABR-vault/experiments/campaigns/` and record what the campaign is trying to prove, what factors will change, and what runs are planned.
- For every changed experiment attempt inside a campaign, record a short `Key Change` note so the tracker shows exactly what changed relative to the series baseline or sibling runs.
- Before launching long runs, check `experiments/private/backup.env` and tell the user if remote backup is active.
- Remember that `env/SABR` is a nested git repo. If a task changes SABR files, report that those changes live outside the top-level git index.
- Keep campaign, tracker, and paper queue records in sync with the primary note vault. Worktrees, branches, and remote checkouts may isolate code changes and runtime artifacts, but `note/EoABR-vault/experiments/campaigns/`, `note/EoABR-vault/experiments/experiments_tracker.md`, and `note/EoABR-vault/experiments/plans/paper_experiment_queue.yaml` are the shared source of truth for paper-campaign state.

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

### Checkout Naming Convention

Use stable, predictable checkout roots instead of ad hoc directories.

- Primary local code checkout: `code/EoH`.
- Primary bookkeeping repo: `note/EoABR-vault`.
- Local experiment worktrees: sibling directories named `EoH-exp-<campaign-or-variant>`.
- Primary remote checkout: a stable shared clone such as `/root/code/EoH-repro`.
- Remote experiment checkouts: `/root/code/exp-<campaign-or-variant>`.

Rules:

1. Do not mix multiple unrelated naming schemes on the same machine.
2. If a remote run needs code isolation, create a dedicated `exp-...` checkout instead of reusing the primary remote clone.
3. If a run does **not** need code isolation, prefer the primary remote checkout and keep results under that checkout's `experiments/results/<run-id>/`.
4. Regardless of where the run executed, sync the final artifacts back into the main local checkout under `experiments/results/<run-id>/` and `experiments/campaign_data/<series>/` so the repo keeps one canonical history.

Important distinction:

- **Isolate code changes** in worktrees / branches / remote experiment checkouts.
- **Do not isolate bookkeeping**. Campaign registration, tracker updates, and paper queue status belong in the primary note vault so later sessions do not lose the experiment narrative.
- Every changed run in a campaign should carry a `Key Change` summary in the series tracker. If you regenerate the tracker, preserve or re-supply those summaries rather than letting them disappear.

## Experiment Lifecycle

Every experiment follows this lifecycle:

1. **Plan**: Register campaign in `note/EoABR-vault/experiments/campaigns/`, define run matrix or queue task
2. **Pre-flight**: Validate environment (see Pre-flight Check)
3. **Launch**: Start runner script(s) -- auto-registers in global tracker
4. **Monitor**: Tail logs, check generation progress
5. **Collect**: Runner auto-generates analysis (CSV, plots, report)
6. **Record**: Runner auto-updates global tracker; manually update series tracker and queue status in the note vault
7. **Cleanup**: Remove temporary worktrees if used

## Post-Launch Health Gate

Do not treat a run as "successfully launched" just because:

- the shell command returned
- a wrapper process still exists
- the run root was created
- or `full_pipeline.log` started receiving output

After every launch, explicitly inspect the run log and confirm the job is making **healthy phase progress**.

Minimum checks:

1. Tail the canonical `logs/full_pipeline.log` (and any launcher log if using `nohup`).
2. Confirm the run passed the wrapper startup stage and entered the real workload:
   - EoH phase: operator output, generation progress, or `population_generation_*.json`
   - Eval phase: dataset loop progress and log writes
3. Look for health blockers before reporting success:
   - repeated `API error`
   - `RemoteDisconnected`
   - `429`
   - `Traceback`
   - `worker_budget_timeout`
   - repeated `llm_timeout` / `eval_timeout`
   - no new population files for an extended interval
4. If the run is unhealthy, report it as such immediately; do not summarize it as a valid experiment result.

Interpretation rule:

- `results_summary.csv` + clean phase completion logs = valid completed run
- process alive but repeated connection / timeout errors = unhealthy run
- no `population_generation_1+` and no analysis outputs = not a valid completed run

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

1. Campaign registration: add or update a tracker in `note/EoABR-vault/experiments/campaigns/` that states the objective, the experimental factor being changed, the expected comparison metric, and the planned run matrix.
2. Phase 1: run EoH evolution. If there are multiple EoH-only jobs, this is the phase that can be parallelized.
3. Phase 2: reuse existing SABR baseline logs whenever the required baseline set already exists. Only rerun phase 2 when the baselines are genuinely missing, invalid, or intentionally changed.
4. Phase 3: evaluate the EoH result on the requested datasets.
5. Phase 4: collect results, generate plots/report, and refresh trackers.

This means the normal default is not "always run the full legacy pipeline". The normal default is:

- record the campaign first
- run only the missing phases
- avoid rerunning shared baseline state when nothing baseline-related changed

## Paper OpenRouter Campaign Rules

For paper-facing EoABR experiments, first read:

- `note/EoABR-vault/experiments/plans/paper_experiment_plan.md`
- `note/EoABR-vault/experiments/plans/paper_experiment_checklist.md`
- `note/EoABR-vault/experiments/plans/paper_experiment_queue.yaml`

Use the queue as task state. Pick one `ready` task or a small same-protocol batch, mark it `running` before launch, then mark it `completed`, `failed`, `blocked`, or `reusable` after verification.

Paper-valid EoABR evolution runs must:

- use OpenRouter through the formal OpenAI-compatible endpoint
- use fixed OpenRouter model IDs, not aliases such as `latest`
- record a frozen manifest beside run artifacts
- record model snapshot, provider route policy, route/usage metadata, timeout policy, retry/error counts, invalid offspring, token usage, and estimated cost
- disable silent fallback routing for strict model/provider comparisons
- complete the planned generations and evaluation without manual cherry-picking

Do not report mixed-provider pilot results as final paper evidence. Keep Table 1 model rows separate, such as `EoABR (Grok 4.3)` and `EoABR (DeepSeek V4 Pro)`, instead of averaging different LLM backbones into one EoABR score.

Before scheduling a new paper run, check the plan's cross-table reuse map and the queue's `reuse_targets` / `reuse_source` fields. Do not rerun an arm if an existing formal OpenRouter run has the same dataset, model ID, provider route policy, seed selection, population size, generations, evaluator, parser, timeout policy, and manifest version.

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

Launcher/log rule:

- Do **not** write ad hoc launcher logs like `.launch-*.log` at repo root.
- If a detached launcher log is needed, place it under the canonical run root:
  `experiments/results/<run-id>/logs/launcher.log`
- `full_pipeline.log` under the same `logs/` directory remains the primary source of truth.
- If you cannot route a launcher's stdout/stderr into the canonical run log tree, do not introduce a separate launcher log at all.

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

## Tracking Layers

### Layer 1: Global Experiment Tracker

`note/EoABR-vault/experiments/experiments_tracker.md` -- git tracked in the note vault, the single source of truth for all experiments.

Every experiment is registered here when it starts and updated when it completes. This file lets all agents (Claude, Codex, etc.) see the full experiment history.

**Registration rule**: Every experiment MUST be registered in the global tracker at the moment it starts, BEFORE Phase 1 begins, with `--status running`. Do NOT register experiments retroactively after completion. The runner scripts do this automatically; for manual or remote runs, call `--register` explicitly before launching.

Managed by `experiments/update_global_tracker.py`:

```bash
# Register at start (runners do this automatically)
uv run python experiments/update_global_tracker.py \
    --register <run-id> --campaign <campaign> --target <dataset> --status running

# Mark complete (runners do this automatically)
uv run python experiments/update_global_tracker.py --complete <run-id>

# Scan results/ for unregistered runs
uv run python experiments/update_global_tracker.py --scan --campaign <campaign>
```

### Layer 2: Campaign Series Tracker

`note/EoABR-vault/experiments/campaigns/<series>.md` -- git tracked in the note vault, one file per research series.

Before starting a new series, register it in `note/EoABR-vault/experiments/campaigns/README.md`.

After experiments complete, generate or update the series tracker:

```bash
uv run python experiments/update_series_tracker.py \
    --name "series-name" \
    --objective "What this series aims to achieve" \
    --baseline "87.0 (Quetra seed, seed-impact study)" \
    --metric "ABRBench-3G (avg)" \
    --run /path/to/run-dir:LabelA \
    --run /path/to/another-dir:LabelB
```

The script also copies `results_summary.csv` to `experiments/campaign_data/<series>/` for git tracking.

Manually fill in the **Analysis** and **Next Steps** sections. These are preserved on re-runs.

### Layer 3: Paper Experiment Queue

`note/EoABR-vault/experiments/plans/paper_experiment_queue.yaml` -- git tracked in the note vault, one machine-readable task queue for paper-facing OpenRouter experiments.

The queue is campaign state, not executable code. It records planned tasks, dependencies, status, protocol fields, manifest paths, artifact paths, reuse sources, and verification notes. Agents should update the queue after each task instead of relying on chat history.

### Layer 4: Per-Run Analysis

`experiments/results/<run-id>/analysis/` -- NOT git tracked.

Contains `results_summary.csv`, `run_report.md`, and `plots/`. Generated automatically by phase 4. For full details of a specific experiment, look here.

### Campaign-First Rule

Before starting a new experiment series, create or update a campaign entry in `note/EoABR-vault/experiments/campaigns/README.md`.

Even when the experiment will run from a worktree or a remote clone, do this registration in the primary local note vault first.

A campaign record should answer:

- What question the series is trying to answer
- Which factor is intentionally changed
- Which factors are held fixed
- Which run ids or planned run matrix belong to the series

### Tracker Update Rules

- For a single run, the runner auto-updates the global tracker.
- For multiple concurrent jobs, set `ABR_SKIP_TRACKER_UPDATE=1` on each and run once after all complete:

```bash
uv run python experiments/update_global_tracker.py --scan
```

- After a series completes, run `update_series_tracker.py` to generate the campaign tracker.

## Recommended Procedure

1. Classify the request as standard mixed or EoH-only study.
2. Register or update the campaign under `note/EoABR-vault/experiments/campaigns/` before launching runs.
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

1. **Push first**: Ensure the remote checkout has the latest runner scripts and experiment code. Push the code branch before starting remote runs.
2. **Queue export**: If the remote server cannot access `note/EoABR-vault`, export only the relevant queue rows or commands. After the run, sync status, manifest path, artifact path, and failure notes back to the note-vault queue.
3. **Auto-tracking**: If the runner script calls `--register` and `--complete` automatically, confirm whether the remote wrote to the note vault or to a local fallback tracker. The note-vault tracker remains the source of truth.
4. **Manual registration**: If the remote checkout does NOT have the tracker infrastructure, or the experiment was run ad hoc, register manually after the run from the primary local `code/EoH` checkout:

```bash
uv run python experiments/update_global_tracker.py \
    --register <run-id> \
    --campaign <campaign> --target <dataset> --status completed \
    --result "3G:XX.X" --notes "description" \
    --started YYYY-MM-DD --completed YYYY-MM-DD
```

5. **Autonomous agents**: Codex or other agents running experiments remotely MUST update the note-vault queue/tracker after retrieval so other agents can see what ran. Set `ABR_CAMPAIGN` so the run is associated with the correct campaign.
6. **Result retrieval**: After remote runs complete, either copy `results_summary.csv` to the local `experiments/results/<run-id>/analysis/` or use the `--result` flag to manually record the key metric.

7. **No repo-root launch logs**: Remote checkouts follow the same rule as local ones. Keep launcher output under `experiments/results/<run-id>/logs/` and delete transient repo-root `.launch-*` files instead of letting them accumulate.

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

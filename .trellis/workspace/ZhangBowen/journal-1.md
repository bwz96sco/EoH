# Journal - ZhangBowen (Part 1)

> AI development session journal
> Started: 2026-02-19

---



## Session 1: Formalize ABR Experiment Workflow And Record Model Runs

**Date**: 2026-03-27
**Task**: Formalize ABR Experiment Workflow And Record Model Runs
**Branch**: `main`

### Summary

(Add summary)

### Main Changes

| Area | Description |
|------|-------------|
| Workflow | Canonical ABR experiment workflow now writes under `experiments/results/<run-id>/raw`, `analysis`, and `logs` instead of mixing outputs across repo root and `examples/user_abr/`. |
| Tracking | Added generated experiment ledger `experiments/experiment_index.md` with automatic EXIT-time refresh from `experiments/update_experiment_tracker.py`. |
| Cache Contract | Kept `examples/user_abr/seed_cache/<dataset>/` as cache-only and separated it from final experiment artifacts. |
| Baseline Provenance | Workflow records whether SABR baselines were rerun or reused, so comparisons stay interpretable when phase 2 is skipped. |

**Committed Workflow Files**:
- `experiments/run_experiment.sh`
- `experiments/run_layout.py`
- `experiments/collect_results.py`
- `experiments/plot_results.py`
- `experiments/update_experiment_tracker.py`
- `experiments/experiment_index.md`
- `.trellis/spec/backend/directory-structure.md`
- `.trellis/spec/backend/quality-guidelines.md`

**Completed Canonical Runs**:
- `20260326-145715-grok-4.1-expert`
  - Summary CSV: `experiments/results/20260326-145715-grok-4.1-expert/analysis/results_summary.csv`
  - Overall average: `EoH = 455.0862`, `BeamSearch = 597.5625`
  - Suite averages: `ABRBench-3G = -120.8478`, `ABRBench-4G+ = 1031.0202`
- `20260326-202134-grok-4.1-thinking`
  - Summary CSV: `experiments/results/20260326-202134-grok-4.1-thinking/analysis/results_summary.csv`
  - Overall average: `EoH = 452.6828`, `BeamSearch = 597.5625`
  - Suite averages: `ABRBench-3G = -122.0663`, `ABRBench-4G+ = 1027.4318`

**Notes**:
- The experiment workflow task remains active because a follow-up report-generation improvement is still uncommitted.
- The older completed task `03-10-abr-ctx-contract` was archived before recording this session.


### Git Commits

| Hash | Message |
|------|---------|
| `3e3b2f4` | (see git log) |
| `ef353c0` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 2: Finalize ABR Reporting Privacy And Backup Workflow

**Date**: 2026-03-27
**Task**: Finalize ABR Reporting Privacy And Backup Workflow
**Branch**: `main`

### Summary

(Add summary)

### Main Changes

| Area | Description |
|------|-------------|
| Run Reports | Added canonical per-run `analysis/run_report.md` generation and updated the report to separate fair online-baseline gaps from oracle/reference `BeamSearch`/`MFD` comparisons. |
| Privacy | Moved the experiment tracker from tracked `experiments/experiment_index.md` to gitignored `experiments/private/experiment_index.md` so future run metadata is not published by default. |
| Backup Workflow | Added optional `rclone` backup support to `experiments/run_experiment.sh`, with post-run copy of the canonical run root and private tracker, plus opt-in seed-cache backup. |
| Local Backup Defaults | Added gitignored `experiments/private/backup.env` support so local OneDrive backup roots can be configured without hardcoding personal remotes into tracked source. |

**Committed Files**:
- `experiments/generate_run_report.py`
- `experiments/run_experiment.sh`
- `experiments/run_layout.py`
- `experiments/update_experiment_tracker.py`
- `experiments/.gitignore`
- `.trellis/spec/backend/directory-structure.md`
- `.trellis/spec/backend/quality-guidelines.md`
- removed tracked `experiments/experiment_index.md`

**Operational Outcome**:
- Current remote backup root is `onedrive_raw:ExperimentsRecord/EoH`
- Verified remote content exists under:
  - `experiments/results/`
  - `experiments/private/`
  - `examples/user_abr/seed_cache/`
- Future workflow runs can use the local default backup root from `experiments/private/backup.env`

**Verification**:
- `python3 -m py_compile experiments/run_layout.py experiments/update_experiment_tracker.py experiments/generate_run_report.py`
- `bash -n experiments/run_experiment.sh`
- `python3 experiments/update_experiment_tracker.py`
- `rclone` remote listings verified under `onedrive_raw:ExperimentsRecord/EoH/...`

**Task Notes**:
- Archived completed task `03-25-abr-experiment-workflow`
- Remaining unrelated local state was left untouched: root `.gitignore`, `abcoder-asts/`, `pylsp/`


### Git Commits

| Hash | Message |
|------|---------|
| `37760ac` | (see git log) |
| `920ef51` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 3: Archive completed 3G experiment tasks

**Date**: 2026-04-16
**Task**: Archive completed 3G experiment tasks
**Branch**: `abr-remote-repro-20260328`

### Summary

Archived completed 3G validation and seed-round2 tasks; island experiment remains in progress and business files are still uncommitted.

### Main Changes

| Area | Status |
|------|--------|
| 3G validation round1 | Archived as a completed negative-result campaign |
| 3G seed round2 | Archived as a completed screening campaign |
| Active Trellis tasks | Cleared; no active tasks remain |
| 3G island round1 | Still running remotely on heyun; not archived |

**Notes**:
- `04-06-3g-validation-round1` and `04-12-3g-seed-round2` were archived under `.trellis/tasks/archive/2026-04/`.
- The repository working tree is still dirty with experiment/code changes outside `.trellis/`; this record only captures session bookkeeping, not a clean business-code checkpoint.
- Remote `grok2api` cutover and the restarted island run were intentionally left as ongoing work rather than closed tasks.


### Git Commits

| Hash | Message |
|------|---------|
| `d6365b9` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete

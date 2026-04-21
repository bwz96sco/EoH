# Campaign CSV Layout Cleanup

## Goal
Move campaign-tracked copied CSV artifacts into a dedicated subdirectory instead of mixing them alongside campaign markdown files or directly under each campaign's root folder.

## Requirements
- Keep campaign markdown trackers under `experiments/campaigns/<series>.md` unchanged.
- Store copied `results_summary.csv` artifacts in a separate dedicated folder hierarchy.
- Update the generator script so future tracker refreshes write to the new location.
- Update existing in-repo references that point to the old copied CSV path.
- Preserve current tracker generation behavior aside from the output location change.

## Acceptance Criteria
- [ ] `experiments/update_series_tracker.py` writes copied CSVs to a dedicated subdirectory, not directly under `experiments/campaigns/<series>/`.
- [ ] Existing campaign markdown references use the new path where needed.
- [ ] The new layout remains git-trackable and consistent with current experiment bookkeeping.
- [ ] The script still generates/updates tracker markdown successfully.

## Technical Notes
- This is a persistence/layout cleanup for campaign-level copied summaries, not a change to canonical run outputs under `experiments/results/<run-id>/analysis/results_summary.csv`.
- Prefer a minimal migration surface: keep filename shapes stable unless the directory move alone is insufficient.

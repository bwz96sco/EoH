# 3G Seed Round 2

## Goal
Design and screen a small set of stronger 3G online seed heuristics, then launch the screening campaign on the remote server.

## Requirements
- Create a new 3G campaign focused on stronger seed design rather than new fitness modes.
- Keep campaign and tracker bookkeeping in the main checkout.
- Isolate code changes in a dedicated worktree or branch before editing seed code.
- Add exactly three new seed heuristics to the ABR seed registry:
  - a QUETRA regime-aware variant
  - a RobustMPC blend variant
  - a distilled variant inspired by the current best evolved A1 heuristic
- Launch a remote screening wave for the new seeds on `ABRBench-3G`.
- Use standard ABR workflow wrappers and canonical output roots.

## Acceptance Criteria
- [ ] New campaign is registered under `experiments/campaigns/`.
- [ ] A dedicated worktree or branch exists for the code changes.
- [ ] Three new seeds are available through `ABR_SEED_NAME`.
- [ ] Local smoke validation confirms the new seeds load and execute.
- [ ] Remote screening runs are launched and registered in the tracker.
- [ ] Main-checkout tracker and campaign files reflect the launched series.

## Technical Notes
- Baseline for the new campaign is `20260402-3g-hardset-round2-a1-r1` (`QUETRA + pop25 + mean = 88.8697`).
- Screening should start with `pop=5`, `ABR_FITNESS_MODE=mean`, and `ABRBench-3G`.
- Prefer `experiments/run_eoh_target_experiment.sh` over direct `runEoH.py`.
- Reuse phase 2 baselines; do not rerun them.

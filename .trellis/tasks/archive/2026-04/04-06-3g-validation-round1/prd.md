# 3G Validation Round 1
# 3G Validation Round 1

## Goal
Test whether a held-out validation split during 3G evolution can beat the current best internal 3G baseline `A1 = QUETRA + pop25 + mean = 88.8697`.

## Requirements
- Add a deterministic train/validation split for ABR training traces without modifying `env/SABR`.
- Add validation-aware 3G fitness modes suitable for EoH evolution.
- Register a new campaign under `experiments/campaigns/` before launch.
- Run a small screening matrix remotely on `heyun` from an isolated worktree checkout.
- Reuse existing phase-2 SABR baselines; do not rerun baseline generation.

## Acceptance Criteria
- [ ] New validation-aware objective is implemented and manually smoke-checked.
- [ ] Campaign tracker records objective, baseline, and planned runs.
- [ ] Remote screening runs start successfully from isolated checkout.
- [ ] Canonical run directories are created under `experiments/results/<run-id>/...`.

## Technical Notes
- Keep the first round narrow: only `ABRBench-3G`, `QUETRA`, `pop25`, `EC_N_POP=10`.
- Compare two scalar objectives: train/validation blended mean and train/validation min gate.
- Avoid phase-2 reruns and keep tracker refresh deferred until the screening completes.
## Goal
Test whether introducing a held-out validation split during 3G evolution can beat the current best internal 3G baseline `A1 = QUETRA + pop25 + mean = 88.8697`.

## Requirements
- Add a deterministic train/validation split for ABR training traces without modifying `env/SABR`.
- Add validation-aware 3G fitness modes suitable for EoH evolution.
- Register a new campaign under `experiments/campaigns/` before launch.
- Run a small screening matrix remotely on `heyun` from an isolated worktree checkout.
- Reuse existing phase-2 SABR baselines; do not rerun baseline generation.

## Acceptance Criteria
- [ ] New validation-aware objective is implemented and manually smoke-checked.
- [ ] Campaign tracker records objective, baseline, and planned runs.
- [ ] Remote screening runs start successfully from isolated checkout.
- [ ] Canonical run directories are created under `experiments/results/<run-id>/...`.

## Technical Notes
- Keep the first round narrow: only `ABRBench-3G`, `QUETRA`, `pop25`, `EC_N_POP=10`.
- Compare two scalar objectives: train/validation blended mean and train/validation min gate.
- Avoid phase-2 reruns and keep tracker refresh deferred until the screening completes.

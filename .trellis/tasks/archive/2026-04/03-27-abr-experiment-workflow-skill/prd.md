# ABR Experiment Workflow Skill

## Goal

Turn the archived ABR experiment workflow into a reusable project-local skill so future experiment runs follow the same command paths, output layout, and concurrency rules.

## Requirements

- Create a repo-local skill for ABR experiment execution.
- Encode the canonical experiment entrypoints and when to use each one.
- Capture the canonical output layout under `experiments/results/<run-id>/...`.
- Capture seed-cache behavior and the preferred wrappers instead of ad hoc direct runs.
- Capture concurrency rules, especially the difference between safe EoH-only family runs and baseline-generating runs that still mutate SABR state.
- Add a short project-level pointer so future agents are nudged toward the skill.

## Acceptance Criteria

- [ ] A new skill exists under the repo-local skills directory.
- [ ] The skill describes the standard mixed, per-dataset, single-target, and single-seed workflows.
- [ ] The skill explains tracker-refresh and backup caveats.
- [ ] A repo-level instruction points experiment tasks to the skill.

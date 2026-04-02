# Population Diversity Maintenance for EoH

## Background

EoH uses a greedy elite selection strategy in `pop_greedy.py`:
1. Remove individuals with `objective is None`
2. Deduplicate by **exact objective value match** (fragile — two different heuristics with the same float fitness are considered duplicates)
3. Keep the top-N by objective (lower is better, since fitness = -QoE)

This causes rapid diversity collapse. On ABRBench-3G with pop_size=5, all individuals converge to conservative MPC variants within 3-4 generations (names like "PessimisticMinMPC", "SuperPessimisticMinMPC"). Once diversity collapses, crossover operators (e1, e2) produce offspring from nearly identical parents, yielding no novel strategies.

Baseline: EoH 3G best = 87.0 (pop5+quetra). With pop5+all seeds, convergence to 84.8-87.0 range regardless of seed.

## Objective

Replace the naive greedy selection with a diversity-aware population management strategy that maintains behavioral diversity while still selecting for fitness. This should allow the population to explore different strategy archetypes (conservative, aggressive, adaptive) simultaneously.

## Requirements

### 1. Behavioral descriptors from evaluation

Modify `prob.py` to return behavioral descriptors alongside fitness:

- **Add to metrics dict**:
  - `behavior_utilization`: mean bandwidth utilization (0-1)
  - `behavior_rebuffer_rate`: fraction of chunks that experienced any rebuffering
  - `behavior_switch_rate`: fraction of chunk transitions that changed bitrate
  - `behavior_min_bitrate_frac`: fraction of chunks where lowest bitrate was chosen

- These form a 4D behavior vector that characterizes HOW the heuristic achieves its QoE, not just WHAT QoE it achieves.

### 2. Diversity-aware population management

Create a new file `eoh/src/eoh/methods/management/pop_diverse.py` with a `population_management_diverse()` function:

- **Behavior-based dedup**: Instead of exact objective match, compute pairwise distance in behavior space. Two individuals are "similar" if their behavior vectors differ by less than `epsilon` in each dimension.

- **Crowding distance selection**: After removing truly duplicate code and None-fitness individuals:
  1. Sort by fitness (ascending, since lower = better for EoH)
  2. Always keep the best individual (elite preservation)
  3. For remaining slots, use a combined score: `rank_fitness * (1 - diversity_weight) + rank_crowding * diversity_weight`
  4. Crowding distance = sum of normalized differences to nearest neighbors in behavior space

- **Parameters**:
  - `diversity_weight`: float 0-1, default 0.3 (30% weight on diversity). Controllable via env var `EC_DIVERSITY_WEIGHT`.
  - `behavior_epsilon`: float, default 0.05. Two individuals within epsilon in ALL behavior dimensions are considered behaviorally identical.

### 3. Wire diversity management into EoH pipeline

Modify `eoh/src/eoh/methods/eoh/eoh_interface_EC.py`:

- In `population_generation_seed()`: Store behavioral descriptors from evaluation in a new field `individual['behavior']` (a dict or list).

- In `get_offspring()`: After successful evaluation, extract behavior from `other_inf` (the feedback string) or from a separate metrics return path.

**IMPORTANT**: The current `evaluate_with_details()` returns `(fitness, feedback_string)`. The behavior descriptors need to be embedded in the feedback string OR we need to modify the return to include them. The cleanest approach:
- Have `prob.py` `evaluate_with_details()` return a richer `other_inf` that includes both the feedback text and the behavior dict. Encode as JSON string or use a separator.
- Alternatively, add a new method `evaluate_with_behavior()` that returns `(fitness, feedback_str, behavior_dict)`.

### 4. Integrate with population_management call

In `eoh/src/eoh/methods/eoh/eoh.py` (the main EoH loop), the population management is called. Make it use `pop_diverse.py` when `EC_DIVERSITY_WEIGHT > 0`:

- Default (`EC_DIVERSITY_WEIGHT=0` or unset): Use existing `pop_greedy.py` (no behavior change)
- When `EC_DIVERSITY_WEIGHT > 0`: Use `pop_diverse.py`

### 5. Store behavior in population JSON

When saving population to `population_generation_N.json`, include the behavior dict for each individual. This enables post-hoc analysis of diversity metrics across generations.

## Files to Modify / Create

| File | Changes |
|------|---------|
| `eoh/src/eoh/methods/management/pop_diverse.py` | **NEW** — diversity-aware population management |
| `eoh/src/eoh/methods/management/__init__.py` | Export new function (if __init__.py exists) |
| `examples/user_abr/prob.py` | Return behavioral descriptors in metrics dict |
| `examples/user_abr/feedback.py` | Include behavior info in feedback string |
| `eoh/src/eoh/methods/eoh/eoh_interface_EC.py` | Store behavior in individual dict, extract from eval results |
| `eoh/src/eoh/methods/eoh/eoh.py` | Use diverse pop management when configured |

## Acceptance Criteria

1. `pop_diverse.py` exists and implements crowding-distance-based selection with configurable diversity weight.
2. Behavioral descriptors (utilization, rebuffer_rate, switch_rate, min_bitrate_frac) are computed in `prob.py` and stored per individual.
3. When `EC_DIVERSITY_WEIGHT=0` (default), behavior is identical to current `pop_greedy.py`.
4. When `EC_DIVERSITY_WEIGHT=0.3`, the population maintains at least 2 distinct behavioral archetypes across generations (verifiable from saved population JSONs).
5. No syntax errors, all existing code paths still work.
6. Population JSON files include behavior data for post-hoc analysis.

## Constraints

- Do NOT modify the `score(state, ctx)` function signature.
- Do NOT modify seed heuristics or prompts (Task A handles that).
- Do NOT modify fitness aggregation modes (Task B handles that).
- The `pop_greedy.py` file must remain unchanged — create a new file instead.
- Keep computational overhead minimal — behavior extraction should be nearly free since the data is already computed during simulation.
- Ensure backward compatibility: if behavior data is missing (e.g., from cached seeds), fall back to fitness-only selection.

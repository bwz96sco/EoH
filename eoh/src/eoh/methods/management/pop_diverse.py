"""Diversity-aware population management for EoH.

Uses crowding distance in behavior space to maintain population diversity
while still selecting for fitness.  When *diversity_weight* is 0 the
behaviour is identical to ``pop_greedy.population_management``.
"""

from __future__ import annotations

import heapq
import os
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Behaviour keys (order matters -- they define the behaviour vector)
# ---------------------------------------------------------------------------
BEHAVIOR_KEYS = [
    "behavior_utilization",
    "behavior_rebuffer_rate",
    "behavior_switch_rate",
    "behavior_min_bitrate_frac",
]


def _get_diversity_weight() -> float:
    """Read diversity weight from environment, default 0 (pure greedy)."""
    try:
        return float(os.environ.get("EC_DIVERSITY_WEIGHT", "0"))
    except (TypeError, ValueError):
        return 0.0


def _get_behavior_epsilon() -> float:
    """Read behavior epsilon from environment, default 0.05."""
    try:
        return float(os.environ.get("EC_BEHAVIOR_EPSILON", "0.05"))
    except (TypeError, ValueError):
        return 0.05


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_behavior_vector(ind: dict[str, Any]) -> np.ndarray | None:
    """Return a numpy array of the 4D behaviour descriptors, or None."""
    beh = ind.get("behavior")
    if beh is None:
        return None
    if isinstance(beh, dict):
        vals = [beh.get(k) for k in BEHAVIOR_KEYS]
        if any(v is None for v in vals):
            return None
        return np.array(vals, dtype=np.float64)
    # Allow list / array-like already
    try:
        arr = np.asarray(beh, dtype=np.float64).ravel()
        if arr.size == len(BEHAVIOR_KEYS):
            return arr
    except Exception:
        pass
    return None


def _behavior_dedup(
    pop: list[dict[str, Any]],
    epsilon: float,
) -> list[dict[str, Any]]:
    """Remove individuals whose behaviour vectors are within *epsilon* in ALL dims.

    When two individuals are behaviourally identical (within epsilon), keep
    the one with the better (lower) objective.  Individuals without behaviour
    data are always kept (they cannot be compared).
    """
    if epsilon <= 0:
        return list(pop)

    # Separate into those with and without behaviour
    with_beh: list[tuple[np.ndarray, dict]] = []
    without_beh: list[dict] = []

    for ind in pop:
        bv = _extract_behavior_vector(ind)
        if bv is not None:
            with_beh.append((bv, ind))
        else:
            without_beh.append(ind)

    # Sort by objective (lower is better) so we keep the best of duplicates
    with_beh.sort(key=lambda t: t[1].get("objective", float("inf")))

    kept: list[tuple[np.ndarray, dict]] = []
    for bv, ind in with_beh:
        is_dup = False
        for kept_bv, _kept_ind in kept:
            if np.all(np.abs(bv - kept_bv) < epsilon):
                is_dup = True
                break
        if not is_dup:
            kept.append((bv, ind))

    return [ind for _, ind in kept] + without_beh


def _crowding_distance(behavior_matrix: np.ndarray) -> np.ndarray:
    """Compute crowding distance for each row of *behavior_matrix*.

    Uses the standard NSGA-II crowding distance: for each dimension,
    sort, and add the normalized gap between neighbors.  Boundary
    individuals get infinite distance (clamped to a large float).
    """
    n, d = behavior_matrix.shape
    if n <= 2:
        return np.full(n, np.inf)

    distances = np.zeros(n, dtype=np.float64)
    for dim in range(d):
        col = behavior_matrix[:, dim]
        sorted_idx = np.argsort(col)
        col_sorted = col[sorted_idx]

        span = col_sorted[-1] - col_sorted[0]
        if span < 1e-12:
            continue  # all same in this dimension

        # Boundary individuals get large distance
        distances[sorted_idx[0]] = np.inf
        distances[sorted_idx[-1]] = np.inf

        for i in range(1, n - 1):
            distances[sorted_idx[i]] += (
                (col_sorted[i + 1] - col_sorted[i - 1]) / span
            )

    return distances


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def population_management(
    pop: list[dict[str, Any]],
    size: int,
    diversity_weight: float | None = None,
    behavior_epsilon: float | None = None,
) -> list[dict[str, Any]]:
    """Select *size* individuals from *pop* using diversity-aware selection.

    Parameters
    ----------
    pop : list[dict]
        Current population (individuals with 'objective' and optionally
        'behavior' fields).
    size : int
        Target population size.
    diversity_weight : float or None
        Weight for crowding-distance rank (0 = pure greedy, 1 = pure
        diversity).  Read from ``EC_DIVERSITY_WEIGHT`` env var when None.
    behavior_epsilon : float or None
        Threshold for behaviour-based deduplication.  Read from
        ``EC_BEHAVIOR_EPSILON`` env var when None.

    Returns
    -------
    list[dict]
        Selected population, sorted by objective (ascending = best first).
    """
    if diversity_weight is None:
        diversity_weight = _get_diversity_weight()
    if behavior_epsilon is None:
        behavior_epsilon = _get_behavior_epsilon()

    # -- Step 1: remove None-fitness individuals
    pop = [ind for ind in pop if ind.get("objective") is not None]

    if size > len(pop):
        size = len(pop)
    if size <= 0:
        return []

    # -- Fallback: pure greedy (identical to pop_greedy.py)
    if diversity_weight <= 0:
        # Exact-objective dedup (same as pop_greedy)
        unique_pop: list[dict] = []
        unique_objectives: list[float] = []
        for ind in pop:
            if ind["objective"] not in unique_objectives:
                unique_pop.append(ind)
                unique_objectives.append(ind["objective"])
        return heapq.nsmallest(size, unique_pop, key=lambda x: x["objective"])

    # -- Step 2: behaviour-based dedup
    pop = _behavior_dedup(pop, behavior_epsilon)

    if size >= len(pop):
        return sorted(pop, key=lambda x: x.get("objective", float("inf")))

    # -- Step 3: sort by fitness (ascending, lower = better)
    pop.sort(key=lambda x: x.get("objective", float("inf")))

    # Always keep the best individual (elite preservation)
    elite = pop[0]
    candidates = pop[1:]

    remaining_slots = size - 1
    if remaining_slots <= 0:
        return [elite]

    if remaining_slots >= len(candidates):
        return [elite] + candidates

    # -- Step 4: build behaviour matrix for candidates
    beh_vecs = []
    has_behavior = []
    for ind in candidates:
        bv = _extract_behavior_vector(ind)
        if bv is not None:
            beh_vecs.append(bv)
            has_behavior.append(True)
        else:
            # Use zeros as placeholder (will get low crowding distance
            # but that's fine -- they'll be ranked by fitness alone)
            beh_vecs.append(np.zeros(len(BEHAVIOR_KEYS), dtype=np.float64))
            has_behavior.append(False)

    beh_matrix = np.array(beh_vecs, dtype=np.float64)
    n_candidates = len(candidates)

    # -- Step 5: compute fitness rank (0 = best, already sorted)
    fitness_ranks = np.arange(n_candidates, dtype=np.float64)

    # -- Step 6: compute crowding distance and rank
    if beh_matrix.shape[0] >= 2 and any(has_behavior):
        cd = _crowding_distance(beh_matrix)
        # Higher crowding distance is better -> rank descending
        cd_order = np.argsort(-cd)
        crowding_ranks = np.empty(n_candidates, dtype=np.float64)
        for rank_val, idx in enumerate(cd_order):
            crowding_ranks[idx] = float(rank_val)
    else:
        # No behaviour data available -- fall back to fitness only
        crowding_ranks = fitness_ranks.copy()

    # -- Step 7: combined score (lower is better)
    # combined = fitness_rank * (1 - w) + crowding_rank * w
    combined = fitness_ranks * (1.0 - diversity_weight) + crowding_ranks * diversity_weight

    # Select top-k by combined score
    selected_indices = np.argsort(combined)[:remaining_slots]

    result = [elite] + [candidates[i] for i in selected_indices]
    result.sort(key=lambda x: x.get("objective", float("inf")))
    return result

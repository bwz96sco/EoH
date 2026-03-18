from __future__ import annotations

import math

import numpy as np

from prob import ABRProblem
from seed_heuristics import (
    score_bb,
    score_bola,
    score_quetra,
    score_rate_based,
    score_robust_mpc,
)


def _assert_scores_shape(fn, state, ctx) -> None:
    scores = fn(state, ctx)
    assert isinstance(scores, np.ndarray)
    assert scores.shape == ctx["bitrates_kbps"].shape
    assert np.isfinite(scores).any()


def unit_test_seed_functions() -> None:
    ctx = {
        "bitrates_kbps": np.array([300, 750, 1200, 1850, 2850, 4300], dtype=float),
        "chunk_len_s": 4.0,
        "smooth_penalty": 1.0,
        "rebuf_penalty": 4.3,
        "buffer_max_s": 60.0,
        "link_rtt_s": 0.08,
    }
    state = {
        "buffer_s": 12.0,
        "last_bitrate_idx": 1,
        "throughput_hist_mbps": np.array([2.0, 1.8, 2.2, 1.9, 2.1, 1.7], dtype=float),
        "next_chunk_sizes_bytes": np.array([400000, 800000, 1200000, 1800000, 2800000, 4200000], dtype=float),
        "future_chunk_sizes_bytes": np.array(
            [
                [400000, 800000, 1200000, 1800000, 2800000, 4200000],
                [390000, 790000, 1190000, 1790000, 2790000, 4190000],
                [410000, 810000, 1210000, 1810000, 2810000, 4210000],
            ],
            dtype=float,
        ),
        "chunk_remain": 40,
        "rebuffer_sec": 0.0,
    }

    _assert_scores_shape(score_bb, state, ctx)
    _assert_scores_shape(score_bola, state, ctx)
    _assert_scores_shape(score_quetra, state, ctx)
    _assert_scores_shape(score_robust_mpc, state, ctx)
    _assert_scores_shape(score_rate_based, state, ctx)


def integration_test_seed_population(max_traces: int = 3) -> None:
    problem = ABRProblem(max_traces=max_traces, trace_split="test", dataset="FCC-18")
    seeds = problem.prompts.get_seed_heuristics()

    for seed in seeds:
        fitness = problem.evaluate(seed["code"])
        assert fitness is not None and math.isfinite(float(fitness))
        print(f"{seed['algorithm']} -> objective={fitness:.5f}")


if __name__ == "__main__":
    unit_test_seed_functions()
    integration_test_seed_population()
    print("OK")

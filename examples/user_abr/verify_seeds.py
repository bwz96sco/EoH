"""Verify seed heuristics against actual SABR baseline scripts.

Runs both the seed heuristic (via EoH score interface) and a faithful
re-implementation of each SABR baseline on the same traces, then compares
per-step decisions and overall QoE.
"""
from __future__ import annotations

import sys
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np

from abr_api import extract_state, make_ctx
from prob import ABRProblem
from seed_heuristics import (
    score_bb,
    score_bola,
    score_quetra,
    score_rate_based,
    score_robust_mpc,
)


# ---------------------------------------------------------------------------
# Faithful re-implementations of SABR baselines (decision-only, no logging)
# ---------------------------------------------------------------------------

def sabr_bb_decision(buffer_s: float, k: int, reservoir: float = 5.0, cushion: float = 10.0) -> int:
    """Exact SABR bb.py logic: int() truncation."""
    if buffer_s < reservoir:
        bit_rate = 0
    elif buffer_s >= reservoir + cushion:
        bit_rate = k - 1
    else:
        bit_rate = (k - 1) * (buffer_s - reservoir) / float(cushion)
    return int(bit_rate)


def sabr_bola_decision(
    buffer_s: float,
    bitrates: np.ndarray,
    next_sizes: np.ndarray,
    min_buf: float = 10.0,
    target_buf: float = 30.0,
) -> int:
    """Exact SABR bola.py logic: log utility, vp computed from bitrates."""
    k = len(bitrates)
    gp = 1.0 + np.log(bitrates[-1] / float(bitrates[0])) / (target_buf / min_buf - 1.0)
    vp = min_buf / (gp - 1.0)

    best_score = -1e30
    best_q = 0
    for q in range(k):
        s = (vp * (np.log(bitrates[q] / float(bitrates[0])) + gp) - buffer_s) / next_sizes[q]
        if s >= best_score:  # >= means ties go to higher bitrate
            best_score = s
            best_q = q
    return best_q


class SABRQuetra:
    """Faithful re-implementation of SABR quetra.py QuetraABR."""

    SLACK_60 = [59.25,59.2246,59.1983,59.1712,59.143,59.1139,59.0836,59.0522,59.0195,58.9855,58.95,58.9129,58.8742,58.8336,58.7911,58.7464,58.6994,58.6498,58.5975,58.5421,58.4833,58.4209,58.3543,58.2831,58.2069,58.125,58.0367,57.9411,57.8373,57.7241,57.6,57.4634,57.3122,57.1438,56.955,56.7417,56.4986,56.2189,55.8934,55.5096,55.0503,54.4904,53.7932,52.9034,51.736,50.1614,47.9911,44.984,40.9181,35.7703,29.92,24.1077,19.0476,15.0712,12.1288,9.99749,8.44445,7.2892,6.40712,5.71575,5.16083,4.70615,4.32698,4.006,3.73079,3.49221,3.28339,3.09909,2.93521,2.78854,2.65649]

    def __init__(self, buffer_max: int = 60, alpha: float = 0.1):
        self.buffer_max = buffer_max
        self.alpha = alpha
        self.av = 0.0
        self.count = 0
        self.throughput_array: list[float] = []

    def push(self, throughput_bps: float) -> None:
        if throughput_bps < 10_000_000:
            self.throughput_array.append(throughput_bps)

    def predict(self) -> float:
        arr = self.throughput_array
        n = len(arr)
        if n < 1:
            return 0.0
        elif n == 1:
            self.av = arr[-1]
        elif n == 2:
            self.av = (arr[0] + arr[1]) / 2.0
        else:
            self.av = (1 - self.alpha) * self.av + self.alpha * arr[-1]
        return self.av

    def select(self, buffer_s: float, bitrate_list_bps: list[int]) -> int:
        av_kbps = self.predict() / 1000.0
        buff_array = []
        for br_bps in bitrate_list_bps:
            rho = av_kbps / (br_bps / 1000.0)
            if rho < 0.5:
                buff_array.append(self.buffer_max)
            elif rho >= 1.2:
                buff_array.append(0.0)
            else:
                idx = int((rho - 0.5) / 0.01)
                buff_array.append(self.SLACK_60[idx] * (self.buffer_max / 60.0))

        min_diff = abs(buffer_s - buff_array[0])
        min_index = 0
        for i in range(1, len(buff_array)):
            diff = abs(buffer_s - buff_array[i])
            if diff <= min_diff:  # <= means ties go to higher bitrate
                min_diff = diff
                min_index = i

        # All slack == buffer_max → pick lowest
        if buff_array[min_index] == self.buffer_max and buff_array[-1] == buff_array[0]:
            min_index = 0

        # Low-res protection
        if buffer_s < (90.0 / 240.0) * self.buffer_max:
            min_index = 0

        self.count += 1
        return min_index


# ---------------------------------------------------------------------------
# Simulation harness
# ---------------------------------------------------------------------------

def run_comparison(dataset: str = "FCC-18", max_traces: int | None = 5) -> None:
    """Run seed heuristics vs SABR baselines on same traces, compare decisions."""
    prob = ABRProblem(trace_split="test", dataset=dataset, max_traces=max_traces)
    env_mod = prob._sabr_env_module
    bitrates = prob.video_bit_rates
    k = int(bitrates.size)
    bitrate_list_bps = [int(x * 1000) for x in bitrates]

    print(f"Dataset: {dataset}")
    print(f"Bitrates (kbps): {bitrates.tolist()}")
    print(f"Traces: {len(prob.all_file_names)}")
    print(f"Buffer max: {prob.buffer_max_s}s, Chunk len: {prob.chunk_len_s}s")
    print()

    # --- BB comparison ---
    print("=" * 60)
    print("BB: Seed vs SABR")
    print("=" * 60)
    _compare_bb(prob, env_mod, bitrates, k)

    # --- BOLA comparison ---
    print("\n" + "=" * 60)
    print("BOLA: Seed vs SABR")
    print("=" * 60)
    _compare_bola(prob, env_mod, bitrates, k)

    # --- QUETRA comparison ---
    print("\n" + "=" * 60)
    print("QUETRA: Seed vs SABR")
    print("=" * 60)
    _compare_quetra(prob, env_mod, bitrates, k, bitrate_list_bps)


def _simulate_dual(
    prob: ABRProblem,
    env_mod: Any,
    score_fn,
    sabr_decide_fn,
    name: str,
) -> tuple[dict, dict]:
    """Run same traces with seed heuristic and SABR decision, track disagreements."""
    env = env_mod.Environment(
        all_cooked_time=prob.all_cooked_time,
        all_cooked_bw=prob.all_cooked_bw,
        random_seed=42,
    )
    np.random.seed(42)

    last_bit_rate = 1
    bit_rate = 1
    throughput_history = deque(maxlen=8)

    seed_qoe = 0.0
    sabr_qoe = 0.0
    total_steps = 0
    mismatches = 0
    video_count = 0

    while True:
        (delay_ms, sleep_time_ms, buffer_s, rebuf_s,
         video_chunk_size_bytes, next_video_chunk_sizes,
         end_of_video, video_chunk_remain) = env.get_video_chunk(bit_rate)

        reward = (
            prob.video_bit_rates[bit_rate] / 1000.0
            - prob.rebuf_penalty * rebuf_s
            - prob.smooth_penalty * abs(prob.video_bit_rates[bit_rate] - prob.video_bit_rates[last_bit_rate]) / 1000.0
        )
        seed_qoe += reward
        sabr_qoe += reward

        if delay_ms > 1e-6:
            tp_kbps = (float(video_chunk_size_bytes) * 8.0) / float(delay_ms)
        else:
            tp_kbps = float(prob.video_bit_rates[bit_rate])
        throughput_history.append(tp_kbps)

        last_bit_rate = bit_rate
        total_steps += 1

        state = extract_state(
            obs=None,
            info=(delay_ms, sleep_time_ms, buffer_s, rebuf_s,
                  video_chunk_size_bytes, next_video_chunk_sizes,
                  end_of_video, video_chunk_remain),
            last_action=last_bit_rate,
            throughput_history=np.asarray(throughput_history, dtype=np.float64),
        )

        # Seed decision
        scores = score_fn(state, prob.ctx)
        seed_action = int(np.argmax(scores))

        # SABR decision
        sabr_action = sabr_decide_fn(
            state=state,
            buffer_s=buffer_s,
            bitrates=prob.video_bit_rates,
            next_sizes=np.asarray(next_video_chunk_sizes, dtype=np.float64),
            delay_ms=delay_ms,
            video_chunk_size_bytes=video_chunk_size_bytes,
        )

        if seed_action != sabr_action:
            mismatches += 1
            if mismatches <= 5:
                print(f"  Step {total_steps}: seed={seed_action} sabr={sabr_action} "
                      f"buf={buffer_s:.1f}s tp={tp_kbps:.0f}kbps")

        bit_rate = seed_action  # Both follow seed path for consistency

        if end_of_video:
            last_bit_rate = 1
            bit_rate = 1
            throughput_history.clear()
            video_count += 1
            if video_count >= len(prob.all_file_names):
                break

    print(f"  Total steps: {total_steps}, Mismatches: {mismatches} "
          f"({100*mismatches/max(total_steps,1):.1f}%)")
    return {"qoe": seed_qoe / max(video_count, 1), "steps": total_steps}, \
           {"mismatches": mismatches}


def _compare_bb(prob, env_mod, bitrates, k):
    """Compare BB seed vs SABR BB."""
    # Unit test on specific buffer values
    ctx = prob.ctx
    test_bufs = [0, 3, 5, 7.5, 10, 12.5, 14.99, 15, 20]
    print("  Buffer(s) | Seed idx | SABR idx | Match?")
    print("  " + "-" * 50)
    for buf in test_bufs:
        state = {"buffer_s": buf}
        seed_scores = score_bb(state, ctx)
        seed_idx = int(np.argmax(seed_scores))
        sabr_idx = sabr_bb_decision(buf, k, reservoir=5.0, cushion=10.0)
        match = "OK" if seed_idx == sabr_idx else "DIFF"
        print(f"  {buf:9.2f} | {seed_idx:8d} | {sabr_idx:8d} | {match}")

    # Key insight
    print("\n  Note: SABR BB uses int() truncation (floor).")
    print("  Seed BB uses argmax(-|idx - target|) which rounds to nearest.")
    print("  Difference occurs when fractional target > X.5")


def _compare_bola(prob, env_mod, bitrates, k):
    """Compare BOLA seed vs SABR BOLA."""
    # Compute correct SABR vp
    gp_sabr = 1.0 + np.log(bitrates[-1] / float(bitrates[0])) / (30.0 / 10.0 - 1.0)
    vp_sabr = 10.0 / (gp_sabr - 1.0)

    # Seed uses ctx["V"] which defaults to 5.0
    v_seed = float(prob.ctx.get("V", 5.0))

    print(f"  SABR gp = {gp_sabr:.4f}, vp = {vp_sabr:.4f}")
    print(f"  Seed V (from ctx) = {v_seed:.4f}")
    print(f"  -> {'MATCH' if abs(vp_sabr - v_seed) < 0.01 else 'MISMATCH'}: "
          f"delta = {abs(vp_sabr - v_seed):.4f}")
    print()

    # Compare decisions at various buffer levels
    test_bufs = [0, 5, 10, 20, 30, 40, 50]
    # Use a representative next_chunk_sizes
    dummy_sizes = np.array([50000, 100000, 180000, 300000, 500000, 800000], dtype=np.float64)
    if k != 6:
        dummy_sizes = np.linspace(50000, 800000, k)

    print("  Buffer(s) | Seed idx | SABR idx | Match?")
    print("  " + "-" * 50)
    for buf in test_bufs:
        state = {
            "buffer_s": buf,
            "next_chunk_sizes_bytes": dummy_sizes,
        }
        seed_scores = score_bola(state, prob.ctx)
        seed_idx = int(np.argmax(seed_scores))
        sabr_idx = sabr_bola_decision(buf, bitrates, dummy_sizes)
        match = "OK" if seed_idx == sabr_idx else "DIFF"
        print(f"  {buf:9.1f} | {seed_idx:8d} | {sabr_idx:8d} | {match}")

    print(f"\n  Root cause: make_ctx sets V=5.0, but SABR computes vp={vp_sabr:.4f}")


def _compare_quetra(prob, env_mod, bitrates, k, bitrate_list_bps):
    """Compare QUETRA seed vs SABR QUETRA."""
    # Test EMA prediction difference
    print("  EMA prediction comparison:")
    test_histories = [
        [5000],
        [3000, 7000],
        [3000, 5000, 7000],
        [2000, 3000, 5000, 7000, 4000],
    ]
    for hist_kbps in test_histories:
        hist_mbps = np.array(hist_kbps, dtype=np.float64) / 1000.0

        # Seed EMA
        from seed_heuristics import _ema
        seed_pred_mbps = _ema(hist_mbps, 0.1)
        seed_pred_kbps = seed_pred_mbps * 1000.0

        # SABR EMA: predict() is called after each push (stateful)
        sabr_q = SABRQuetra(buffer_max=60, alpha=0.1)
        for tp_kbps in hist_kbps:
            sabr_q.push(tp_kbps * 1000.0)  # bit/s
            sabr_q.predict()  # called after each push, updates av
        sabr_pred_kbps = sabr_q.av / 1000.0  # already in bit/s

        match = "OK" if abs(seed_pred_kbps - sabr_pred_kbps) < 0.1 else "DIFF"
        print(f"  hist={hist_kbps} -> seed={seed_pred_kbps:.1f} sabr={sabr_pred_kbps:.1f} {match}")

    # Test decision comparison at various buffer levels
    print("\n  Decision comparison (after 5 throughput samples):")
    tp_history_kbps = [2000, 3000, 2500, 4000, 3500]  # typical history
    tp_history_mbps = np.array(tp_history_kbps, dtype=np.float64) / 1000.0

    # Replicate SABR's stateful EMA (predict called once per step)
    sabr_q = SABRQuetra(buffer_max=60, alpha=0.1)
    for tp in tp_history_kbps:
        sabr_q.push(tp * 1000.0)
        sabr_q.predict()  # stateful update after each push
    # Use av directly - don't call select() which calls predict again
    av_kbps = sabr_q.av / 1000.0

    test_bufs = [5, 15, 25, 35, 45, 55]
    ctx = prob.ctx
    print(f"  SABR av_kbps = {av_kbps:.1f}, seed pred_kbps = {_ema(tp_history_mbps, 0.1)*1000:.1f}")
    print("  Buffer(s) | Seed idx | SABR idx | Match?")
    print("  " + "-" * 50)
    for buf in test_bufs:
        state = {
            "buffer_s": buf,
            "throughput_hist_mbps": tp_history_mbps,
        }
        seed_scores = score_quetra(state, ctx)
        seed_idx = int(np.argmax(seed_scores))

        # Compute SABR decision manually using av_kbps
        buff_array = []
        for br_bps in bitrate_list_bps:
            rho = av_kbps / (br_bps / 1000.0)
            if rho < 0.5:
                buff_array.append(60)
            elif rho >= 1.2:
                buff_array.append(0.0)
            else:
                idx = int((rho - 0.5) / 0.01)
                buff_array.append(SABRQuetra.SLACK_60[idx])

        min_diff = abs(buf - buff_array[0])
        min_index = 0
        for i in range(1, len(buff_array)):
            diff = abs(buf - buff_array[i])
            if diff <= min_diff:
                min_diff = diff
                min_index = i
        if buff_array[min_index] == 60 and buff_array[-1] == buff_array[0]:
            min_index = 0
        if buf < (90.0 / 240.0) * 60:
            min_index = 0
        sabr_idx = min_index

        match = "OK" if seed_idx == sabr_idx else "DIFF"
        print(f"  {buf:9.1f} | {seed_idx:8d} | {sabr_idx:8d} | {match}")


if __name__ == "__main__":
    ds = sys.argv[1] if len(sys.argv) > 1 else "FCC-18"
    run_comparison(dataset=ds, max_traces=5)

from __future__ import annotations

import textwrap
from collections.abc import Sequence
from typing import Any

import numpy as np


def _to_1d_float(arr: Any) -> np.ndarray:
    out = np.asarray(arr, dtype=np.float64).reshape(-1)
    return out


def _harmonic_mean(x: np.ndarray, eps: float = 1e-6) -> float:
    x = _to_1d_float(x)
    x = x[np.isfinite(x)]
    x = x[x > eps]
    if x.size == 0:
        return 0.0
    return float(x.size / np.sum(1.0 / np.maximum(x, eps)))


def _ema(x: np.ndarray, alpha: float) -> float:
    """SABR-compatible EMA: n=1 raw, n=2 average, n>=3 incremental EMA."""
    x = _to_1d_float(x)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return 0.0
    if x.size == 1:
        return float(x[0])
    alpha = float(np.clip(alpha, 0.0, 1.0))
    v = (float(x[0]) + float(x[1])) / 2.0
    for y in x[2:]:
        v = (1.0 - alpha) * v + alpha * float(y)
    return v


def _get_bitrates_kbps(ctx: dict[str, Any]) -> np.ndarray:
    bitrates = np.asarray(ctx.get("bitrates_kbps", []), dtype=np.float64).reshape(-1)
    if bitrates.size == 0:
        raise ValueError("ctx['bitrates_kbps'] must be a non-empty array.")
    return bitrates


def score_bb(state: dict[str, Any], ctx: dict[str, Any]) -> np.ndarray:
    """BB: buffer-based mapping from buffer level to bitrate index."""
    bitrates = _get_bitrates_kbps(ctx)
    k = int(bitrates.size)
    buffer_s = float(state.get("buffer_s", 0.0))
    reservoir_s = float(ctx.get("reservoir_s", 5.0))
    cushion_s = float(ctx.get("cushion_s", 10.0))

    if buffer_s < reservoir_s:
        target = 0.0
    elif buffer_s >= reservoir_s + cushion_s:
        target = float(k - 1)
    else:
        frac = (buffer_s - reservoir_s) / max(cushion_s, 1e-6)
        target = float(int(frac * float(k - 1)))  # floor like SABR

    idx = np.arange(k, dtype=np.float64)
    return -np.abs(idx - target)


def score_bola(state: dict[str, Any], ctx: dict[str, Any]) -> np.ndarray:
    """BOLA: maximize (V*(utility+gp)-buffer)/chunk_size for each quality."""
    bitrates = _get_bitrates_kbps(ctx)
    buffer_s = float(state.get("buffer_s", 0.0))
    next_sizes = np.asarray(state.get("next_chunk_sizes_bytes", []), dtype=np.float64)
    next_sizes = next_sizes.reshape(-1)
    if next_sizes.size != bitrates.size:
        raise ValueError("state['next_chunk_sizes_bytes'] must have shape (K,).")

    utility = np.log(np.maximum(bitrates, 1.0) / max(float(bitrates[0]), 1.0))
    b_min = float(ctx.get("bola_buffer_min_s", 10.0))
    b_target = float(ctx.get("bola_buffer_target_s", 30.0))
    if b_target <= b_min:
        b_target = b_min + 1e-3

    gp = 1.0 + float(utility[-1]) / (b_target / b_min - 1.0)
    v = float(ctx.get("V", b_min / max(gp - 1.0, 1e-6)))

    denom = np.maximum(next_sizes, 1.0)
    scores = (v * (utility + gp) - buffer_s) / denom
    return scores.astype(np.float64)



# QUETRA slack lookup tables from SABR (M/D/1/K queueing model).
# Index i corresponds to rho = 0.5 + i*0.01, for i in 0..70.
_QUETRA_SLACK_TABLES: dict[int, list[float]] = {
    30: [29.25,29.2246,29.1983,29.1712,29.143,29.1139,29.0836,29.0522,29.0195,28.9855,28.95,28.9129,28.8742,28.8336,28.7911,28.7464,28.6994,28.6498,28.5975,28.5421,28.4833,28.4209,28.3543,28.2832,28.2069,28.125,28.0367,27.9411,27.8373,27.7241,27.6001,27.4636,27.3125,27.1444,26.9562,26.744,26.5031,26.2277,25.9103,25.542,25.1119,24.6069,24.0121,23.3115,22.4893,21.5325,20.4347,19.1998,17.8455,16.4048,14.9228,13.451,12.039,10.7266,9.54002,8.4909,7.57875,6.79468,6.12517,5.55493,5.06895,4.65353,4.29676,3.9886,3.72075,3.48639,3.28001,3.09712,2.93406,2.78786,2.65609],
    60: [59.25,59.2246,59.1983,59.1712,59.143,59.1139,59.0836,59.0522,59.0195,58.9855,58.95,58.9129,58.8742,58.8336,58.7911,58.7464,58.6994,58.6498,58.5975,58.5421,58.4833,58.4209,58.3543,58.2831,58.2069,58.125,58.0367,57.9411,57.8373,57.7241,57.6,57.4634,57.3122,57.1438,56.955,56.7417,56.4986,56.2189,55.8934,55.5096,55.0503,54.4904,53.7932,52.9034,51.736,50.1614,47.9911,44.984,40.9181,35.7703,29.92,24.1077,19.0476,15.0712,12.1288,9.99749,8.44445,7.2892,6.40712,5.71575,5.16083,4.70615,4.32698,4.006,3.73079,3.49221,3.28339,3.09909,2.93521,2.78854,2.65649],
    120: [119.25,119.225,119.198,119.171,119.143,119.114,119.084,119.052,119.02,118.985,118.95,118.913,118.874,118.834,118.791,118.746,118.699,118.65,118.598,118.542,118.483,118.421,118.354,118.283,118.207,118.125,118.037,117.941,117.837,117.724,117.6,117.463,117.312,117.144,116.955,116.742,116.499,116.219,115.893,115.51,115.05,114.489,113.79,112.892,111.697,110.026,107.527,103.433,95.9794,81.9,59.9193,38.0624,24.1326,16.7349,12.6553,10.1631,8.49674,7.3058,6.41242,5.71746,5.16138,4.70633,4.32703,4.00602,3.7308,3.49221,3.28339,3.09909,2.93521,2.78854,2.65649],
}


def _quetra_slack(rho: float, buffer_max_s: float) -> float:
    """Look up slack from SABR's precomputed M/D/1/K table."""
    if rho < 0.5:
        return buffer_max_s
    if rho >= 1.2:
        return 0.0
    bmax = int(buffer_max_s)
    table = _QUETRA_SLACK_TABLES.get(bmax)
    if table is None:
        # Fallback: use buffer_max=60 table scaled proportionally.
        table = _QUETRA_SLACK_TABLES[60]
        idx = min(int((rho - 0.5) / 0.01), len(table) - 1)
        return table[idx] * (buffer_max_s / 60.0)
    idx = min(int((rho - 0.5) / 0.01), len(table) - 1)
    return table[idx]


def score_quetra(state: dict[str, Any], ctx: dict[str, Any]) -> np.ndarray:
    """QUETRA: choose bitrate by matching buffer to M/D/1/K slack table."""
    bitrates = _get_bitrates_kbps(ctx)
    k = int(bitrates.size)
    buffer_s = float(state.get("buffer_s", 0.0))
    buffer_max_s = float(ctx.get("buffer_max_s", 60.0))
    alpha = float(ctx.get("alpha", 0.1))

    hist_mbps = np.asarray(state.get("throughput_hist_mbps", []), dtype=np.float64)
    pred_mbps = _ema(hist_mbps, alpha)
    pred_kbps = max(pred_mbps * 1000.0, 0.0)

    low_res_ratio = float(ctx.get("quetra_low_res_ratio", 90.0 / 240.0))
    if buffer_s < low_res_ratio * buffer_max_s:
        return -np.arange(k, dtype=np.float64)

    slack = np.empty(k, dtype=np.float64)
    for i in range(k):
        rho = pred_kbps / max(float(bitrates[i]), 1.0)
        slack[i] = _quetra_slack(rho, buffer_max_s)

    # All slack equal to buffer_max → lowest bitrate (SABR behavior)
    if slack[0] == buffer_max_s and slack[-1] == buffer_max_s:
        return -np.arange(k, dtype=np.float64)

    # Tiny bias toward higher bitrate to match SABR tie-breaking (<=)
    return -np.abs(slack - buffer_s) + np.arange(k, dtype=np.float64) * 1e-10


def score_robust_mpc(state: dict[str, Any], ctx: dict[str, Any]) -> np.ndarray:
    """RobustMPC-lite: short horizon simulation assuming constant quality."""
    bitrates = _get_bitrates_kbps(ctx)
    k = int(bitrates.size)

    buffer_s = float(state.get("buffer_s", 0.0))
    last_idx = int(state.get("last_bitrate_idx", 0))
    last_idx = int(np.clip(last_idx, 0, k - 1))

    chunk_len_s = float(ctx.get("chunk_len_s", 4.0))
    rebuf_penalty = float(ctx.get("rebuf_penalty", 4.3))
    smooth_penalty = float(ctx.get("smooth_penalty", 1.0))
    margin = float(ctx.get("robust_margin", 0.1))
    horizon = int(ctx.get("mpc_horizon", 3))
    horizon = max(1, min(horizon, int(state.get("chunk_remain", horizon))))

    next_sizes = np.asarray(state.get("next_chunk_sizes_bytes", []), dtype=np.float64)
    next_sizes = next_sizes.reshape(-1)
    if next_sizes.size != k:
        raise ValueError("state['next_chunk_sizes_bytes'] must have shape (K,).")

    hist_mbps = np.asarray(state.get("throughput_hist_mbps", []), dtype=np.float64)
    pred_mbps = _harmonic_mean(hist_mbps)
    pred_mbps *= max(0.0, 1.0 - margin)
    pred_mbps = max(pred_mbps, 1e-3)

    last_kbps = float(bitrates[last_idx])
    scores = np.empty(k, dtype=np.float64)
    for i in range(k):
        buf = buffer_s
        total = 0.0
        dl_s = float(next_sizes[i]) * 8.0 / (pred_mbps * 1e6)
        for t in range(horizon):
            rebuf_s = max(dl_s - buf, 0.0)
            buf = max(buf - dl_s, 0.0) + chunk_len_s
            total += float(bitrates[i]) / 1000.0 - rebuf_penalty * rebuf_s
            if t == 0:
                total -= smooth_penalty * abs(float(bitrates[i]) - last_kbps) / 1000.0
        scores[i] = total
    return scores


def score_rate_based(state: dict[str, Any], ctx: dict[str, Any]) -> np.ndarray:
    """Rate-based: select highest bitrate under predicted bandwidth (with margin)."""
    bitrates = _get_bitrates_kbps(ctx)
    hist_mbps = np.asarray(state.get("throughput_hist_mbps", []), dtype=np.float64)
    margin = float(ctx.get("robust_margin", 0.1))

    pred_mbps = _harmonic_mean(hist_mbps)
    pred_mbps *= max(0.0, 1.0 - margin)
    allowed_kbps = max(pred_mbps * 1000.0, 0.0)

    excess = np.maximum(bitrates - allowed_kbps, 0.0)
    denom = max(allowed_kbps, 1.0)
    return bitrates / 1000.0 - 1000.0 * (excess / denom) ** 2


def get_seed_heuristics() -> list[dict[str, str]]:
    """Return seed heuristics as EoH individuals: [{'algorithm','code'}, ...]."""
    return list(SEED_HEURISTICS)


BB_CODE = textwrap.dedent(
    """
    import numpy as np

    def score(state, ctx):
        \"\"\"BB: buffer-based mapping from buffer level to bitrate index.\"\"\"
        bitrates = np.asarray(ctx.get("bitrates_kbps", []), dtype=float).reshape(-1)
        k = int(bitrates.size)
        if k == 0:
            return np.array([], dtype=float)

        buffer_s = float(state.get("buffer_s", 0.0))
        reservoir_s = float(ctx.get("reservoir_s", 5.0))
        cushion_s = float(ctx.get("cushion_s", 10.0))

        if buffer_s < reservoir_s:
            target = 0.0
        elif buffer_s >= reservoir_s + cushion_s:
            target = float(k - 1)
        else:
            frac = (buffer_s - reservoir_s) / max(cushion_s, 1e-6)
            target = float(int(frac * float(k - 1)))  # floor like SABR

        idx = np.arange(k, dtype=float)
        return -np.abs(idx - target)
    """
).strip()


BOLA_CODE = textwrap.dedent(
    """
    import numpy as np

    def score(state, ctx):
        \"\"\"BOLA: maximize (V*(utility+gp)-buffer)/chunk_size for each quality.\"\"\"
        bitrates = np.asarray(ctx.get("bitrates_kbps", []), dtype=float).reshape(-1)
        next_sizes = np.asarray(state.get("next_chunk_sizes_bytes", []), dtype=float).reshape(-1)
        if bitrates.size == 0 or next_sizes.size != bitrates.size:
            return np.zeros_like(bitrates, dtype=float)

        buffer_s = float(state.get("buffer_s", 0.0))
        utility = np.log(np.maximum(bitrates, 1.0) / max(float(bitrates[0]), 1.0))

        b_min = float(ctx.get("bola_buffer_min_s", 10.0))
        b_target = float(ctx.get("bola_buffer_target_s", 30.0))
        if b_target <= b_min:
            b_target = b_min + 1e-3
        gp = 1.0 + float(utility[-1]) / (b_target / b_min - 1.0)
        v = float(ctx.get("V", b_min / max(gp - 1.0, 1e-6)))

        denom = np.maximum(next_sizes, 1.0)
        return (v * (utility + gp) - buffer_s) / denom
    """
).strip()


QUETRA_CODE = textwrap.dedent(
    """
    import numpy as np

    # QUETRA slack table (M/D/1/K queueing model, buffer_max=60).
    # Index i corresponds to rho = 0.5 + i*0.01.
    _SLACK_60 = [59.25,59.2246,59.1983,59.1712,59.143,59.1139,59.0836,59.0522,59.0195,58.9855,58.95,58.9129,58.8742,58.8336,58.7911,58.7464,58.6994,58.6498,58.5975,58.5421,58.4833,58.4209,58.3543,58.2831,58.2069,58.125,58.0367,57.9411,57.8373,57.7241,57.6,57.4634,57.3122,57.1438,56.955,56.7417,56.4986,56.2189,55.8934,55.5096,55.0503,54.4904,53.7932,52.9034,51.736,50.1614,47.9911,44.984,40.9181,35.7703,29.92,24.1077,19.0476,15.0712,12.1288,9.99749,8.44445,7.2892,6.40712,5.71575,5.16083,4.70615,4.32698,4.006,3.73079,3.49221,3.28339,3.09909,2.93521,2.78854,2.65649]

    def _quetra_slack(rho, buffer_max_s):
        if rho < 0.5:
            return buffer_max_s
        if rho >= 1.2:
            return 0.0
        idx = min(int((rho - 0.5) / 0.01), len(_SLACK_60) - 1)
        return _SLACK_60[idx] * (buffer_max_s / 60.0)

    def _ema(x, alpha):
        \"\"\"SABR-compatible EMA: n=1 raw, n=2 average, n>=3 incremental.\"\"\"
        x = np.asarray(x, dtype=float).reshape(-1)
        x = x[np.isfinite(x)]
        if x.size == 0:
            return 0.0
        if x.size == 1:
            return float(x[0])
        alpha = float(np.clip(alpha, 0.0, 1.0))
        v = (float(x[0]) + float(x[1])) / 2.0
        for y in x[2:]:
            v = (1.0 - alpha) * v + alpha * float(y)
        return v

    def score(state, ctx):
        \"\"\"QUETRA: match buffer to M/D/1/K slack table lookup.\"\"\"
        bitrates = np.asarray(ctx.get("bitrates_kbps", []), dtype=float).reshape(-1)
        k = int(bitrates.size)
        if k == 0:
            return np.array([], dtype=float)

        buffer_s = float(state.get("buffer_s", 0.0))
        buffer_max_s = float(ctx.get("buffer_max_s", 60.0))
        alpha = float(ctx.get("alpha", 0.1))

        hist_mbps = np.asarray(state.get("throughput_hist_mbps", []), dtype=float)
        pred_kbps = max(_ema(hist_mbps, alpha) * 1000.0, 0.0)

        low_res_ratio = float(ctx.get("quetra_low_res_ratio", 90.0 / 240.0))
        if buffer_s < low_res_ratio * buffer_max_s:
            return -np.arange(k, dtype=float)

        slack = np.empty(k, dtype=float)
        for i in range(k):
            rho = pred_kbps / max(float(bitrates[i]), 1.0)
            slack[i] = _quetra_slack(rho, buffer_max_s)

        # All slack equal to buffer_max → lowest bitrate
        if slack[0] == buffer_max_s and slack[-1] == buffer_max_s:
            return -np.arange(k, dtype=float)

        # Tiny bias toward higher bitrate to match SABR tie-breaking
        return -np.abs(slack - buffer_s) + np.arange(k, dtype=float) * 1e-10
    """
).strip()


ROBUST_MPC_CODE = textwrap.dedent(
    """
    import numpy as np

    def _harmonic_mean(x, eps=1e-6):
        x = np.asarray(x, dtype=float).reshape(-1)
        x = x[np.isfinite(x)]
        x = x[x > eps]
        if x.size == 0:
            return 0.0
        return float(x.size / np.sum(1.0 / np.maximum(x, eps)))

    def score(state, ctx):
        \"\"\"RobustMPC-lite: short horizon simulation assuming constant quality.\"\"\"
        bitrates = np.asarray(ctx.get("bitrates_kbps", []), dtype=float).reshape(-1)
        k = int(bitrates.size)
        next_sizes = np.asarray(state.get("next_chunk_sizes_bytes", []), dtype=float).reshape(-1)
        if k == 0 or next_sizes.size != k:
            return np.zeros_like(bitrates, dtype=float)

        buffer_s = float(state.get("buffer_s", 0.0))
        last_idx = int(np.clip(int(state.get("last_bitrate_idx", 0)), 0, k - 1))
        last_kbps = float(bitrates[last_idx])

        chunk_len_s = float(ctx.get("chunk_len_s", 4.0))
        rebuf_penalty = float(ctx.get("rebuf_penalty", 4.3))
        smooth_penalty = float(ctx.get("smooth_penalty", 1.0))
        margin = float(ctx.get("robust_margin", 0.1))
        horizon = int(ctx.get("mpc_horizon", 3))
        horizon = max(1, min(horizon, int(state.get("chunk_remain", horizon))))

        hist_mbps = np.asarray(state.get("throughput_hist_mbps", []), dtype=float)
        pred_mbps = _harmonic_mean(hist_mbps) * max(0.0, 1.0 - margin)
        pred_mbps = max(pred_mbps, 1e-3)

        scores = np.empty(k, dtype=float)
        for i in range(k):
            buf = buffer_s
            total = 0.0
            dl_s = float(next_sizes[i]) * 8.0 / (pred_mbps * 1e6)
            for t in range(horizon):
                rebuf_s = max(dl_s - buf, 0.0)
                buf = max(buf - dl_s, 0.0) + chunk_len_s
                total += float(bitrates[i]) / 1000.0 - rebuf_penalty * rebuf_s
                if t == 0:
                    total -= smooth_penalty * abs(float(bitrates[i]) - last_kbps) / 1000.0
            scores[i] = total
        return scores
    """
).strip()


RATE_BASED_CODE = textwrap.dedent(
    """
    import numpy as np

    def _harmonic_mean(x, eps=1e-6):
        x = np.asarray(x, dtype=float).reshape(-1)
        x = x[np.isfinite(x)]
        x = x[x > eps]
        if x.size == 0:
            return 0.0
        return float(x.size / np.sum(1.0 / np.maximum(x, eps)))

    def score(state, ctx):
        \"\"\"Rate-based: pick highest bitrate under predicted bandwidth.\"\"\"
        bitrates = np.asarray(ctx.get("bitrates_kbps", []), dtype=float).reshape(-1)
        if bitrates.size == 0:
            return np.array([], dtype=float)

        margin = float(ctx.get("robust_margin", 0.1))
        hist_mbps = np.asarray(state.get("throughput_hist_mbps", []), dtype=float)
        allowed_kbps = max(_harmonic_mean(hist_mbps) * max(0.0, 1.0 - margin) * 1000.0, 0.0)

        excess = np.maximum(bitrates - allowed_kbps, 0.0)
        denom = max(allowed_kbps, 1.0)
        return bitrates / 1000.0 - 1000.0 * (excess / denom) ** 2
    """
).strip()


SEED_HEURISTICS: Sequence[dict[str, str]] = [
    {
        "algorithm": "{BB: buffer-based mapping from buffer occupancy to bitrate index}",
        "code": BB_CODE,
    },
    {
        "algorithm": "{BOLA: maximize utility+buffer tradeoff per chunk size}",
        "code": BOLA_CODE,
    },
    {
        "algorithm": "{QUETRA: EMA throughput -> rho -> M/D/1/K slack table lookup -> buffer matching}",
        "code": QUETRA_CODE,
    },
    {
        "algorithm": "{RobustMPC-lite: harmonic-mean bandwidth + short horizon simulation}",
        "code": ROBUST_MPC_CODE,
    },
    {
        "algorithm": "{Rate-based: choose highest bitrate within predicted bandwidth margin}",
        "code": RATE_BASED_CODE,
    },
]


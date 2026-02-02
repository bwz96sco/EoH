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
    x = _to_1d_float(x)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return 0.0
    alpha = float(np.clip(alpha, 0.0, 1.0))
    v = float(x[0])
    for y in x[1:]:
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
        target = frac * float(k - 1)

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


def score_quetra(state: dict[str, Any], ctx: dict[str, Any]) -> np.ndarray:
    """QUETRA-style: choose bitrate by matching buffer to slack derived from rho."""
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

    rho = pred_kbps / np.maximum(bitrates, 1.0)

    slack = np.empty(k, dtype=np.float64)
    slack[rho < 0.5] = buffer_max_s
    slack[rho >= 1.2] = 0.0

    mid = (rho >= 0.5) & (rho < 1.2)
    slack[mid] = buffer_max_s * (1.0 - (rho[mid] - 0.5) / (1.2 - 0.5))

    return -np.abs(slack - buffer_s)


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
            target = frac * float(k - 1)

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

    def _ema(x, alpha):
        x = np.asarray(x, dtype=float).reshape(-1)
        x = x[np.isfinite(x)]
        if x.size == 0:
            return 0.0
        alpha = float(np.clip(alpha, 0.0, 1.0))
        v = float(x[0])
        for y in x[1:]:
            v = (1.0 - alpha) * v + alpha * float(y)
        return v

    def score(state, ctx):
        \"\"\"QUETRA-style: match buffer to slack derived from rho.\"\"\"
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

        rho = pred_kbps / np.maximum(bitrates, 1.0)
        slack = np.empty(k, dtype=float)
        slack[rho < 0.5] = buffer_max_s
        slack[rho >= 1.2] = 0.0
        mid = (rho >= 0.5) & (rho < 1.2)
        slack[mid] = buffer_max_s * (1.0 - (rho[mid] - 0.5) / (1.2 - 0.5))
        return -np.abs(slack - buffer_s)
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
        "algorithm": "{QUETRA: EMA throughput -> rho -> target slack buffer matching}",
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


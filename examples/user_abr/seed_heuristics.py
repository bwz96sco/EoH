from __future__ import annotations

import textwrap
import types
from collections.abc import Sequence


BB_CODE = textwrap.dedent(
    """
    import numpy as np

    def score(state, ctx):
        \"\"\"BB: buffer-based mapping from buffer level to bitrate index.\"\"\"
        bitrates = np.asarray(ctx.get("bitrates_kbps", []), dtype=float).reshape(-1)
        k = int(bitrates.size)
        if k == 0:
            return np.array([], dtype=float)

        reservoir_s = 5.0
        cushion_s = 10.0
        buffer_s = float(state.get("buffer_s", 0.0))

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

        buffer_min_s = 10.0
        buffer_target_s = 30.0
        buffer_s = float(state.get("buffer_s", 0.0))
        utility = np.log(np.maximum(bitrates, 1.0) / max(float(bitrates[0]), 1.0))

        gp = 1.0 + float(utility[-1]) / (buffer_target_s / buffer_min_s - 1.0)
        v = buffer_min_s / max(gp - 1.0, 1e-6)

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

        alpha = 0.1
        low_res_ratio = 90.0 / 240.0
        buffer_s = float(state.get("buffer_s", 0.0))
        buffer_max_s = float(ctx.get("buffer_max_s", 60.0))

        hist_mbps = np.asarray(state.get("throughput_hist_mbps", []), dtype=float)
        pred_kbps = max(_ema(hist_mbps, alpha) * 1000.0, 0.0)

        if buffer_s < low_res_ratio * buffer_max_s:
            return -np.arange(k, dtype=float)

        slack = np.empty(k, dtype=float)
        for i in range(k):
            rho = pred_kbps / max(float(bitrates[i]), 1.0)
            slack[i] = _quetra_slack(rho, buffer_max_s)

        # All slack equal to buffer_max -> lowest bitrate
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

        margin = 0.1
        horizon = 3
        buffer_s = float(state.get("buffer_s", 0.0))
        last_idx = int(np.clip(int(state.get("last_bitrate_idx", 0)), 0, k - 1))
        last_kbps = float(bitrates[last_idx])

        chunk_len_s = float(ctx.get("chunk_len_s", 4.0))
        rebuf_penalty = float(ctx.get("rebuf_penalty", 4.3))
        smooth_penalty = float(ctx.get("smooth_penalty", 1.0))
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

        margin = 0.1
        hist_mbps = np.asarray(state.get("throughput_hist_mbps", []), dtype=float)
        allowed_kbps = max(_harmonic_mean(hist_mbps) * max(0.0, 1.0 - margin) * 1000.0, 0.0)

        excess = np.maximum(bitrates - allowed_kbps, 0.0)
        denom = max(allowed_kbps, 1.0)
        return bitrates / 1000.0 - 1000.0 * (excess / denom) ** 2
    """
).strip()


def _load_seed_module(name: str, code: str) -> types.ModuleType:
    module = types.ModuleType(name)
    exec(code, module.__dict__)
    return module


_BB_MODULE = _load_seed_module("eoh_seed_bb", BB_CODE)
_BOLA_MODULE = _load_seed_module("eoh_seed_bola", BOLA_CODE)
_QUETRA_MODULE = _load_seed_module("eoh_seed_quetra", QUETRA_CODE)
_ROBUST_MPC_MODULE = _load_seed_module("eoh_seed_robust_mpc", ROBUST_MPC_CODE)
_RATE_BASED_MODULE = _load_seed_module("eoh_seed_rate_based", RATE_BASED_CODE)

# Export executable helpers from the exact same code text written to seeds.json.
score_bb = _BB_MODULE.score
score_bola = _BOLA_MODULE.score
score_quetra = _QUETRA_MODULE.score
score_robust_mpc = _ROBUST_MPC_MODULE.score
score_rate_based = _RATE_BASED_MODULE.score
_ema = _QUETRA_MODULE._ema


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


def get_seed_heuristics() -> list[dict[str, str]]:
    """Return seed heuristics as EoH individuals: [{'algorithm','code'}, ...]."""
    return list(SEED_HEURISTICS)

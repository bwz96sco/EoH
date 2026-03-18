from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


def extract_state(
    obs: Any,
    info: Any,
    last_action: int,
    throughput_history: Sequence[float] | np.ndarray,
    *,
    future_chunk_sizes_bytes: Sequence[Sequence[float]] | np.ndarray | None = None,
) -> dict[str, Any]:
    """Convert SABR env outputs to an LLM-friendly state dict.

    This helper supports both:
    - SABR `fixed_env.Environment.get_video_chunk()` return tuple, and
    - dict-like `info` with equivalent keys.

    Args:
        obs: Reserved for Gym-like env compatibility (unused for SABR fixed_env).
        info: Either a dict or the 8-tuple returned by `get_video_chunk()`.
        last_action: Previous bitrate index (0-based).
        throughput_history: Recent throughput measurements in **Kbps**.
        future_chunk_sizes_bytes: Optional matrix of future chunk sizes in bytes
            with shape `(H, K)`, where `H` is the planning horizon and `K` is the
            number of bitrate actions. If omitted, the state falls back to a
            single-step matrix built from `next_chunk_sizes_bytes`.
    """

    if isinstance(info, Mapping):
        buffer_s = float(info.get("buffer_s", info.get("buffer_sec", 0.0)))
        rebuffer_sec = float(info.get("rebuffer_sec", info.get("rebuf", 0.0)))
        next_chunk_sizes_bytes = np.asarray(
            info.get("next_chunk_sizes_bytes", info.get("next_chunk_sizes", [])),
            dtype=np.float64,
        )
        chunk_remain = int(info.get("chunk_remain", 0))
    else:
        try:
            (
                _delay_ms,
                _sleep_time_ms,
                buffer_s,
                rebuffer_sec,
                _video_chunk_size_bytes,
                next_video_chunk_sizes,
                _end_of_video,
                chunk_remain,
            ) = info
        except Exception as exc:  # pragma: no cover
            raise ValueError(
                "Unsupported SABR info format; expected mapping or 8-tuple."
            ) from exc
        next_chunk_sizes_bytes = np.asarray(next_video_chunk_sizes, dtype=np.float64)

    throughput_hist_kbps = np.asarray(throughput_history, dtype=np.float64)
    throughput_hist_mbps = throughput_hist_kbps / 1000.0

    if future_chunk_sizes_bytes is None:
        if next_chunk_sizes_bytes.size == 0:
            future_chunk_sizes = np.empty((0, 0), dtype=np.float64)
        else:
            future_chunk_sizes = next_chunk_sizes_bytes.reshape(1, -1)
    else:
        future_chunk_sizes = np.asarray(future_chunk_sizes_bytes, dtype=np.float64)
        if future_chunk_sizes.ndim == 1:
            if future_chunk_sizes.size == 0:
                future_chunk_sizes = np.empty((0, 0), dtype=np.float64)
            else:
                future_chunk_sizes = future_chunk_sizes.reshape(1, -1)

    return {
        "buffer_s": float(buffer_s),
        "last_bitrate_idx": int(last_action),
        "throughput_hist_mbps": throughput_hist_mbps,
        "next_chunk_sizes_bytes": next_chunk_sizes_bytes,
        "future_chunk_sizes_bytes": future_chunk_sizes,
        "chunk_remain": int(chunk_remain),
        "rebuffer_sec": float(rebuffer_sec),
    }


def extract_future_chunk_sizes(
    env: Any,
    video_chunk_remain: int,
    *,
    horizon: int = 5,
) -> np.ndarray:
    """Build a `(H, K)` chunk-size matrix for upcoming chunks from SABR env state."""

    plan_horizon = int(max(0, min(horizon, int(video_chunk_remain))))
    if plan_horizon <= 0:
        return np.empty((0, 0), dtype=np.float64)

    video_size = getattr(env, "video_size", None)
    chunk_idx = int(getattr(env, "video_chunk_counter", 0))
    if video_size is None:
        return np.empty((0, 0), dtype=np.float64)

    bitrate_levels = len(video_size)
    future_sizes = np.empty((plan_horizon, bitrate_levels), dtype=np.float64)
    for position in range(plan_horizon):
        future_chunk_idx = chunk_idx + position
        for quality in range(bitrate_levels):
            future_sizes[position, quality] = float(video_size[quality][future_chunk_idx])

    return future_sizes


def make_ctx(config: Any, env: Any | None = None, **overrides: Any) -> dict[str, Any]:
    """Build a context dict holding evaluator-owned environment constants."""

    def _get_attr(name: str, default: Any) -> Any:
        if hasattr(config, name):
            return getattr(config, name)
        if isinstance(config, Mapping) and name in config:
            return config[name]
        return default

    bitrates_kbps = np.asarray(_get_attr("VIDEO_BIT_RATE", []), dtype=np.float64)
    rebuf_penalty = float(_get_attr("REBUF_PENALTY", 4.3))

    chunk_len_s = float(overrides.pop("chunk_len_s", 4.0))
    buffer_max_s = float(overrides.pop("buffer_max_s", 60.0))
    link_rtt_s = float(overrides.pop("link_rtt_s", 0.08))
    if env is not None:
        if hasattr(env, "VIDEO_CHUNCK_LEN"):
            chunk_len_s = float(env.VIDEO_CHUNCK_LEN) / 1000.0
        if hasattr(env, "BUFFER_THRESH"):
            buffer_max_s = float(env.BUFFER_THRESH) / 1000.0
        if hasattr(env, "LINK_RTT"):
            link_rtt_s = float(env.LINK_RTT) / 1000.0

    ctx: dict[str, Any] = {
        "bitrates_kbps": bitrates_kbps,
        "chunk_len_s": float(chunk_len_s),
        "smooth_penalty": float(overrides.pop("smooth_penalty", 1.0)),
        "rebuf_penalty": float(overrides.pop("rebuf_penalty", rebuf_penalty)),
        "buffer_max_s": float(buffer_max_s),
        "link_rtt_s": float(link_rtt_s),
    }
    if overrides:
        unexpected = ", ".join(sorted(overrides))
        raise ValueError(
            f"Unexpected ABR ctx overrides: {unexpected}. "
            "Keep heuristic-specific knobs in the heuristic code."
        )
    return ctx

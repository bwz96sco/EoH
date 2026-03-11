from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


def extract_state(
    obs: Any,
    info: Any,
    last_action: int,
    throughput_history: Sequence[float] | np.ndarray,
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

    return {
        "buffer_s": float(buffer_s),
        "last_bitrate_idx": int(last_action),
        "throughput_hist_mbps": throughput_hist_mbps,
        "next_chunk_sizes_bytes": next_chunk_sizes_bytes,
        "chunk_remain": int(chunk_remain),
        "rebuffer_sec": float(rebuffer_sec),
    }


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
    if env is not None:
        if hasattr(env, "VIDEO_CHUNCK_LEN"):
            chunk_len_s = float(env.VIDEO_CHUNCK_LEN) / 1000.0
        if hasattr(env, "BUFFER_THRESH"):
            buffer_max_s = float(env.BUFFER_THRESH) / 1000.0

    ctx: dict[str, Any] = {
        "bitrates_kbps": bitrates_kbps,
        "chunk_len_s": float(chunk_len_s),
        "smooth_penalty": float(overrides.pop("smooth_penalty", 1.0)),
        "rebuf_penalty": float(overrides.pop("rebuf_penalty", rebuf_penalty)),
        "buffer_max_s": float(buffer_max_s),
    }
    if overrides:
        unexpected = ", ".join(sorted(overrides))
        raise ValueError(
            f"Unexpected ABR ctx overrides: {unexpected}. "
            "Keep heuristic-specific knobs in the heuristic code."
        )
    return ctx

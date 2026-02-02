from __future__ import annotations

from typing import Any


def diagnose_failure_mode(metrics: dict[str, Any]) -> str:
    mean_rebuffer = float(metrics.get("mean_rebuffer_s", 0.0))
    mean_bitrate = float(metrics.get("mean_bitrate_kbps", 0.0))
    mean_switch = float(metrics.get("mean_switch_kbps", 0.0))

    if mean_rebuffer > 0.5:
        return "Excessive rebuffering; be more conservative or add safety margin."
    if mean_bitrate < 0.35 * float(metrics.get("max_bitrate_kbps", mean_bitrate + 1.0)):
        return "Too conservative; increase bitrate when buffer is safe."
    if mean_switch > 1200.0:
        return "High switching; add hysteresis/smoothing to stabilize quality."
    return "No obvious single failure mode; tune tradeoffs (buffer vs bitrate vs switching)."


def format_feedback(metrics: dict[str, Any]) -> str:
    """Format evaluation metrics into a short feedback block for mutation prompts."""
    issue = diagnose_failure_mode(metrics)
    return (
        "Evaluation summary:\n"
        f"- Mean QoE: {float(metrics.get('mean_qoe', 0.0)):.3f}\n"
        f"- Mean rebuffer: {float(metrics.get('mean_rebuffer_s', 0.0)):.3f}s\n"
        f"- Mean bitrate: {float(metrics.get('mean_bitrate_kbps', 0.0)):.1f} kbps\n"
        f"- Mean switch magnitude: {float(metrics.get('mean_switch_kbps', 0.0)):.1f} kbps\n"
        f"- Issue: {issue}\n"
    )


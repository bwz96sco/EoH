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
    lines = [
        "Evaluation summary:",
        f"- Mean QoE: {float(metrics.get('mean_qoe', 0.0)):.3f}",
        f"- Mean rebuffer: {float(metrics.get('mean_rebuffer_s', 0.0)):.3f}s",
        f"- Mean bitrate: {float(metrics.get('mean_bitrate_kbps', 0.0)):.1f} kbps",
        f"- Mean switch magnitude: {float(metrics.get('mean_switch_kbps', 0.0)):.1f} kbps",
    ]
    if "utilization_mean" in metrics:
        lines.append(
            f"- Mean utilization: {float(metrics['utilization_mean']):.3f}"
        )
    if "utilization_penalty" in metrics:
        lines.append(
            f"- Utilization penalty: {float(metrics['utilization_penalty']):.3f}"
        )
    fitness_mode = metrics.get("fitness_mode")
    if fitness_mode and fitness_mode != "mean":
        lines.append(f"- Fitness mode: {fitness_mode}")
    lines.append(f"- Issue: {issue}")
    return "\n".join(lines) + "\n"


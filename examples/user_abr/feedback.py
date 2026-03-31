from __future__ import annotations

import json
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


def _extract_behavior(metrics: dict[str, Any]) -> dict[str, float]:
    """Extract the 4D behavior vector from metrics, returning empty dict if missing."""
    keys = [
        "behavior_utilization",
        "behavior_rebuffer_rate",
        "behavior_switch_rate",
        "behavior_min_bitrate_frac",
    ]
    behavior = {}
    for k in keys:
        if k in metrics:
            behavior[k] = float(metrics[k])
    return behavior


def format_feedback(metrics: dict[str, Any]) -> str:
    """Format evaluation metrics into a short feedback block for mutation prompts.

    If behavioral descriptors are present in *metrics*, they are appended both as
    human-readable lines (for the LLM) and as a machine-parseable JSON trailer
    (for ``eoh_interface_EC`` to extract without fragile regex).
    """
    issue = diagnose_failure_mode(metrics)
    lines = [
        "Evaluation summary:",
        f"- Mean QoE: {float(metrics.get('mean_qoe', 0.0)):.3f}",
        f"- Mean rebuffer: {float(metrics.get('mean_rebuffer_s', 0.0)):.3f}s",
        f"- Mean bitrate: {float(metrics.get('mean_bitrate_kbps', 0.0)):.1f} kbps",
        f"- Mean switch magnitude: {float(metrics.get('mean_switch_kbps', 0.0)):.1f} kbps",
        f"- Issue: {issue}",
    ]

    behavior = _extract_behavior(metrics)
    if behavior:
        lines.append(
            f"- Bandwidth utilization: {behavior.get('behavior_utilization', 0.0):.3f}"
        )
        lines.append(
            f"- Rebuffer rate: {behavior.get('behavior_rebuffer_rate', 0.0):.3f}"
        )
        lines.append(
            f"- Switch rate: {behavior.get('behavior_switch_rate', 0.0):.3f}"
        )
        lines.append(
            f"- Min-bitrate fraction: {behavior.get('behavior_min_bitrate_frac', 0.0):.3f}"
        )
        # Machine-readable JSON trailer for behavior extraction
        lines.append(f"__BEHAVIOR_JSON__:{json.dumps(behavior)}")

    return "\n".join(lines) + "\n"


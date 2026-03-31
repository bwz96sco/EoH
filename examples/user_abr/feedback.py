from __future__ import annotations

from typing import Any


def diagnose_failure_mode(metrics: dict[str, Any]) -> str:
    """Diagnose the dominant failure mode using adaptive thresholds."""
    mean_rebuffer = float(metrics.get("mean_rebuffer_s", 0.0))
    mean_bitrate = float(metrics.get("mean_bitrate_kbps", 0.0))
    mean_switch = float(metrics.get("mean_switch_kbps", 0.0))
    max_bitrate = float(metrics.get("max_bitrate_kbps", mean_bitrate + 1.0))
    rebuf_penalty = float(metrics.get("rebuf_penalty", 4.3))

    # Adaptive rebuffer threshold: 0.1 * rebuf_penalty (e.g., 0.43s for 3G, 4.0s for 4G+)
    rebuf_threshold = 0.1 * rebuf_penalty

    # Adaptive bitrate conservatism threshold scales with rebuf_penalty:
    # Higher rebuf_penalty justifies more conservative bitrate, so lower the bar.
    # 3G (rebuf_penalty=4.3): threshold ~0.25; 4G+ (rebuf_penalty=40): threshold ~0.15
    bitrate_threshold_ratio = max(0.15, 0.35 - 0.02 * rebuf_penalty)

    # Utilization-based diagnosis
    utilization = float(metrics.get("mean_utilization", 0.0))

    issues: list[str] = []

    if mean_rebuffer > rebuf_threshold:
        issues.append("Excessive rebuffering; be more conservative or add safety margin.")
    if mean_bitrate < bitrate_threshold_ratio * max_bitrate:
        issues.append("Too conservative; increase bitrate when buffer is safe.")
    if utilization < 0.2:
        issues.append("Severely under-utilizing available bandwidth.")
    elif utilization < 0.4:
        issues.append("Moderately conservative bandwidth utilization.")
    if mean_switch > 1200.0:
        issues.append("High switching; add hysteresis/smoothing to stabilize quality.")

    if not issues:
        return "No obvious single failure mode; tune tradeoffs (buffer vs bitrate vs switching)."
    return " ".join(issues)


def _format_qoe_breakdown(metrics: dict[str, Any]) -> str:
    """Format per-chunk QoE component breakdown."""
    breakdown = metrics.get("qoe_breakdown")
    if not isinstance(breakdown, dict):
        return ""
    br = float(breakdown.get("bitrate_component", 0.0))
    rb = float(breakdown.get("rebuffer_component", 0.0))
    sw = float(breakdown.get("switch_component", 0.0))
    total_loss = rb + sw
    parts: list[str] = []
    if total_loss > 0:
        parts.append(f"rebuf {rb / total_loss * 100:.0f}%")
        parts.append(f"switch {sw / total_loss * 100:.0f}%")
        return f"- QoE breakdown (per-chunk avg): +{br:.3f} bitrate, -{rb:.3f} rebuf, -{sw:.3f} switch (loss share: {', '.join(parts)})\n"
    return f"- QoE breakdown (per-chunk avg): +{br:.3f} bitrate, -{rb:.3f} rebuf, -{sw:.3f} switch\n"


def format_feedback(metrics: dict[str, Any]) -> str:
    """Format evaluation metrics into a short feedback block for mutation prompts."""
    issue = diagnose_failure_mode(metrics)

    lines = [
        "Evaluation summary:",
        f"- Mean QoE: {float(metrics.get('mean_qoe', 0.0)):.3f}",
        f"- Mean rebuffer: {float(metrics.get('mean_rebuffer_s', 0.0)):.3f}s",
        f"- Mean bitrate: {float(metrics.get('mean_bitrate_kbps', 0.0)):.1f} kbps",
        f"- Mean switch: {float(metrics.get('mean_switch_kbps', 0.0)):.1f} kbps",
    ]

    # Utilization
    utilization = metrics.get("mean_utilization")
    if utilization is not None:
        lines.append(f"- Utilization: {float(utilization):.1%}")

    # Distribution info
    qoe_std = metrics.get("qoe_std")
    qoe_worst = metrics.get("qoe_worst_10pct")
    qoe_best = metrics.get("qoe_best_10pct")
    if qoe_std is not None:
        lines.append(f"- QoE std: {float(qoe_std):.2f}, worst-10%: {float(qoe_worst or 0):.2f}, best-10%: {float(qoe_best or 0):.2f}")

    # QoE breakdown
    breakdown_str = _format_qoe_breakdown(metrics)
    if breakdown_str:
        lines.append(breakdown_str.rstrip("\n"))

    lines.append(f"- Issue: {issue}")

    return "\n".join(lines) + "\n"


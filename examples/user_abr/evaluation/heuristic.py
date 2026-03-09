# Replace this with your evolved heuristic from EoH output.
import numpy as np


def score(state, ctx):
    """Placeholder: buffer-based fallback."""
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

"""Generate a synthetic e1-shaped long prompt for the grok2api probe.

Run once (or rerun if EoH's prompt template changes materially) to refresh
`experiments/grok2api_probe_sample_prompt.txt`. The generated prompt mimics
an ABR-style e1 prompt with 5 fake parent algorithms padded to ~13-15k chars
so the probe exercises grok2api with a payload comparable to real EoH e1
calls.

Usage:
  uv run python experiments/_build_grok2api_probe_sample_prompt.py
"""

from __future__ import annotations

from pathlib import Path

OUTPUT = Path(__file__).with_name("grok2api_probe_sample_prompt.txt")

TASK = (
    "Evolve a scoring heuristic score(state, ctx) for an adaptive bitrate "
    "controller evaluated on ABRBench-3G traces. The heuristic receives the "
    "current player state (buffer occupancy in seconds, last chosen bitrate "
    "index, recent throughput history, next chunk size estimates, future "
    "chunk size estimates, chunks remaining, rebuffer seconds) and a context "
    "dict (available bitrates in kbps, chunk length, smooth penalty, rebuf "
    "penalty, buffer max, link RTT). It must return a numpy array of per-"
    "bitrate scores the controller will argmax over at each step to select "
    "the next chunk quality. The objective is to maximize mean QoE across "
    "the ABRBench-3G training traces under the plain average aggregation."
)

INOUT_INF = (
    "All inputs are numpy arrays or floats; the returned scores array must "
    "have the same shape as ctx['bitrates_kbps'] and contain at least one "
    "finite value. Do not mutate state or ctx. Do not import anything outside "
    "numpy. Do not call into external services. The scoring function must be "
    "deterministic given its inputs."
)

OTHER_INF = (
    "Keep the implementation concise but readable. Prefer vectorized numpy "
    "operations over Python loops when it does not harm clarity. Avoid very "
    "aggressive floating point tricks that would break on reasonable inputs."
)

FAKE_PARENT_TEMPLATE_ALGO = (
    "{{Algorithm {idx}: {name}. Combine the throughput forecast "
    "(harmonic mean of the last {hist} throughput samples) with a "
    "quadratic buffer-occupancy preference centered on target_buffer={target} "
    "seconds and a smoothness bonus that penalizes switching away from "
    "last_bitrate_idx by more than one step. Add a small rebuffer-risk term "
    "derived from next_chunk_sizes_bytes divided by the throughput forecast "
    "so low-buffer states avoid bitrates whose download time would likely "
    "drain the buffer below link_rtt_s. Blend the three terms with weights "
    "{w1:.2f}, {w2:.2f}, and {w3:.2f} before returning a score vector in the "
    "same shape as ctx['bitrates_kbps'].}}"
)

FAKE_PARENT_TEMPLATE_CODE = """\
import numpy as np

def score(state, ctx):
    bitrates = ctx['bitrates_kbps']
    chunk_len = ctx['chunk_len_s']
    rtt = ctx['link_rtt_s']
    smooth_penalty = ctx['smooth_penalty']
    rebuf_penalty = ctx['rebuf_penalty']
    buffer_max = ctx['buffer_max_s']

    buffer_s = state['buffer_s']
    last_idx = state['last_bitrate_idx']
    hist = state['throughput_hist_mbps']
    next_sizes = state['next_chunk_sizes_bytes']

    if hist.size == 0:
        forecast_mbps = 1.0
    else:
        tail = hist[-{hist}:]
        tail = np.clip(tail, 1e-3, None)
        forecast_mbps = len(tail) / np.sum(1.0 / tail)

    download_time_s = (next_sizes * 8.0 / 1_000_000.0) / max(forecast_mbps, 1e-3)
    rebuf_risk = np.maximum(0.0, download_time_s - max(buffer_s - rtt, 0.0))

    target = {target}
    buffer_pref = -((buffer_s - target) ** 2) * {w2:.6f}

    idx_axis = np.arange(bitrates.shape[0], dtype=float)
    smooth_bonus = -np.abs(idx_axis - last_idx) * smooth_penalty * {w3:.6f}

    throughput_pref = np.log1p(np.maximum(0.0, forecast_mbps - bitrates / 1000.0)) * {w1:.6f}

    score_vec = throughput_pref + buffer_pref + smooth_bonus - rebuf_penalty * rebuf_risk
    score_vec = np.where(np.isfinite(score_vec), score_vec, -np.inf)
    if not np.isfinite(score_vec).any():
        score_vec = np.zeros_like(bitrates, dtype=float)
    return score_vec
"""


def build_prompt(n_parents: int = 5, pad_marker: str = "# probe padding") -> str:
    parents_block: list[str] = []
    for i in range(1, n_parents + 1):
        algo = FAKE_PARENT_TEMPLATE_ALGO.format(
            idx=i,
            name=f"synthetic_ABR_heuristic_v{i}",
            hist=2 + i,
            target=8 + 2 * i,
            w1=0.7 + 0.05 * i,
            w2=0.5 + 0.1 * i,
            w3=0.3 + 0.05 * i,
        )
        code = FAKE_PARENT_TEMPLATE_CODE.format(
            hist=2 + i,
            target=8 + 2 * i,
            w1=0.7 + 0.05 * i,
            w2=0.5 + 0.1 * i,
            w3=0.3 + 0.05 * i,
        )
        parents_block.append(
            f"No.{i} algorithm and the corresponding code are: \n{algo}\n{code}\n"
        )

    prompt_body = (
        TASK
        + "\n"
        + f"I have {n_parents} existing algorithms with their codes as follows: \n"
        + "".join(parents_block)
        + "Please help me create a new algorithm that has a totally different form "
        + "from the given ones. \n"
        + "First, describe your new algorithm and main steps in one sentence. "
        + "The description must be inside a brace. Next, implement it in Python as "
        + "a function named score. This function should accept 2 input(s): 'state', "
        + "'ctx'. The function should return 1 output(s): 'scores'. "
        + INOUT_INF
        + " "
        + OTHER_INF
        + "\nDo not give additional explanations."
    )

    target_chars = 14000
    if len(prompt_body) < target_chars:
        padding_lines = []
        while len(prompt_body) + sum(len(x) + 1 for x in padding_lines) < target_chars:
            padding_lines.append(
                f"{pad_marker}: This is a synthetic probe padding line to grow "
                f"the prompt to a realistic ~14k character e1 payload. It is "
                f"inert filler and may be safely ignored by the model; it does "
                f"not alter the heuristic specification above."
            )
        prompt_body = prompt_body + "\n" + "\n".join(padding_lines)
    return prompt_body


def main() -> None:
    prompt = build_prompt()
    OUTPUT.write_text(prompt)
    print(f"wrote {OUTPUT} ({len(prompt)} chars)")


if __name__ == "__main__":
    main()

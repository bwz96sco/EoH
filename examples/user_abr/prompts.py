from __future__ import annotations

from seed_heuristics import SEED_HEURISTICS


class GetPrompts:
    def __init__(self) -> None:
        self.prompt_task = (
            "Design a heuristic for Adaptive Bitrate (ABR) streaming. "
            "At each video chunk, you must score each bitrate action; the client picks argmax. "
            "QoE is the sum over chunks of: bitrate_kbps/1000 - smooth_penalty*|bitrate_change_kbps|/1000 - rebuf_penalty*rebuffer_seconds. "
            "The goal is to maximize QoE (the evaluator returns negative QoE for minimization)."
        )
        self.prompt_func_name = "score"
        self.prompt_func_inputs = ["state", "ctx"]
        self.prompt_func_outputs = ["scores"]

        self.prompt_inout_inf = (
            "'state' is a dict with:\n"
            "- buffer_s: float\n"
            "- last_bitrate_idx: int (0-based)\n"
            "- throughput_hist_mbps: numpy array of recent throughputs (Mbps), newest last, up to 10 samples\n"
            "- next_chunk_sizes_bytes: numpy array shape (K,) for next chunk sizes by bitrate\n"
            "- future_chunk_sizes_bytes: numpy array shape (H, K) for up to 5 upcoming chunks by bitrate; the first row matches next_chunk_sizes_bytes when available\n"
            "- chunk_remain: int\n"
            "- rebuffer_sec: float (last rebuffer duration)\n"
            "'ctx' is a dict with environment constants only:\n"
            "- bitrates_kbps: numpy array shape (K,)\n"
            "- chunk_len_s: float\n"
            "- smooth_penalty: float (penalty weight for bitrate switching)\n"
            "- rebuf_penalty: float (penalty weight for rebuffering)\n"
            "- buffer_max_s: float\n"
            "- link_rtt_s: float\n"
            "Return 'scores' as a numpy array of shape (K,); higher is better."
        )

        self.prompt_other_inf = (
            "Include the import 'import numpy as np'. "
            "Use deterministic logic without global side effects, and avoid mutating inputs. "
            "Always guard against empty throughput history and non-finite values. "
            "Keep the function fast: O(K) or O(K*H) per step when possible; a small fixed-horizon combinatorial search is acceptable if H stays tiny. "
            "If you plan ahead, only use the chunk-size horizon already provided in 'state'. "
            "If your heuristic needs thresholds, safety margins, smoothing factors, or horizons, define them inside the code as local or module constants. "
            "Do not expect undocumented keys in 'ctx'. "
            "IMPORTANT: For low-bandwidth scenarios (3G networks where bandwidth is similar to max bitrate), "
            "avoid being uniformly conservative. A good heuristic should be ADAPTIVE: "
            "- When buffer is healthy (>30% of max), it's safe to pick higher bitrates even with uncertain bandwidth. "
            "- When buffer is low (<15% of max), be conservative to avoid rebuffering. "
            "- The worst strategy is always picking the lowest bitrate — it wastes bandwidth and scores poorly on easier traces. "
            "- Think of it as a risk-reward tradeoff: the buffer is your safety margin. "
            "This optimization focuses on WORST-CASE trace performance (CVaR), not just average. "
            "A heuristic that performs decently on ALL traces beats one that's great on easy traces but terrible on hard ones."
        )

    def get_task(self) -> str:
        return self.prompt_task

    def get_func_name(self) -> str:
        return self.prompt_func_name

    def get_func_inputs(self) -> list[str]:
        return self.prompt_func_inputs

    def get_func_outputs(self) -> list[str]:
        return self.prompt_func_outputs

    def get_inout_inf(self) -> str:
        return self.prompt_inout_inf

    def get_other_inf(self) -> str:
        return self.prompt_other_inf

    def get_seed_heuristics(self) -> list[dict[str, str]]:
        return list(SEED_HEURISTICS)

class GetPrompts:
    def __init__(self):
        self.prompt_task = (
            "Design a buffer-based bitrate adaptation heuristic for adaptive video streaming. "
            "At the end of each chunk download, the heuristic receives the current playback "
            "state (buffer level, rebuffer duration, metadata of the next chunk, and recent "
            "throughput measurements) and must choose the bitrate index for the next chunk. "
            "The objective is to maximize the QoE defined as bitrate reward minus rebuffering "
            "and smoothness penalties while avoiding stalls."
        )
        self.prompt_func_name = "select_bitrate"
        self.prompt_func_inputs = [
            "buffer_sec",
            "last_quality",
            "rebuffer_sec",
            "chunk_size_bytes",
            "delay_ms",
            "next_chunk_sizes",
            "chunk_remain",
            "video_bit_rates",
            "throughput_history",
            "rebuf_penalty",
            "smooth_penalty",
            "chunk_duration",
        ]
        self.prompt_func_outputs = ["bitrate_index"]
        self.prompt_inout_inf = (
            "'buffer_sec' is the current buffer occupancy in seconds. 'last_quality' is the "
            "previous bitrate index (0-based). 'rebuffer_sec' is the rebuffer duration during "
            "the last download. 'chunk_size_bytes' and 'delay_ms' describe the chunk that just "
            "finished downloading. 'next_chunk_sizes' is a NumPy array with the sizes (bytes) "
            "for the upcoming chunk at each bitrate. 'chunk_remain' is the number of chunks "
            "remaining in the video. 'video_bit_rates' is a NumPy array of nominal bitrate "
            "levels (Kbps). 'throughput_history' is a NumPy array of recent measured throughputs "
            "in Kbps (may be empty on the first chunk). 'rebuf_penalty' and 'smooth_penalty' "
            "are scalar coefficients for QoE, and 'chunk_duration' is the nominal chunk length "
            "in seconds."
        )
        self.prompt_other_inf = (
            "Return an integer index between 0 and len(video_bit_rates)-1. "
            "Use deterministic logic without global side effects, and avoid mutating the inputs. "
            "You may define helper functions. Always guard against empty throughput history and "
            "zero delays. Prefer NumPy operations (assume 'import numpy as np')."
        )

    def get_task(self):
        return self.prompt_task

    def get_func_name(self):
        return self.prompt_func_name

    def get_func_inputs(self):
        return self.prompt_func_inputs

    def get_func_outputs(self):
        return self.prompt_func_outputs

    def get_inout_inf(self):
        return self.prompt_inout_inf

    def get_other_inf(self):
        return self.prompt_other_inf


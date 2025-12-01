"""
Prompts for EoH-based state feature and network architecture evolution for Pensieve ABR.

The LLM designs both:
1. compute_state() - transforms raw observations into a 2D state array
2. build_network() - creates a PyTorch neural network for the A3C agent
"""


class GetPrompts:
    def __init__(self):
        self.prompt_task = (
            "Design a state representation and neural network architecture for an A3C-based "
            "adaptive bitrate (ABR) streaming agent. The agent observes network conditions and "
            "video playback state, then selects a bitrate for the next video chunk. "
            "Your goal is to maximize QoE (Quality of Experience), which rewards high bitrate, "
            "penalizes rebuffering, and penalizes bitrate switches. "
            "You must design: (1) a compute_state function that transforms raw observations into "
            "a 2D numpy array [num_features, history_len] of your chosen dimensions, and "
            "(2) a build_network function that creates a PyTorch nn.Module accepting this state "
            "and outputting action probabilities and state value."
        )

        self.prompt_func_name = "compute_state"

        self.prompt_func_inputs = [
            "buffer_size",
            "delay",
            "video_chunk_size",
            "next_chunk_sizes",
            "video_chunk_remain",
            "last_bit_rate",
            "video_bit_rates",
            "rebuf",
            "history",
        ]

        self.prompt_func_outputs = ["state"]

        self.prompt_inout_inf = (
            "'buffer_size' is the current playback buffer in seconds. "
            "'delay' is the download time of the last chunk in milliseconds. "
            "'video_chunk_size' is the size of the last downloaded chunk in bytes. "
            "'next_chunk_sizes' is a numpy array of size 6 containing the byte sizes of the next chunk at each bitrate level. "
            "'video_chunk_remain' is the number of chunks remaining in the video (max 48). "
            "'last_bit_rate' is the index (0-5) of the previously selected bitrate. "
            "'video_bit_rates' is a numpy array of 6 bitrate levels in Kbps (e.g., [300, 750, 1200, 1850, 2850, 4300]). "
            "'rebuf' is the rebuffering time in seconds that occurred during the last download. "
            "'history' is a dictionary containing historical observations: "
            "  - 'throughput': list of past throughput measurements in Kbps "
            "  - 'delay': list of past delays in ms "
            "  - 'buffer': list of past buffer sizes in seconds "
            "  - 'bitrate': list of past bitrate indices selected "
            "  - 'rebuf': list of past rebuffer durations in seconds "
            "(each list has up to 8 recent entries, oldest first). "
            "The function should return 'state', a 2D numpy array of shape [num_features, history_len] "
            "where num_features and history_len are your design choices. "
            "Values should be normalized (typically 0-1 range) for stable neural network training."
        )

        self.prompt_other_inf = (
            "IMPORTANT: You must also define a 'build_network(state_dim, action_dim)' function in the same code block. "
            "'state_dim' is a tuple (num_features, history_len) matching your compute_state output shape. "
            "'action_dim' is 6 (the number of bitrate levels). "
            "build_network must return a PyTorch nn.Module with a forward(x) method that takes "
            "a batch of states [batch, num_features, history_len] and returns (action_probs, value) where "
            "action_probs has shape [batch, 6] (softmax probabilities) and value has shape [batch, 1]. "
            "You may use Conv1d, Linear, LSTM, attention, or any PyTorch layers. "
            "Use 'import torch' and 'import torch.nn as nn' and 'import torch.nn.functional as F'. "
            "Use 'import numpy as np' for compute_state. "
            "Design creative and effective state features - consider derived metrics like: "
            "throughput estimates, buffer safety margins, bitrate-to-throughput ratios, "
            "download time predictions, trend indicators, etc. "
            "The network architecture should match your state representation - e.g., use Conv1d for temporal patterns, "
            "attention for variable-length history, or simple MLPs for compact states."
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


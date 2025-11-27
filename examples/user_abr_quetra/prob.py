import importlib.util
import sys
import types
import warnings
from collections import deque
from pathlib import Path

import numpy as np

from prompts import GetPrompts


class ABRQuetra:
    DEFAULT_QUALITY = 1
    HISTORY_WINDOW = 8
    EPS = 1e-6
    BUFFER_MAX = 60  # Maximum buffer in seconds (Quetra parameter)
    ALPHA = 0.1  # EMA smoothing factor (Quetra parameter)

    def __init__(self):
        self.prompts = GetPrompts()
        self.random_seed = 42
        self.sabr_root = Path(__file__).resolve().parents[2] / "env" / "SABR"
        (
            self.sabr_config,
            self.sabr_env,
            self.sabr_load_trace,
        ) = self._import_sabr_modules()

        self.video_bit_rates = np.array(
            self.sabr_config.VIDEO_BIT_RATE, dtype=np.float64
        )
        self.rebuf_penalty = float(self.sabr_config.REBUF_PENALTY)
        self.smooth_penalty = 1.0
        self.chunk_duration = float(self.sabr_env.VIDEO_CHUNCK_LEN / 1000.0)

        (
            self.all_cooked_time,
            self.all_cooked_bw,
            self.all_file_names,
        ) = self.sabr_load_trace.load_trace(self.sabr_config.TEST_TRACES)

        if len(self.video_bit_rates) == 0:
            raise ValueError("VIDEO_BIT_RATE from SABR config is empty.")

        self.max_bitrate_idx = len(self.video_bit_rates) - 1

    def _import_sabr_modules(self):
        config_path = self.sabr_root / "config.py"
        env_path = self.sabr_root / "sim_env" / "fixed_env.py"
        load_trace_path = self.sabr_root / "sim_env" / "load_trace.py"

        sabr_config = self._load_module_from_path("eoh_sabr_config", config_path)

        prev_config = sys.modules.get("config")
        sys.modules["config"] = sabr_config
        try:
            sabr_env = self._load_module_from_path("eoh_sabr_fixed_env", env_path)
        finally:
            if prev_config is not None:
                sys.modules["config"] = prev_config
            else:
                sys.modules.pop("config", None)

        sabr_load_trace = self._load_module_from_path(
            "eoh_sabr_load_trace", load_trace_path
        )

        return sabr_config, sabr_env, sabr_load_trace

    @staticmethod
    def _load_module_from_path(name, path):
        if not path.exists():
            raise FileNotFoundError(f"Required SABR module not found: {path}")

        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _sanitize_action(self, value, fallback):
        if isinstance(value, np.ndarray):
            if value.size == 0:
                return fallback
            value = value.flat[0]
        try:
            value = float(value)
        except (TypeError, ValueError):
            return fallback
        if not np.isfinite(value):
            return fallback
        clipped = int(np.clip(value, 0, self.max_bitrate_idx))
        return clipped

    def _simulate(self, alg_module):
        env = self.sabr_env.Environment(
            all_cooked_time=self.all_cooked_time,
            all_cooked_bw=self.all_cooked_bw,
            random_seed=self.random_seed,
        )

        np.random.seed(self.random_seed)

        time_stamp = 0.0
        last_bit_rate = self.DEFAULT_QUALITY
        bit_rate = self.DEFAULT_QUALITY
        throughput_history = deque(maxlen=self.HISTORY_WINDOW)
        rewards = []
        video_count = 0

        while True:
            (
                delay,
                sleep_time,
                buffer_size,
                rebuf,
                video_chunk_size,
                next_video_chunk_sizes,
                end_of_video,
                video_chunk_remain,
            ) = env.get_video_chunk(bit_rate)

            time_stamp += delay
            time_stamp += sleep_time

            reward = (
                self.video_bit_rates[bit_rate] / 1000.0
                - self.rebuf_penalty * rebuf
                - self.smooth_penalty
                * np.abs(
                    self.video_bit_rates[bit_rate]
                    - self.video_bit_rates[last_bit_rate]
                )
                / 1000.0
            )
            rewards.append(reward)

            if delay > self.EPS:
                throughput_kbps = (video_chunk_size * 8.0) / delay
            else:
                throughput_kbps = self.video_bit_rates[bit_rate]
            throughput_history.append(throughput_kbps)

            last_bit_rate = bit_rate

            history_array = np.asarray(throughput_history, dtype=np.float64)
            next_sizes_array = np.asarray(next_video_chunk_sizes, dtype=np.float64)

            try:
                next_bit_rate = alg_module.select_bitrate(
                    buffer_size,
                    last_bit_rate,
                    rebuf,
                    float(video_chunk_size),
                    float(delay),
                    next_sizes_array,
                    int(video_chunk_remain),
                    self.video_bit_rates,
                    history_array,
                    self.rebuf_penalty,
                    self.smooth_penalty,
                    self.chunk_duration,
                    self.BUFFER_MAX,
                    self.ALPHA,
                )
            except Exception:
                return None

            bit_rate = self._sanitize_action(next_bit_rate, last_bit_rate)

            if end_of_video:
                last_bit_rate = self.DEFAULT_QUALITY
                bit_rate = self.DEFAULT_QUALITY
                throughput_history.clear()

                video_count += 1
                if video_count >= len(self.all_file_names):
                    break

        if not rewards:
            return None

        total_reward = np.sum(rewards)
        if not np.isfinite(total_reward):
            return None
        # Return negative reward because EoH uses minimization (lower is better)
        return float(-total_reward)

    def evaluate(self, code_string):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                heuristic_module = types.ModuleType("heuristic_module")
                exec(code_string, heuristic_module.__dict__)
                if not hasattr(heuristic_module, "select_bitrate"):
                    return None
                fitness = self._simulate(heuristic_module)
                if fitness is None or not np.isfinite(fitness):
                    return None
                return float(fitness)
        except Exception:
            return None


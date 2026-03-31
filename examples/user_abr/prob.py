from __future__ import annotations

import importlib.util
import os
import sys
import types
import warnings
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np

from abr_api import extract_future_chunk_sizes, extract_state, make_ctx
from feedback import format_feedback
from prompts import GetPrompts


class ABRProblem:
    DEFAULT_QUALITY = 1
    HISTORY_WINDOW = 10
    MPC_FUTURE_CHUNK_COUNT = 5
    EPS = 1e-6

    VALID_DATASETS = (
        "FCC-16", "FCC-18", "Oboe", "Puffer-21", "Puffer-22", "HSR",
        "Norway3G", "Lumos4G", "Lumos5G", "SolisWi-Fi", "Ghent", "Lab",
        "ABRBench-3G", "ABRBench-4G+",
    )

    VALID_FITNESS_MODES = (
        "mean", "cvar_25", "cvar_10", "mean_std",
        "mean_util", "mean_std_util",
    )

    def __init__(
        self,
        max_traces: int | None = None,
        trace_split: str = "train",
        dataset: str | None = None,
    ) -> None:
        self.prompts = GetPrompts()
        self.random_seed = 42
        self.sabr_root = Path(__file__).resolve().parents[2] / "env" / "SABR"
        self.max_traces = max_traces
        self.trace_split = trace_split

        sabr_config, sabr_env, sabr_load_trace = self._import_sabr_modules()

        # Override dataset if requested (avoids editing SABR config.py manually).
        if dataset is not None:
            if dataset not in self.VALID_DATASETS:
                raise ValueError(
                    f"Unknown dataset '{dataset}'. "
                    f"Valid: {', '.join(self.VALID_DATASETS)}"
                )
            ds = sabr_config._DATASET_OPTION[dataset]
            sabr_config.VIDEO_BIT_RATE = ds["VIDEO_BIT_RATE"]
            sabr_config.REBUF_PENALTY = ds["REBUF_PENALTY"]
            sabr_config.TEST_TRACES = ds["TEST_TRACES"]
            sabr_config.TRAIN_TRACES = ds.get("TRAIN_TRACES", None)
            sabr_config.VIDEO_SIZE_FILE = ds["VIDEO_SIZE_FILE"]
            sabr_config.DATASET_NAME = dataset

        self.video_bit_rates = np.asarray(sabr_config.VIDEO_BIT_RATE, dtype=np.float64)
        if self.video_bit_rates.size == 0:
            raise ValueError("VIDEO_BIT_RATE from SABR config is empty.")

        self.rebuf_penalty = float(sabr_config.REBUF_PENALTY)
        self.smooth_penalty = float(getattr(sabr_env, "SMOOTH_PENALTY", 1.0))
        self.chunk_len_s = float(sabr_env.VIDEO_CHUNCK_LEN) / 1000.0
        self.buffer_max_s = float(sabr_env.BUFFER_THRESH) / 1000.0
        self.total_chunks = int(getattr(sabr_env, "TOTAL_VIDEO_CHUNCK", 48))

        if trace_split == "train":
            trace_path = getattr(sabr_config, "TRAIN_TRACES", None)
            if trace_path is None:
                trace_path = sabr_config.TEST_TRACES
        else:
            trace_path = sabr_config.TEST_TRACES

        all_cooked_time, all_cooked_bw, all_file_names = sabr_load_trace.load_trace(
            trace_path
        )
        if self.max_traces is not None:
            n = int(max(1, min(self.max_traces, len(all_file_names))))
            all_cooked_time = all_cooked_time[:n]
            all_cooked_bw = all_cooked_bw[:n]
            all_file_names = all_file_names[:n]

        self.all_cooked_time = all_cooked_time
        self.all_cooked_bw = all_cooked_bw
        self.all_file_names = all_file_names

        self.max_bitrate_idx = int(self.video_bit_rates.size - 1)
        self.ctx = make_ctx(
            sabr_config,
            env=sabr_env,
            smooth_penalty=self.smooth_penalty,
            rebuf_penalty=self.rebuf_penalty,
            buffer_max_s=self.buffer_max_s,
        )

        self._sabr_env_module = sabr_env

        # --- Fitness mode configuration (env-var driven) ---
        self.fitness_mode = os.environ.get("ABR_FITNESS_MODE", "mean")
        if self.fitness_mode not in self.VALID_FITNESS_MODES:
            raise ValueError(
                f"Unknown ABR_FITNESS_MODE '{self.fitness_mode}'. "
                f"Valid: {', '.join(self.VALID_FITNESS_MODES)}"
            )
        self.util_threshold = float(os.environ.get("ABR_UTIL_THRESHOLD", "0.25"))
        self.util_weight = float(os.environ.get("ABR_UTIL_WEIGHT", "50.0"))
        self.std_weight = float(os.environ.get("ABR_STD_WEIGHT", "0.5"))

    # ------------------------------------------------------------------
    # Fitness aggregation
    # ------------------------------------------------------------------
    def _aggregate_qoe(
        self,
        per_video_qoes: list[float],
        per_video_utilizations: list[float],
    ) -> tuple[float, dict[str, float]]:
        """Aggregate per-video QoE into a single fitness value.

        Returns (fitness, extra_metrics) where fitness is *negated* QoE
        (lower is better, since EoH minimises).
        """
        qoes = np.asarray(per_video_qoes, dtype=np.float64)
        utils = np.asarray(per_video_utilizations, dtype=np.float64)
        mode = self.fitness_mode
        extra: dict[str, float] = {
            "utilization_mean": float(np.mean(utils)) if utils.size > 0 else 0.0,
            "fitness_mode": 0.0,  # placeholder; we store the string in metrics later
        }

        if mode == "mean":
            agg = float(np.mean(qoes))

        elif mode == "cvar_25":
            k = max(1, int(np.ceil(0.25 * len(qoes))))
            agg = float(np.mean(np.sort(qoes)[:k]))

        elif mode == "cvar_10":
            k = max(1, int(np.ceil(0.10 * len(qoes))))
            agg = float(np.mean(np.sort(qoes)[:k]))

        elif mode == "mean_std":
            mean_val = float(np.mean(qoes))
            std_val = float(np.std(qoes))
            agg = mean_val - self.std_weight * std_val

        elif mode == "mean_util":
            base_qoe = float(np.mean(qoes))
            mean_util = float(np.mean(utils)) if utils.size > 0 else 0.0
            util_penalty = max(0.0, self.util_threshold - mean_util) * self.util_weight
            extra["utilization_penalty"] = util_penalty
            agg = base_qoe - util_penalty

        elif mode == "mean_std_util":
            mean_val = float(np.mean(qoes))
            std_val = float(np.std(qoes))
            norm = max(abs(mean_val), 1.0)
            variance_penalty = self.std_weight * (std_val / norm)

            mean_util = float(np.mean(utils)) if utils.size > 0 else 0.0
            util_penalty = max(0.0, self.util_threshold - mean_util) * self.util_weight
            extra["utilization_penalty"] = util_penalty

            agg = mean_val - variance_penalty - util_penalty

        else:
            # Should not happen due to __init__ validation, but be safe.
            agg = float(np.mean(qoes))

        return float(-agg), extra

    def _import_sabr_modules(self) -> tuple[Any, Any, Any]:
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
    def _load_module_from_path(name: str, path: Path) -> Any:
        if not path.exists():
            raise FileNotFoundError(f"Required SABR module not found: {path}")

        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def _sanitize_action(self, value: Any, fallback: int) -> int:
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
        return int(np.clip(int(value), 0, self.max_bitrate_idx))

    def _sanitize_scores(self, scores: Any) -> np.ndarray | None:
        scores_arr = np.asarray(scores, dtype=np.float64).reshape(-1)
        if scores_arr.size != self.video_bit_rates.size:
            return None
        scores_arr = np.nan_to_num(
            scores_arr, nan=-np.inf, posinf=-np.inf, neginf=-np.inf
        )
        if not np.isfinite(scores_arr).any():
            return None
        return scores_arr

    def _build_future_chunk_sizes(
        self,
        env: Any,
        video_chunk_remain: int,
    ) -> np.ndarray:
        return extract_future_chunk_sizes(
            env,
            video_chunk_remain,
            horizon=self.MPC_FUTURE_CHUNK_COUNT,
        )

    def _simulate(self, score_fn) -> tuple[float | None, dict[str, Any] | None]:
        env = self._sabr_env_module.Environment(
            all_cooked_time=self.all_cooked_time,
            all_cooked_bw=self.all_cooked_bw,
            random_seed=self.random_seed,
        )

        np.random.seed(self.random_seed)

        last_bit_rate = self.DEFAULT_QUALITY
        bit_rate = self.DEFAULT_QUALITY
        throughput_history = deque(maxlen=self.HISTORY_WINDOW)

        total_reward = 0.0
        total_rebuf = 0.0
        total_bitrate = 0.0
        total_switch = 0.0
        total_steps = 0

        video_count = 0
        per_video_qoes: list[float] = []
        per_video_utilizations: list[float] = []
        video_reward = 0.0
        video_bitrate_sum = 0.0
        video_steps = 0
        max_bitrate = float(np.max(self.video_bit_rates))

        while True:
            (
                delay_ms,
                sleep_time_ms,
                buffer_s,
                rebuf_s,
                video_chunk_size_bytes,
                next_video_chunk_sizes,
                end_of_video,
                video_chunk_remain,
            ) = env.get_video_chunk(bit_rate)

            reward = (
                self.video_bit_rates[bit_rate] / 1000.0
                - self.rebuf_penalty * rebuf_s
                - self.smooth_penalty
                * abs(self.video_bit_rates[bit_rate] - self.video_bit_rates[last_bit_rate])
                / 1000.0
            )
            if not np.isfinite(reward):
                return None, None

            total_reward += float(reward)
            total_rebuf += float(rebuf_s)
            total_bitrate += float(self.video_bit_rates[bit_rate])
            total_switch += float(
                abs(self.video_bit_rates[bit_rate] - self.video_bit_rates[last_bit_rate])
            )
            total_steps += 1

            # Per-video accumulators
            video_reward += float(reward)
            video_bitrate_sum += float(self.video_bit_rates[bit_rate])
            video_steps += 1

            if delay_ms > self.EPS:
                throughput_kbps = (float(video_chunk_size_bytes) * 8.0) / float(delay_ms)
            else:
                throughput_kbps = float(self.video_bit_rates[bit_rate])
            throughput_history.append(throughput_kbps)

            last_bit_rate = bit_rate
            future_chunk_sizes_bytes = self._build_future_chunk_sizes(
                env,
                video_chunk_remain,
            )

            state = extract_state(
                obs=None,
                info=(
                    delay_ms,
                    sleep_time_ms,
                    buffer_s,
                    rebuf_s,
                    video_chunk_size_bytes,
                    next_video_chunk_sizes,
                    end_of_video,
                    video_chunk_remain,
                ),
                last_action=last_bit_rate,
                throughput_history=np.asarray(throughput_history, dtype=np.float64),
                future_chunk_sizes_bytes=future_chunk_sizes_bytes,
            )

            try:
                scores = self._sanitize_scores(score_fn(state, self.ctx))
            except Exception:
                return None, None

            if scores is None:
                next_bit_rate = last_bit_rate
            else:
                next_bit_rate = int(np.argmax(scores))

            bit_rate = self._sanitize_action(next_bit_rate, last_bit_rate)

            if end_of_video:
                # Record per-video QoE and utilization
                per_video_qoes.append(video_reward)
                if video_steps > 0 and max_bitrate > 0:
                    video_util = video_bitrate_sum / (video_steps * max_bitrate)
                else:
                    video_util = 0.0
                per_video_utilizations.append(video_util)
                video_reward = 0.0
                video_bitrate_sum = 0.0
                video_steps = 0

                last_bit_rate = self.DEFAULT_QUALITY
                bit_rate = self.DEFAULT_QUALITY
                throughput_history.clear()

                video_count += 1
                if video_count >= len(self.all_file_names):
                    break

        if total_steps <= 0 or video_count <= 0:
            return None, None

        fitness, extra = self._aggregate_qoe(per_video_qoes, per_video_utilizations)

        mean_qoe = float(total_reward / video_count)
        metrics: dict[str, Any] = {
            "mean_qoe": mean_qoe,
            "mean_rebuffer_s": float(total_rebuf / total_steps),
            "mean_bitrate_kbps": float(total_bitrate / total_steps),
            "mean_switch_kbps": float(total_switch / total_steps),
            "max_bitrate_kbps": float(np.max(self.video_bit_rates)),
            "utilization_mean": extra["utilization_mean"],
            "fitness_mode": self.fitness_mode,
        }
        if "utilization_penalty" in extra:
            metrics["utilization_penalty"] = extra["utilization_penalty"]
        return fitness, metrics

    def evaluate_with_details(self, code_string: str) -> tuple[float | None, str | None]:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                heuristic_module = types.ModuleType("heuristic_module")
                exec(code_string, heuristic_module.__dict__)
                score_fn = getattr(heuristic_module, "score", None)
                if score_fn is None:
                    return None, None

                fitness, metrics = self._simulate(score_fn)
                if fitness is None or not np.isfinite(fitness) or metrics is None:
                    return None, None

                return float(fitness), format_feedback(metrics)
        except Exception:
            return None, None

    def evaluate(self, code_string: str) -> float | None:
        fitness, _ = self.evaluate_with_details(code_string)
        return fitness

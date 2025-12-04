"""
ABRPensieve problem class for EoH-based state feature and network evolution.

This module evaluates LLM-generated code that defines:
1. compute_state() - transforms raw observations into state features
2. build_network() - creates a PyTorch neural network for the agent
"""

import importlib.util
import sys
import types
import warnings
from collections import deque
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from prompts import GetPrompts


# Training hyperparameters
#MAX_EPOCHS = 110000
MAX_EPOCHS = 10000
TRAIN_SEQ_LEN = 100
ACTOR_LR_RATE = 0.0001
CRITIC_LR_RATE = 0.001
GAMMA = 0.99
ENTROPY_WEIGHT = 0.5
ENTROPY_DECAY_INTERVAL = 10000
ENTROPY_MIN = 0.1

# Environment constants
A_DIM = 6
HISTORY_LEN = 8
M_IN_K = 1000.0
BUFFER_NORM_FACTOR = 10.0
CHUNK_TIL_VIDEO_END_CAP = 48.0
DEFAULT_QUALITY = 1
NORMALIZED_FACTOR = 10.0


class ABRPensieve:
    """
    EoH problem class that evaluates LLM-generated state features and networks.
    
    The evaluation process:
    1. Parse LLM code to extract compute_state() and build_network()
    2. Create environment wrapper with custom state computation
    3. Build neural network using LLM's architecture
    4. Train the agent using A3C for MAX_EPOCHS
    5. Evaluate on test traces and return negative QoE
    """

    def __init__(self):
        self.prompts = GetPrompts()
        self.random_seed = 42
        
        # Get SABR project root
        self.sabr_root = Path(__file__).resolve().parents[2] / "env" / "SABR"
        
        # Import SABR modules
        (
            self.sabr_config,
            self.train_env,
            self.load_trace,
        ) = self._import_sabr_modules()
        
        # Load configuration
        self.video_bit_rates = np.array(self.sabr_config.VIDEO_BIT_RATE, dtype=np.float64)
        self.rebuf_penalty = float(self.sabr_config.REBUF_PENALTY)
        self.smooth_penalty = 1.0
        self.train_traces = self.sabr_config.TRAIN_TRACES
        self.test_traces = self.sabr_config.TEST_TRACES
        
        # Load test traces for evaluation
        (
            self.test_cooked_time,
            self.test_cooked_bw,
            self.test_file_names,
        ) = self.load_trace.load_trace(self.test_traces)
        
    def _import_sabr_modules(self):
        """Dynamically import SABR modules."""
        config_path = self.sabr_root / "config.py"
        train_env_path = self.sabr_root / "sim_env" / "train_env.py"
        load_trace_path = self.sabr_root / "sim_env" / "load_trace.py"
        
        sabr_config = self._load_module_from_path("eoh_sabr_config", config_path)
        
        # Temporarily inject config into sys.modules for train_env import
        prev_config = sys.modules.get("config")
        sys.modules["config"] = sabr_config
        try:
            train_env = self._load_module_from_path("eoh_train_env", train_env_path)
        finally:
            if prev_config is not None:
                sys.modules["config"] = prev_config
            else:
                sys.modules.pop("config", None)
        
        load_trace = self._load_module_from_path("eoh_load_trace", load_trace_path)
        
        return sabr_config, train_env, load_trace

    @staticmethod
    def _load_module_from_path(name, path):
        """Load a Python module from file path."""
        if not path.exists():
            raise FileNotFoundError(f"Required SABR module not found: {path}")
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _create_env_wrapper(self, compute_state_fn):
        """
        Create an environment wrapper that uses the LLM's compute_state function.
        """
        train_env = self.train_env
        video_bit_rates = self.video_bit_rates
        
        # Load training traces
        all_cooked_time, all_cooked_bw, _ = self.load_trace.load_trace(self.train_traces)
        
        class ABREnvWrapper:
            def __init__(wrapper_self, random_seed=42):
                wrapper_self.env = train_env.Environment(
                    all_cooked_time=all_cooked_time,
                    all_cooked_bw=all_cooked_bw,
                    random_seed=random_seed
                )
                wrapper_self.last_bit_rate = DEFAULT_QUALITY
                wrapper_self.history = {
                    'throughput': deque(maxlen=HISTORY_LEN),
                    'delay': deque(maxlen=HISTORY_LEN),
                    'buffer': deque(maxlen=HISTORY_LEN),
                    'bitrate': deque(maxlen=HISTORY_LEN),
                    'rebuf': deque(maxlen=HISTORY_LEN),
                }
                wrapper_self.state_dim = None
                
            def reset(wrapper_self):
                wrapper_self.last_bit_rate = DEFAULT_QUALITY
                wrapper_self.history = {
                    'throughput': deque(maxlen=HISTORY_LEN),
                    'delay': deque(maxlen=HISTORY_LEN),
                    'buffer': deque(maxlen=HISTORY_LEN),
                    'bitrate': deque(maxlen=HISTORY_LEN),
                    'rebuf': deque(maxlen=HISTORY_LEN),
                }
                
                # Get initial observation
                bit_rate = wrapper_self.last_bit_rate
                delay, sleep_time, buffer_size, rebuf, \
                    video_chunk_size, next_chunk_sizes, \
                    end_of_video, video_chunk_remain = wrapper_self.env.get_video_chunk(bit_rate)
                
                # Update history
                if delay > 1e-6:
                    throughput = (video_chunk_size * 8.0 / 1000.0) / (delay / 1000.0)
                else:
                    throughput = video_bit_rates[bit_rate]
                    
                wrapper_self.history['throughput'].append(throughput)
                wrapper_self.history['delay'].append(delay)
                wrapper_self.history['buffer'].append(buffer_size)
                wrapper_self.history['bitrate'].append(bit_rate)
                wrapper_self.history['rebuf'].append(rebuf)
                
                # Compute state using LLM function
                history_dict = {k: list(v) for k, v in wrapper_self.history.items()}
                state = compute_state_fn(
                    buffer_size=buffer_size,
                    delay=delay,
                    video_chunk_size=video_chunk_size,
                    next_chunk_sizes=np.array(next_chunk_sizes, dtype=np.float64),
                    video_chunk_remain=video_chunk_remain,
                    last_bit_rate=bit_rate,
                    video_bit_rates=video_bit_rates,
                    rebuf=rebuf,
                    history=history_dict
                )
                
                state = np.array(state, dtype=np.float32)
                if wrapper_self.state_dim is None:
                    wrapper_self.state_dim = state.shape
                    
                return state
                
            def step(wrapper_self, action):
                bit_rate = int(action)
                
                delay, sleep_time, buffer_size, rebuf, \
                    video_chunk_size, next_chunk_sizes, \
                    end_of_video, video_chunk_remain = wrapper_self.env.get_video_chunk(bit_rate)
                
                # Compute reward (QoE)
                reward = (
                    video_bit_rates[bit_rate] / M_IN_K
                    - wrapper_self._get_rebuf_penalty() * rebuf
                    - wrapper_self._get_smooth_penalty() * np.abs(
                        video_bit_rates[bit_rate] - video_bit_rates[wrapper_self.last_bit_rate]
                    ) / M_IN_K
                )
                
                # Update history
                if delay > 1e-6:
                    throughput = (video_chunk_size * 8.0 / 1000.0) / (delay / 1000.0)
                else:
                    throughput = video_bit_rates[bit_rate]
                    
                wrapper_self.history['throughput'].append(throughput)
                wrapper_self.history['delay'].append(delay)
                wrapper_self.history['buffer'].append(buffer_size)
                wrapper_self.history['bitrate'].append(bit_rate)
                wrapper_self.history['rebuf'].append(rebuf)
                
                wrapper_self.last_bit_rate = bit_rate
                
                # Compute state using LLM function
                history_dict = {k: list(v) for k, v in wrapper_self.history.items()}
                state = compute_state_fn(
                    buffer_size=buffer_size,
                    delay=delay,
                    video_chunk_size=video_chunk_size,
                    next_chunk_sizes=np.array(next_chunk_sizes, dtype=np.float64),
                    video_chunk_remain=video_chunk_remain,
                    last_bit_rate=bit_rate,
                    video_bit_rates=video_bit_rates,
                    rebuf=rebuf,
                    history=history_dict
                )
                
                state = np.array(state, dtype=np.float32)
                
                # Normalize reward for training stability
                reward = reward / 10.0
                
                return state, reward, end_of_video, {}
                
            def _get_rebuf_penalty(wrapper_self):
                return 4.3  # Default rebuf penalty
                
            def _get_smooth_penalty(wrapper_self):
                return 1.0
        
        return ABREnvWrapper
    
    def _train_model(self, env_class, network, epochs=MAX_EPOCHS):
        """
        Train the A3C agent.
        
        Args:
            env_class: Environment wrapper class
            network: PyTorch nn.Module
            epochs: Number of training epochs
            
        Returns:
            Trained network
        """
        env = env_class(random_seed=self.random_seed)
        
        # Setup optimizer
        optimizer = optim.RMSprop(network.parameters(), lr=ACTOR_LR_RATE)
        
        state = env.reset()
        s_batch, a_batch, r_batch = [], [], []
        
        epoch = 0
        while epoch < epochs:
            network.eval()
            with torch.no_grad():
                state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
                action_probs, _ = network(state_tensor)
                action_probs = action_probs.numpy().flatten()
            
            # Sample action
            action_cumsum = np.cumsum(action_probs)
            action = (action_cumsum > np.random.rand()).argmax()
            
            # Store experience
            s_batch.append(state)
            action_vec = np.zeros(A_DIM)
            action_vec[action] = 1
            a_batch.append(action_vec)
            
            # Step environment
            state, reward, done, _ = env.step(action)
            r_batch.append(reward)
            
            # Train when batch is full or episode ends
            if len(r_batch) >= TRAIN_SEQ_LEN or done:
                # Compute returns
                network.train()
                
                s_tensor = torch.tensor(np.array(s_batch), dtype=torch.float32)
                a_tensor = torch.tensor(np.array(a_batch), dtype=torch.float32)
                r_array = np.array(r_batch)
                
                # Forward pass
                action_probs, values = network(s_tensor)
                
                # Compute n-step returns
                R_batch = torch.zeros_like(values)
                if done:
                    R_t = 0.0
                else:
                    R_t = values[-1].item()
                    
                for t in reversed(range(len(r_batch))):
                    R_t = r_array[t] + GAMMA * R_t
                    R_batch[t, 0] = R_t
                
                # Compute losses
                advantage = R_batch - values
                critic_loss = advantage.pow(2).mean()
                
                log_probs = torch.log(action_probs + 1e-10)
                actor_loss = -(torch.sum(log_probs * a_tensor, dim=1) * advantage.detach().squeeze()).mean()
                
                entropy = -torch.sum(action_probs * log_probs, dim=1).mean()
                entropy_weight = self._get_entropy_weight(epoch)
                
                total_loss = actor_loss + 0.5 * critic_loss - entropy_weight * entropy
                
                # Backprop
                optimizer.zero_grad()
                total_loss.backward()
                torch.nn.utils.clip_grad_norm_(network.parameters(), 5.0)
                optimizer.step()
                
                epoch += 1
                s_batch, a_batch, r_batch = [], [], []
                
            if done:
                state = env.reset()
        
        return network
    
    def _get_entropy_weight(self, epoch):
        """Calculate entropy weight with decay."""
        weight = ENTROPY_WEIGHT - (epoch // ENTROPY_DECAY_INTERVAL) * 0.1
        return max(weight, ENTROPY_MIN)
    
    def _evaluate_model(self, network, compute_state_fn):
        """
        Evaluate trained model on test traces.
        
        Returns:
            Total QoE across all test traces
        """
        total_qoe = 0.0
        
        for trace_idx in range(len(self.test_file_names)):
            # Create test environment for this trace
            test_env = self.train_env.Environment(
                all_cooked_time=[self.test_cooked_time[trace_idx]],
                all_cooked_bw=[self.test_cooked_bw[trace_idx]],
                random_seed=self.random_seed
            )
            
            history = {
                'throughput': deque(maxlen=HISTORY_LEN),
                'delay': deque(maxlen=HISTORY_LEN),
                'buffer': deque(maxlen=HISTORY_LEN),
                'bitrate': deque(maxlen=HISTORY_LEN),
                'rebuf': deque(maxlen=HISTORY_LEN),
            }
            
            last_bit_rate = DEFAULT_QUALITY
            bit_rate = DEFAULT_QUALITY
            episode_reward = 0.0
            
            while True:
                delay, sleep_time, buffer_size, rebuf, \
                    video_chunk_size, next_chunk_sizes, \
                    end_of_video, video_chunk_remain = test_env.get_video_chunk(bit_rate)
                
                # Compute reward
                reward = (
                    self.video_bit_rates[bit_rate] / M_IN_K
                    - self.rebuf_penalty * rebuf
                    - self.smooth_penalty * np.abs(
                        self.video_bit_rates[bit_rate] - self.video_bit_rates[last_bit_rate]
                    ) / M_IN_K
                )
                episode_reward += reward
                
                # Update history
                if delay > 1e-6:
                    throughput = (video_chunk_size * 8.0 / 1000.0) / (delay / 1000.0)
                else:
                    throughput = self.video_bit_rates[bit_rate]
                    
                history['throughput'].append(throughput)
                history['delay'].append(delay)
                history['buffer'].append(buffer_size)
                history['bitrate'].append(bit_rate)
                history['rebuf'].append(rebuf)
                
                last_bit_rate = bit_rate
                
                if end_of_video:
                    break
                
                # Compute state and select action
                history_dict = {k: list(v) for k, v in history.items()}
                state = compute_state_fn(
                    buffer_size=buffer_size,
                    delay=delay,
                    video_chunk_size=video_chunk_size,
                    next_chunk_sizes=np.array(next_chunk_sizes, dtype=np.float64),
                    video_chunk_remain=video_chunk_remain,
                    last_bit_rate=bit_rate,
                    video_bit_rates=self.video_bit_rates,
                    rebuf=rebuf,
                    history=history_dict
                )
                
                state = np.array(state, dtype=np.float32)
                
                network.eval()
                with torch.no_grad():
                    state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
                    action_probs, _ = network(state_tensor)
                    bit_rate = action_probs.argmax(dim=1).item()
            
            total_qoe += episode_reward
        
        return total_qoe

    def evaluate(self, code_string):
        """
        Evaluate LLM-generated code.
        
        Args:
            code_string: Python code containing compute_state() and build_network()
            
        Returns:
            Negative QoE (for minimization) or None on failure
        """
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                # Create module from code string
                heuristic_module = types.ModuleType("heuristic_module")
                
                # Add necessary imports to module namespace
                heuristic_module.__dict__['__builtins__'] = __builtins__
                heuristic_module.__dict__['np'] = np
                heuristic_module.__dict__['numpy'] = np
                heuristic_module.__dict__['torch'] = torch
                heuristic_module.__dict__['nn'] = nn
                heuristic_module.__dict__['F'] = F
                heuristic_module.__dict__['optim'] = optim
                
                # Prepend imports if not present in code
                import_block = (
                    "import numpy as np\n"
                    "import torch\n"
                    "import torch.nn as nn\n"
                    "import torch.nn.functional as F\n"
                )
                if "import numpy" not in code_string and "import np" not in code_string:
                    code_string = import_block + code_string
                
                # Execute code
                exec(code_string, heuristic_module.__dict__)
                
                # Validate required functions exist
                if not hasattr(heuristic_module, 'compute_state'):
                    print("Error: compute_state function not found")
                    return None
                if not hasattr(heuristic_module, 'build_network'):
                    print("Error: build_network function not found")
                    return None
                
                compute_state_fn = heuristic_module.compute_state
                build_network_fn = heuristic_module.build_network
                
                # Create environment wrapper
                env_class = self._create_env_wrapper(compute_state_fn)
                
                # Get state dimensions from a test reset
                test_env = env_class(random_seed=0)
                test_state = test_env.reset()
                state_dim = test_state.shape
                
                # Build network with better error handling
                try:
                    network = build_network_fn(state_dim, A_DIM)
                except NameError as e:
                    # Common error: LLM uses 'state' instead of 'state_dim' or 'x'
                    print(f"NameError in build_network: {e}")
                    print(f"Error Code: {code_string}")
                    return None
                    
                if not isinstance(network, nn.Module):
                    print("Error: build_network must return nn.Module")
                    return None
                
                # Validate network output
                test_input = torch.tensor(test_state, dtype=torch.float32).unsqueeze(0)
                action_probs, value = network(test_input)
                
                if action_probs.shape != (1, A_DIM):
                    print(f"Error: action_probs shape {action_probs.shape} != (1, {A_DIM})")
                    return None
                if value.shape != (1, 1):
                    print(f"Error: value shape {value.shape} != (1, 1)")
                    return None
                
                # Train model
                trained_network = self._train_model(env_class, network)
                
                # Evaluate on test traces
                total_qoe = self._evaluate_model(trained_network, compute_state_fn)
                
                if not np.isfinite(total_qoe):
                    return None
                
                # Return negative QoE (EoH minimizes)
                return float(-total_qoe)
                
        except Exception as e:
            print(f"Evaluation error: {e}")
            import traceback
            traceback.print_exc()
            return None


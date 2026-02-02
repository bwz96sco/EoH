# EoH-ABR Integration Plan

## Problem Summary

Current issues with `user_abr_bb` and `user_abr_quetra`:
1. **Inconsistent function signatures**: BB uses 12 parameters, Quetra uses 14 parameters
2. **Prompts don't leverage existing heuristics**: Current prompts only describe the problem, not utilizing BB/BOLA/QUETRA/MPC as seed heuristics for evolution

## Goal

Implement a unified ABR heuristic evolution framework that:
1. Uses a **common `score(state, ctx)` interface** for all ABR algorithms
2. **Seeds the initial population** with existing heuristics (BB, BOLA, QUETRA, RobustMPC)
3. **Incorporates parent heuristics in prompts** for e1/e2/m1/m2/m3 operations

---

## Implementation Plan

### Phase 1: Create Unified ABR API

**File: `examples/user_abr/abr_api.py`**

```python
def extract_state(obs, info, last_action, throughput_history) -> dict:
    """Convert SABR env observation to LLM-friendly dict"""
    return {
        "buffer_s": float,           # Current buffer in seconds
        "last_bitrate_idx": int,     # Previous bitrate index
        "throughput_hist_mbps": np.ndarray,  # Recent throughputs
        "next_chunk_sizes_bytes": np.ndarray,  # Chunk sizes per bitrate
        "chunk_remain": int,         # Chunks remaining
        "rebuffer_sec": float,       # Last rebuffer duration
    }

def make_ctx(config) -> dict:
    """Build context dict with constants"""
    return {
        "bitrates_kbps": np.ndarray,  # Available bitrate levels
        "chunk_len_s": float,         # Chunk duration
        "smooth_penalty": float,      # δ coefficient
        "rebuf_penalty": float,       # μ coefficient
        "buffer_max_s": float,        # Max buffer capacity
        # Algorithm-specific knobs
        "reservoir_s": float,         # BB threshold
        "cushion_s": float,           # BB cushion
        "V": float,                   # BOLA aggressiveness
        "alpha": float,               # QUETRA EMA factor
        "robust_margin": float,       # MPC safety margin
    }
```

**Target function signature (unified for all ABR heuristics):**
```python
def score(state: dict, ctx: dict) -> np.ndarray:
    """
    Returns scores for each bitrate action; higher is better.
    Shape: (K,) where K = number of bitrate levels.
    """
```

### Phase 2: Create Seed Heuristics

**File: `examples/user_abr/seed_heuristics.py`**

Implement 4-5 seed heuristics in unified `score(state, ctx)` format:

| Heuristic | One-Sentence Description |
|-----------|-------------------------|
| BB | Buffer-based: linearly interpolate bitrate between reservoir and cushion thresholds |
| BOLA | Lyapunov optimization: trade utility plus buffer against chunk size |
| QUETRA | Queue-theoretic: target buffer occupancy based on throughput utilization |
| RobustMPC | Short-horizon planning: predict rebuffer and smooth penalties using harmonic mean bandwidth |
| Rate-based | Simple: pick highest bitrate that doesn't exceed predicted throughput |

Each heuristic follows identical structure:
```python
def score_bb(state, ctx):
    """Buffer-based: select bitrate by linear interpolation between reservoir and cushion."""
    R = np.asarray(ctx["bitrates_kbps"], dtype=float)
    B = float(state["buffer_s"])
    reservoir = float(ctx.get("reservoir_s", 5.0))
    cushion = float(ctx.get("cushion_s", 10.0))
    # ... implementation
    return -np.abs(R - target)  # Shape (K,)
```

### Phase 3: Unified Problem Class

**File: `examples/user_abr/prob.py`**

Create unified `ABRProblem` class that:

1. **Imports SABR modules** from `/env/SABR/`
2. **Implements `evaluate(code_string)`** with unified interface:
   ```python
   def evaluate(self, code_string):
       # Execute code, extract score() function
       # Run simulation: action = np.argmax(score(state, ctx))
       # Return negative mean QoE (EoH minimizes)
   ```
3. **Simulation loop** using `extract_state()` and `make_ctx()`
4. **Error handling** with action sanitization

### Phase 4: Enhanced Prompts with Parent Heuristics

**File: `examples/user_abr/prompts.py`**

Create `GetPrompts` class that:

1. **Includes task description** for ABR problem
2. **Defines unified function signature** `score(state, ctx) -> np.ndarray`
3. **Provides seed heuristics** for initial population seeding
4. **Supports parent heuristic injection** in e1/e2/m1/m2/m3 prompts

Key methods:
```python
class GetPrompts:
    def get_task(self):
        return """Design a heuristic for Adaptive Bitrate (ABR) streaming.
        At each chunk, score each bitrate; the client picks argmax.
        QoE = Σ bitrate - δ*|Δbitrate| - μ*rebuffer_seconds"""

    def get_func_name(self): return "score"
    def get_func_inputs(self): return ["state", "ctx"]
    def get_func_outputs(self): return ["scores"]

    def get_seed_heuristics(self):
        """Return list of seed heuristics for initial population"""
        return [
            {"algorithm": "{BB: linear interpolation...}", "code": "..."},
            {"algorithm": "{BOLA: utility+buffer...}", "code": "..."},
            {"algorithm": "{QUETRA: buffer-as-queue...}", "code": "..."},
            {"algorithm": "{RobustMPC: predict rebuffer...}", "code": "..."},
        ]
```

### Phase 5: Feedback Formatting

**File: `examples/user_abr/feedback.py`**

Create feedback formatter for M1 mutations:
```python
def format_feedback(eval_results):
    """Summarize why heuristic failed for LLM guidance"""
    return f"""
    Mean QoE: {qoe:.2f}
    Mean rebuffer: {rebuf:.2f}s
    Mean bitrate: {bitrate:.0f} kbps
    Mean switch magnitude: {switch:.0f} kbps
    Issue: {diagnose_failure_mode(eval_results)}
    """
```

### Phase 6: Main Runner

**File: `examples/user_abr/runEoH.py`**

```python
from eoh import eoh
from eoh.utils.getParas import Paras
from prob import ABRProblem

problem = ABRProblem()
paras = Paras()

paras.set_paras(
    method="eoh",
    problem=problem,
    llm_api_endpoint="...",
    llm_model="...",
    ec_pop_size=5,  # Match 5 seed heuristics
    ec_n_pop=10,
    exp_n_proc=4,
    eva_numba_decorator=False,
    # Seed with existing heuristics
    initial_population=problem.prompts.get_seed_heuristics()
)

evolution = eoh.EVOL(paras)
evolution.run()
```

---

## File Structure

```
examples/user_abr/
├── runEoH.py           # Main entry point
├── prob.py             # Unified ABRProblem class
├── prompts.py          # Enhanced prompts with seed heuristics
├── abr_api.py          # extract_state() and make_ctx()
├── seed_heuristics.py  # BB/BOLA/QUETRA/MPC/Rate-based implementations
├── feedback.py         # Failure mode diagnosis for M1
└── evaluation/
    ├── runEval.py      # Post-evolution evaluation
    └── heuristic.py    # Copy evolved heuristic here
```

---

## Key Changes from Current Implementation

| Aspect | Current (BB/Quetra) | New (Unified) |
|--------|---------------------|---------------|
| Function signature | `select_bitrate(12-14 params)` | `score(state, ctx) -> np.ndarray` |
| Seed heuristics | None | BB, BOLA, QUETRA, MPC, Rate-based |
| Prompt content | Problem description only | Problem + parent heuristics |
| State handling | Raw params | Named dict fields |
| Algorithm variations | Separate folders | Single unified framework |

---

## Verification Plan

1. **Unit test seed heuristics**: Verify each returns valid `np.ndarray` shape `(K,)`
2. **Integration test**: Run single evaluation with each seed heuristic
3. **Evolution test**: Run EoH with seed population, verify parents appear in prompts
4. **Comparison test**: Compare evolved heuristics against baseline BB/BOLA/QUETRA/MPC on SABR test traces

---

## Migration Path

1. Create new `examples/user_abr/` with unified implementation
2. Validate the unified implementation works correctly
3. Delete `user_abr_bb/` and `user_abr_quetra/` folders

# Quality Guidelines

> Code quality standards for EoH backend development.

---

## Overview

EoH is a research-oriented Python framework. It has no linting, formatting, or type-checking tools configured. The codebase uses mixed conventions. This document captures the actual patterns to follow for consistency.

---

## Build and Dependencies

- **Python**: >= 3.10 (required)
- **Package manager**: `uv` (recommended) or pip
- **Build system**: setuptools via `pyproject.toml`
- **Core dependencies**: numpy, numba, joblib, requests
- **No linting/formatting tools** configured (no ruff, black, mypy, flake8)
- **No CI/CD pipeline**

---

## Code Style (Actual Conventions)

### Naming

| Element | Convention | Examples |
|---------|-----------|----------|
| Classes | PascalCase or ALLCAPS | `EVOL`, `EOH`, `InterfaceEC`, `GetPrompts`, `BPONLINE` |
| Functions | snake_case | `parent_selection()`, `population_management()`, `get_response()` |
| Files | Mixed (see directory-structure.md) | snake_case preferred for new files |
| Constants | Not explicitly defined | Inline values throughout |

### Type Hints

Type hints are **inconsistently used**. They appear in newer files (`user_abr/prob.py`, `evaluator_accelerate.py`, `api_local_llm.py`) but are absent from most core files.

**For new code**: Add type hints to function signatures. Use Python 3.10+ syntax (`str | None` instead of `Optional[str]`).

```python
# Good (newer style, as in examples/user_abr/prob.py)
def evaluate_with_details(self, code_string: str) -> tuple[float | None, str | None]:

# Existing style (most core code, no annotations)
def evaluate(self, code_string):
```

### Imports

Imports are currently unorganized (stdlib, third-party, local mixed together). **For new code**, prefer PEP 8 grouping:

```python
# stdlib
import json
import time

# third-party
import numpy as np
from joblib import Parallel, delayed

# local
from .eoh_evolution import Evolution
```

### Docstrings

Docstrings are rare. When present, they use one-liner or informal style. **For new code**, add docstrings to public methods at minimum.

---

## Architecture Patterns

### Factory/Delegation Pattern (Core Architecture)

```python
# eoh/src/eoh/eoh.py:32-42 -- EVOL delegates to resolved method
def run(self):
    problemGenerator = problems.Probs(self.paras)
    problem = problemGenerator.get_problem()
    methodGenerator = methods.Methods(self.paras, problem)
    method = methodGenerator.get_method()
    method.run()
```

### Configuration via Paras Class

All configuration flows through a single `Paras` object using `setattr`:

```python
# eoh/src/eoh/utils/getParas.py:99-113
def set_paras(self, *args, **kwargs):
    for key, value in kwargs.items():
        if hasattr(self, key):
            setattr(self, key, value)
```

**Warning**: Typos in parameter names are silently ignored due to `hasattr` check.

### Duck-Typed Problem Interface

Problems use duck typing (no base class or Protocol):

```python
# Required interface for any problem class:
class MyProblem:
    def __init__(self):
        self.prompts = GetPrompts()  # Must have .prompts attribute

    def evaluate(self, code_string) -> float | None:
        # Must accept code string, return fitness or None
        ...

    # Optional: enables feedback-guided mutation
    def evaluate_with_details(self, code_string) -> tuple[float | None, str | None]:
        ...
```

### Explicit Prompt/Evaluator Contracts

For LLM-evolved problems that pass helper inputs such as `state` and `ctx`, keep the contract explicit and synchronized across prompt text, evaluator code, and seed heuristics.

**Convention**:
- `state` should contain per-step runtime observations only
- Evaluator-owned `ctx` should contain shared environment constants only
- Heuristic-specific thresholds, horizons, and safety margins should live inside the heuristic code, not as hidden `ctx` fields

**Example** (`examples/user_abr/`):

```python
# Good: ctx only exposes environment constants used by every heuristic
ctx = {
    "bitrates_kbps": bitrates_kbps,
    "chunk_len_s": chunk_len_s,
    "smooth_penalty": smooth_penalty,
    "rebuf_penalty": rebuf_penalty,
    "buffer_max_s": buffer_max_s,
}

def score(state, ctx):
    robust_margin = 0.1
    horizon = 3
    ...
```

```python
# Bad: evaluator injects heuristic-owned knobs that the prompt may forget to document
ctx = {
    "bitrates_kbps": bitrates_kbps,
    "robust_margin": 0.1,
    "mpc_horizon": 3,
}
```

**Why**: Hidden `ctx` fields cause prompt/schema drift and make evolved heuristics depend on evaluator internals instead of their own code.

## Scenario: ABR Multi-Step State Contract

### 1. Scope / Trigger
- Trigger: A heuristic needs exact runtime lookahead data, such as SABR-style robust MPC that scores action sequences over several upcoming chunks.

### 2. Signatures

```python
def extract_state(
    obs,
    info,
    last_action,
    throughput_history,
    *,
    future_chunk_sizes_bytes=None,
) -> dict[str, Any]:
    ...

def score(state, ctx):
    ...
```

### 3. Contracts
- `state` may grow with additional runtime observations when the evaluator can derive them at each step.
- For ABR lookahead, put future chunk sizes in `state["future_chunk_sizes_bytes"]` as shape `(H, K)`.
- `ctx` keeps shared environment constants only, such as `chunk_len_s`, `rebuf_penalty`, `smooth_penalty`, `buffer_max_s`, and `link_rtt_s`.
- Keep heuristic-owned knobs such as MPC horizon or buffer penalties inside the heuristic code.

### 4. Validation & Error Matrix

| Condition | Expected behavior |
|-----------|-------------------|
| `future_chunk_sizes_bytes` missing | Evaluator or helper should fall back to a single-step matrix built from `next_chunk_sizes_bytes` |
| `future_chunk_sizes_bytes.shape[1] != len(ctx["bitrates_kbps"])` | Heuristic should reject the input and return a safe default score vector |
| Extra heuristic knobs passed through `ctx` | `make_ctx()` should raise `ValueError` |

### 5. Good/Base/Bad Cases
- Good: `state` includes `future_chunk_sizes_bytes` because it changes every chunk and depends on the current chunk index.
- Base: `state` includes only `next_chunk_sizes_bytes` when no multi-step planner needs more lookahead.
- Bad: `ctx` includes `mpc_horizon`, `robust_margin`, or other algorithm-specific tuning fields.

### 6. Tests Required
- Smoke test: seed functions accept the widened `state` and still return finite score arrays.
- Verification test: SABR-style robust MPC seed matches a faithful port on the same per-step states.
- Contract test: prompt text, evaluator state construction, and seed expectations list the same fields.

### 7. Wrong vs Correct

#### Wrong

```python
ctx = {
    "bitrates_kbps": bitrates_kbps,
    "mpc_horizon": 5,
    "link_rtt_s": 0.08,
}
```

#### Correct

```python
state = {
    "next_chunk_sizes_bytes": next_chunk_sizes_bytes,
    "future_chunk_sizes_bytes": future_chunk_sizes_bytes,
}
ctx = {
    "bitrates_kbps": bitrates_kbps,
    "link_rtt_s": 0.08,
}
```

## Scenario: Seed Algorithm Description Contract

### 1. Scope / Trigger
- Trigger: A problem seeds the population with `{"algorithm", "code"}` pairs, or evolution operators feed existing `algorithm` descriptions back into LLM prompts.

### 2. Signatures

```python
seed = {
    "algorithm": str,
    "code": str,
}

offspring = {
    "algorithm": str | None,
    "code": str | None,
    "objective": float | None,
    "other_inf": str | None,
}
```

### 3. Contracts
- Treat `algorithm` as prompt scaffolding, not as a decorative label.
- The description should be one sentence that summarizes the decision backbone:
  signal used, decision rule, and distinguishing mechanism.
- Prefer framework-neutral wording when a generic statement is equally accurate.
- Do not duplicate low-level code details, numeric constants, or long formulas that already appear in `code`.
- Keep the description consistent with the implementation, because operators such as `e1`, `e2`, `m1`, and `m2` show both the description and code to the LLM.

### 4. Validation & Error Matrix

| Condition | Expected behavior |
|-----------|-------------------|
| Description is empty or only a name | Prompt quality degrades because the LLM loses the high-level summary |
| Description is overly long or code-like | Prompt budget is wasted and the summary may conflict with the implementation |
| Description uses repo-specific names that the model may not know | Prefer a generic mechanism-level rewrite if it stays faithful |
| Description disagrees with the code | Fix the description immediately; code-description drift is misleading in mutation/crossover prompts |

### 5. Good/Base/Bad Cases
- Good: `"{Rate-based: use a conservative harmonic-mean bandwidth estimate and penalize bitrates above that budget so the best score stays near the highest sustainable quality}"`
- Base: `"{Rate-based: choose bitrate from predicted bandwidth}"`
- Bad: `"{SABR thing with alpha=0.1 and horizon=5 and some arrays and if-statements copied from the code line by line}"`

### 6. Tests Required
- Prompt inspection: verify parent prompts still show a short mechanism-level summary plus the full code.
- Drift check: when seed code changes materially, review whether the paired description still matches.
- Parsability check: keep the description short enough to read cleanly in `e1/e2/m1/m2` prompts.

### 7. Wrong vs Correct

#### Wrong

```python
{
    "algorithm": "{RobustMPC: SABR-style thing copied from robust_mpc.cc with horizon=5 and hard-coded details from the source file}",
    "code": ROBUST_MPC_CODE,
}
```

#### Correct

```python
{
    "algorithm": "{RobustMPC: estimate conservative future bandwidth from harmonic-mean throughput and recent prediction error, then exhaustively evaluate short bitrate sequences with a bitrate-minus-rebuffer-minus-switching objective and return the first action of the best sequence}",
    "code": ROBUST_MPC_CODE,
}
```

### Module-as-Strategy Pattern

Selection and management strategies are plain modules with a single function:

```python
# eoh/src/eoh/methods/selection/prob_rank.py
def parent_selection(pop, m):
    # Returns list of m parents
    ...
```

### Individual Data Schema

Every individual (offspring) is a dict with exactly these keys:

```python
offspring = {
    'algorithm': str | None,    # Natural language description
    'code': str | None,         # Python source code
    'objective': float | None,  # Fitness value (rounded to 5 decimals)
    'other_inf': str | None     # Evaluation feedback (optional)
}
```

---

## Forbidden Patterns

1. **Never use `logging` module** -- the codebase uses `print()` exclusively. Introducing `logging` would create inconsistency.
2. **Never add database dependencies** -- EoH uses file-based JSON storage only.
3. **Never commit API keys** -- LLM credentials must be set at runtime via `set_paras()` or environment variables.
4. **Never skip the try/except in evaluate()** -- LLM-generated code is untrusted and will frequently fail.
5. **Never modify the individual dict schema** without updating all three method implementations (EOH, AEL, LS).

---

## Required Patterns

1. **Wrap `exec()` in try/except** -- all evaluation of LLM-generated code must catch `Exception` and return `None`
2. **Set timeouts** -- always use `ThreadPoolExecutor` with timeout for evaluation calls
3. **Suppress warnings in evaluate** -- use `with warnings.catch_warnings(): warnings.simplefilter("ignore")`
4. **Save results per generation** -- write population JSON to `results/pops/` at the end of each generation
5. **Gate debug output** -- verbose output should be behind `if self.debug_mode:`

---

## Testing

**Current state**: No formal test suite. Only a manual smoke test at `eoh/src/eoh/test/run.py`.

**For new code**: Manual testing by running an example with a small configuration:

```python
paras.set_paras(
    ec_pop_size=2,
    ec_n_pop=1,
    exp_debug_mode=True
)
```

---

## Code Duplication (Known Issues)

These are known duplications in the codebase:

1. **`evaluator_accelerate.py`** is identically copied in `methods/eoh/`, `methods/ael/`, and `methods/localsearch/`
2. **Method classes** (EOH, AEL, LS) have near-identical `__init__` and `run()` methods (~90% identical)
3. **User-defined problem classes** in examples are often copy-pasted from built-in problem classes

When modifying shared patterns, check all three method implementations.

---

## Code Review Checklist

- [ ] `evaluate()` methods catch `Exception` and return `None`
- [ ] Timeouts set for evaluation calls
- [ ] Debug output gated behind `debug_mode`
- [ ] Population JSON saved per generation
- [ ] No hardcoded API keys or credentials
- [ ] New parameters added to `Paras.__init__` with defaults
- [ ] Changes to individual schema reflected in all methods
- [ ] No `logging` module introduced

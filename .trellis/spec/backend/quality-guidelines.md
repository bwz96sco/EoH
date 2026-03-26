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

## Scenario: Canonical ABR Experiment Output Layout

### 1. Scope / Trigger
- Trigger: Any change to `examples/user_abr/runEoH.py`, `experiments/run_experiment.sh`, or the ABR analysis scripts that write run artifacts.

### 2. Contracts
- Canonical run root is `experiments/results/<run-id>/`.
- `run-id` may be caller-provided via `ABR_RUN_ID`, or auto-generated once by the top-level runner.
- Raw EoH outputs must live under `experiments/results/<run-id>/raw/eoh/<output-name>/...`.
- Caller-controlled names must be sanitized single path components appended under the canonical root. Do not accept free-form output directories.
- Analysis outputs must always be written to:
  - `experiments/results/<run-id>/analysis/results_summary.csv`
  - `experiments/results/<run-id>/analysis/plots/`
- Logs must live under `experiments/results/<run-id>/logs/`.
- `examples/user_abr/seed_cache/<dataset>/` remains cache-only. Do not mix final experiment outputs into `seed_cache`.

### 3. Good/Base/Bad Cases
- Good: `run_experiment.sh` resolves one `run-id`, exports it, and every downstream step writes under the same canonical tree.
- Base: direct `runEoH.py` execution auto-generates a timestamped `run-id` and writes raw EoH output under `experiments/results/<run-id>/raw/eoh/<dataset>/`.
- Bad: `collect_results.py --output /tmp/results.csv` or `plot_results.py --output-dir some/random/path`.
- Bad: copying outputs back out of the canonical tree into `examples/user_abr/results/`.

### 4. Validation & Error Matrix

| Condition | Expected behavior |
|-----------|-------------------|
| `ABR_RUN_ID` unset for the top-level pipeline | Runner creates a timestamped canonical run directory once and reuses it everywhere |
| `ABR_RUN_ID` unset for analysis-only scripts | Script fails fast and asks for `--run-id` or `ABR_RUN_ID` |
| Output name contains `/`, whitespace, or shell metacharacters | Sanitize to a safe single path component before joining under `raw/eoh/` |
| Script accepts arbitrary output directory input | Reject the design and route through canonical helpers instead |

### 5. Tests Required
- `python3 -m py_compile examples/user_abr/runEoH.py experiments/collect_results.py experiments/plot_results.py experiments/run_layout.py`
- `bash -n experiments/run_experiment.sh`
- Manual dry run: confirm one `run-id` produces `raw/`, `analysis/`, and `logs/` under the same timestamped directory

### 6. Wrong vs Correct

#### Wrong

```python
parser.add_argument("--output", help="Write anywhere the caller wants")
```

#### Correct

```python
parser.add_argument("--run-id", default=os.environ.get("ABR_RUN_ID"))
output_path = build_analysis_csv_path(REPO_ROOT, run_id=args.run_id)
```

## Scenario: ABR Experiment Tracker Contract

### 1. Scope / Trigger
- Trigger: Any change to `experiments/run_experiment.sh`, `experiments/update_experiment_tracker.py`, `experiments/run_layout.py`, or ABR analysis code that affects what a canonical run records.

### 2. Signatures

```bash
python3 experiments/update_experiment_tracker.py
python3 experiments/update_experiment_tracker.py --run-id 20260325-234552-abr-rerun
```

```python
def build_experiment_tracker_path(repo_root: Path) -> Path:
    ...
```

### 3. Contracts
- Canonical tracker path is `experiments/experiment_index.md`.
- The tracker is generated from canonical run roots under `experiments/results/<run-id>/`; do not hand-maintain parallel notes elsewhere.
- Each entry must record, when available:
  - run id and status
  - short abstract/scope
  - models used and key EoH parameters
  - short result record
  - paths to canonical artifacts such as run root, summary CSV, plots, report, log, and best heuristic snapshots
- Partial runs must still appear if they already created a canonical run directory or pipeline log.
- The top-level ABR workflow must refresh the tracker automatically at the end of the run, including partial/failing runs via an `EXIT`-time update.
- The tracker summarizes the runs currently present on disk. If old run directories are deleted, their entries disappear on the next rebuild.

### 4. Validation & Error Matrix

| Condition | Expected behavior |
|-----------|-------------------|
| Completed run has `analysis/results_summary.csv` | Tracker entry status becomes `completed` and includes suite-level short results |
| Partial run has raw outputs or pipeline log but no summary CSV | Tracker entry status becomes `partial` and lists available artifacts only |
| `experiments/results/` is empty | Tracker still writes `experiments/experiment_index.md` with an empty-state message |
| A run reuses shared SABR baselines because phase 2 was skipped | Tracker abstract/phase record should say phase 2 was skipped, so provenance stays explicit |
| A path in config points to a temp seed file | Tracker should summarize it as generated seed provenance instead of a meaningless temp path dump |

### 5. Good/Base/Bad Cases
- Good: `run_experiment.sh` updates the tracker automatically on exit, and the tracker is rebuilt from canonical run directories.
- Base: a manual `python3 experiments/update_experiment_tracker.py` refresh after a direct experiment run.
- Bad: keeping experiment history only in ad hoc chat logs or hand-edited notes.
- Bad: recording a run in the tracker while its actual outputs live outside `experiments/results/<run-id>/`.

### 6. Tests Required
- `python3 -m py_compile experiments/update_experiment_tracker.py experiments/run_layout.py`
- `bash -n experiments/run_experiment.sh`
- Manual check: run `python3 experiments/update_experiment_tracker.py` and verify `experiments/experiment_index.md` includes the current canonical run with artifact paths and suite-level short results.

### 7. Wrong vs Correct

#### Wrong

```markdown
- Keep a private note somewhere about the run.
- Save some outputs under `results/`, some under `examples/user_abr/`, and manually paste a summary later.
```

#### Correct

```bash
ABR_RUN_ID=20260326-abr bash experiments/run_experiment.sh
# ...
# EXIT hook refreshes experiments/experiment_index.md from experiments/results/<run-id>/
```

## Scenario: Remote LLM Transport Contract

### 1. Scope / Trigger
- Trigger: A remote chat-completion endpoint is used through `eoh/src/eoh/llm/api_general.py`.

### 2. Signatures

```python
class InterfaceAPI:
    def __init__(self, api_endpoint, api_key, model_LLM, debug_mode):
        ...

    def get_response(self, prompt_content):
        ...
```

### 3. Contracts
- `api_endpoint` may be a bare host, `http://host[:port]`, `https://host[:port]`, or a base path ending in `/v1` or `/chat/completions`.
- Bare hosts default to HTTPS.
- The request payload must send `"stream": False`, because the client expects one JSON response with `choices[0].message.content`.
- The request path must normalize as:
  - bare host or base host -> `/v1/chat/completions`
  - endpoint ending in `/v1` -> `/v1/chat/completions`
  - endpoint ending in `/chat/completions` -> use as-is
- Responses without a `choices` key are retryable API failures, not successful empty replies.

### 4. Validation & Error Matrix

| Condition | Expected behavior |
|-----------|-------------------|
| `api_endpoint="api.example.com"` | Use `HTTPSConnection("api.example.com")` and path `/v1/chat/completions` |
| `api_endpoint="http://127.0.0.1:8000"` | Use `HTTPConnection("127.0.0.1:8000")` |
| Endpoint streams by default | Sending `"stream": False` should force a single JSON completion |
| Response body only contains `{"error": ...}` | Raise retryable error with keys/body snippet and continue retry loop |

### 5. Good/Base/Bad Cases
- Good: `LLM_API_ENDPOINT=http://host:8000` for an HTTP reverse proxy that serves OpenAI-compatible chat completions.
- Base: `LLM_API_ENDPOINT=api.openai.com` for a standard HTTPS provider.
- Bad: Hardcoding `HTTPSConnection` and assuming every response contains `choices`.

### 6. Tests Required
- `python3 -m py_compile eoh/src/eoh/llm/api_general.py`
- One real API smoke check that verifies `get_response("Reply with only: 2")` returns a normal completion on the configured endpoint.

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

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

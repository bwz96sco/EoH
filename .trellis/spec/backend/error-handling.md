# Error Handling

> How errors are handled in the EoH project.

---

## Overview

EoH uses a **layered error suppression architecture**. There are no custom exception classes. Errors are caught broadly at each boundary layer and converted to `None` values that propagate upward. The population management layer acts as the final cleanup, discarding individuals with `None` objectives.

This design is intentional: LLM-generated code is untrusted and frequently produces runtime errors, so the framework must be resilient to arbitrary failures during evaluation.

---

## Error Types

**No custom exceptions.** The project uses only built-in Python exceptions. The universal error signal is `None` (returned in place of a fitness value when evaluation fails).

---

## Error Handling Patterns

### Pattern 1: Catch-All -> Return None (Evaluation Layer)

This is the **dominant pattern** across all problem evaluators. Every `evaluate()` method wraps `exec()` of LLM-generated code in a broad try/except.

```python
# eoh/src/eoh/problems/optimization/bp_online/run.py:105-125
def evaluate(self, code_string):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            heuristic_module = types.ModuleType("heuristic_module")
            exec(code_string, heuristic_module.__dict__)
            sys.modules[heuristic_module.__name__] = heuristic_module
            fitness = self.evaluateGreedy(heuristic_module)
            return fitness
    except Exception as e:
        return None
```

**Convention**: All `evaluate()` methods must catch `Exception` and return `None` on failure. Error prints inside the except block are typically commented out.

### Pattern 2: Catch-All -> Return Null Offspring (Method Layer)

The `InterfaceEC.get_offspring()` wraps the entire offspring generation + evaluation:

```python
# eoh/src/eoh/methods/eoh/eoh_interface_EC.py:144-215
def get_offspring(self, pop, operator):
    try:
        p, offspring = self._get_alg(pop, operator)
        # ... evaluate ...
    except Exception as e:
        offspring = {
            'algorithm': None,
            'code': None,
            'objective': None,
            'other_inf': None
        }
        p = None
    return p, offspring
```

Null offspring are filtered out by population management:

```python
# eoh/src/eoh/methods/management/pop_greedy.py:4
pop = [individual for individual in pop if individual['objective'] is not None]
```

### Pattern 3: Retry with Bounded Attempts (LLM API)

Remote LLM API calls retry up to 5 times:

```python
# eoh/src/eoh/llm/api_general.py:31-50
response = None
n_trial = 1
while True:
    n_trial += 1
    if n_trial > self.n_trial:     # self.n_trial = 5
        return response             # returns None after 5 failures
    try:
        conn = http.client.HTTPSConnection(self.api_endpoint)
        conn.request("POST", "/v1/chat/completions", payload, headers)
        # ... parse response ...
        break
    except Exception as e:
        if self.debug_mode:
            print(f"Error in API (attempt {n_trial}/{self.n_trial}): {e}")
        continue
```

### Pattern 4: Infinite Retry (Local LLM API)

Local LLM calls retry forever with bare `except:`:

```python
# eoh/src/eoh/llm/api_local_llm.py:14-20
def get_response(self, content: str) -> str:
    while True:
        try:
            response = self._do_request(content)
            return response
        except:
            continue
```

### Pattern 5: Early exit() on Misconfiguration

LLM configuration errors terminate the process immediately:

```python
# eoh/src/eoh/llm/interface_LLM.py:18-45
if self.api_key == None or self.api_endpoint == None:
    print(">> Stop with wrong API setting: ...")
    exit()

res = self.interface_llm.get_response("1+1=?")
if res == None:
    print(">> Error in LLM API, wrong endpoint, key, model or local deployment!")
    exit()
```

### Pattern 6: LLM Response Parsing Retry

When regex fails to extract algorithm/code from LLM response, retry up to 3 times:

```python
# eoh/src/eoh/methods/eoh/eoh_evolution.py:144-191
n_retry = 1
while (len(algorithm) == 0 or len(code) == 0):
    response = self.interface_llm.get_response(prompt_content)
    # ... regex extraction ...
    if n_retry > 3:
        break
    n_retry += 1
```

**Warning**: If all retries fail, `algorithm[0]` on an empty list raises uncaught `IndexError`.

### Pattern 7: Large Penalty Value (Solver Fallback)

Some user-defined problems assign a large penalty instead of `None`:

```python
# examples/user_tsp_gls/gls/gls_run.py:19-34
try:
    # ... run GLS solver ...
    gap = (best_cost / opt_cost - 1) * 100
except Exception as e:
    gap = 1E10  # Very large penalty value
```

### Pattern 8: Parallel Execution Timeout

Joblib parallel execution catches timeout exceptions:

```python
# eoh/src/eoh/methods/eoh/eoh_interface_EC.py:235-244
try:
    results = Parallel(n_jobs=self.n_p, timeout=self.timeout+15)(
        delayed(self.get_offspring)(pop, operator) for _ in range(self.pop_size))
except Exception as e:
    print("Parallel time out .")
```

Individual evaluations use `ThreadPoolExecutor` for per-task timeouts:

```python
with concurrent.futures.ThreadPoolExecutor() as executor:
    future = executor.submit(self.interface_eval.evaluate, code)
    fitness = future.result(timeout=self.timeout)
```

---

## Error Propagation Summary

| Layer | Pattern | On Error |
|-------|---------|----------|
| LLM API (remote) | Retry 5 times | Returns `None` |
| LLM API (local) | Infinite retry | Never returns failure |
| LLM Config | Validation | `exit()` |
| Response Parsing | Retry 3 times | Potential `IndexError` crash |
| Evaluation | Catch-all | Returns `None` |
| Offspring Creation | Catch-all | Returns null offspring dict |
| Parallel Execution | Catch timeout | Partial results |
| Seed Init | Catch-all | `exit()` (fatal) |
| Population Management | Filter | Removes `None` objectives |
| Main Loop | None | No error handling |

---

## Conventions for New Code

1. **Evaluate methods**: Always wrap in try/except, return `None` on failure
2. **LLM calls**: Use bounded retry (don't use bare `except:` with infinite retry)
3. **Configuration errors**: Use `exit()` with descriptive print message
4. **Parallel execution**: Always set timeouts on both joblib and ThreadPoolExecutor
5. **Warnings**: Suppress with `warnings.catch_warnings()` context manager inside evaluate methods
6. **Never raise custom exceptions** -- the framework expects `None` as the error signal

---

## Common Mistakes

1. **Forgetting to handle `None` fitness**: When processing evaluation results, always check for `None` before numeric operations
2. **Bare `except:` with infinite retry**: Only acceptable for local LLM (where server restart is expected). Use bounded retries for everything else
3. **Not setting timeouts**: Evaluation of LLM-generated code can hang forever. Always use `ThreadPoolExecutor` with timeout
4. **Using `== None` instead of `is None`**: The codebase uses `== None` throughout (legacy pattern), but `is None` is preferred for new code

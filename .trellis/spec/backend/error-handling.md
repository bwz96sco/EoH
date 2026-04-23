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
# eoh/src/eoh/methods/eoh/eoh_interface_EC.py:304-415
def get_offspring(self, pop, operator, generation, offspring_index):
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

Remote LLM API calls retry up to 5 times with exponential backoff:

```python
# eoh/src/eoh/llm/api_general.py:32-105
response = None
start_time = time.monotonic()
for attempt in range(1, self.n_trial + 1):
    elapsed_before_attempt = time.monotonic() - start_time
    if elapsed_before_attempt >= self.total_timeout_s:
        self.last_request_meta = {
            "status": "llm_timeout",
            "attempts": attempt - 1,
            "elapsed_ms": round(elapsed_before_attempt * 1000, 3),
            "error_type": "TotalTimeoutExceeded",
        }
        return None
    try:
        conn = self._make_connection()
        conn.request("POST", self._request_path(), payload, headers)
        # ... parse response ...
        break
    except Exception as e:
        error_type = type(e).__name__
        is_timeout = isinstance(e, (TimeoutError, socket.timeout))
        if attempt < self.n_trial:
            if is_timeout and attempt_elapsed >= self.request_timeout_s:
                time.sleep(0)
            else:
                time.sleep(min(2 ** attempt, 16))  # Exponential backoff, capped at 16s
        continue
```

### Pattern 4: Infinite Retry (Local LLM API)

Local LLM calls retry forever, catching all exceptions:

```python
# eoh/src/eoh/llm/api_local_llm.py:20-41
def get_response(self, content: str) -> str:
    start_time = time.monotonic()
    attempts = 0
    while True:
        try:
            attempts += 1
            response = self._do_request(content)
            self.last_request_meta = {
                "status": "success",
                "attempts": attempts,
                "elapsed_ms": round((time.monotonic() - start_time) * 1000, 3),
                "error_type": None,
            }
            return response
        except Exception as exc:
            self.last_request_meta = {
                "status": "llm_error",
                "attempts": attempts,
                "elapsed_ms": round((time.monotonic() - start_time) * 1000, 3),
                "error_type": type(exc).__name__,
            }
            continue
```

### Pattern 5: Early exit() on Misconfiguration

LLM configuration errors terminate the process immediately:

```python
# eoh/src/eoh/llm/interface_LLM.py:40-46
if self.api_key == None or self.api_endpoint == None:
    print(">> Stop with wrong API setting: ...")
    exit()

res = self.interface_llm.get_response("1+1=?")
if res == None:
    print(">> Error in LLM API, wrong endpoint, key, model or local deployment!")
    exit()
```

### Pattern 6: LLM Response Parsing Retry with Budget Timeout

When regex fails to extract algorithm/code from LLM response, retry up to 4 times with a total timeout budget:

```python
# eoh/src/eoh/methods/eoh/eoh_evolution.py:192-251
def _get_alg(self, prompt_content):
    start_time = time.monotonic()
    prompt_attempts = 0

    while prompt_attempts < 4:
        elapsed_s = time.monotonic() - start_time
        if elapsed_s >= self.llm_total_timeout_s:
            self._set_last_generation_meta(
                status="llm_timeout",
                error_type="TotalPhaseTimeoutExceeded",
            )
            raise TimeoutError("LLM phase exceeded total timeout budget.")

        prompt_attempts += 1
        response = self.interface_llm.get_response(prompt_content)
        algorithm, code = self._extract_algorithm_and_code(response)

        if len(algorithm) > 0 and len(code) > 0:
            self._set_last_generation_meta(status="success", ...)
            return [code_all, algorithm]

    # All retries exhausted
    self._set_last_generation_meta(status="parse_error", ...)
    raise ValueError(detail)
```

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

### Pattern 8: Subprocess-Based Evaluation with Timeout

Individual evaluations use `multiprocessing.Process` + `Queue` for per-task isolation and timeout:

```python
# eoh/src/eoh/methods/eoh/eoh_interface_EC.py:128-185
def _evaluate_with_timeout(self, code):
    start_time = time.monotonic()
    use_details = hasattr(self.interface_eval, "evaluate_with_details")
    start_methods = multiprocessing.get_all_start_methods()
    ctx_name = "fork" if "fork" in start_methods else start_methods[0]
    ctx = multiprocessing.get_context(ctx_name)
    result_queue = ctx.Queue()
    process = ctx.Process(
        target=_evaluate_worker,
        args=(self.interface_eval, code, use_details, result_queue),
    )
    process.start()
    process.join(timeout=self.timeout)

    if process.is_alive():
        process.terminate()
        process.join()
        return None, None, {"status": "eval_timeout", ...}

    if result_queue.empty():
        return None, None, {"status": "eval_error", ...}

    status, fitness, other_inf, detail = result_queue.get()
    # ...
```

### Pattern 9: Parallel Execution Budget Timeout

Joblib parallel execution has its own timeout as the outermost boundary:

```python
# eoh/src/eoh/methods/eoh/eoh_interface_EC.py:435-457
def get_algorithm(self, pop, operator, generation=0):
    try:
        results = Parallel(n_jobs=self.n_p, timeout=self.parallel_timeout)(
            delayed(self.get_offspring)(pop, operator, generation, offspring_index)
            for offspring_index in range(self.pop_size)
        )
    except Exception as e:
        print("Parallel time out .")
        self._write_timeout_record(
            self._diagnostic_record(
                root_cause="worker_budget_timeout",
                event="worker_budget_timeout",
            )
        )
```

The parallel timeout is computed as: `self.parallel_timeout = self.llm_total_timeout_s + self.timeout + 15`

```python
# eoh/src/eoh/methods/eoh/eoh_interface_EC.py:84
self.parallel_timeout = self.llm_total_timeout_s + self.timeout + 15
```

Worker submission has a serialization boundary before any timeout logic runs. Objects captured by `Parallel(...)` must remain pickle-safe for the selected backend. In particular, remote LLM clients must not retain live sockets or HTTP connection objects in the serialized state. The current `InterfaceAPI` implementation drops `_connection` during pickling so each worker can lazily rebuild its own connection after deserialization.

---

## Three-Layer Timeout System

EoH implements a three-layer timeout hierarchy to bound the time spent on any single offspring generation attempt. Each layer is nested inside the next.

### Layer 1: LLM Request Timeout (`llm_request_timeout_s`)

**Scope**: Single HTTP request to the LLM API.

**Default**: 30 seconds (configured via `Paras.llm_request_timeout_s`).

**Implementation**: Set as `timeout=` parameter on `http.client.HTTPSConnection` / `HTTPConnection`:

```python
# eoh/src/eoh/llm/api_general.py:113-118
def _make_connection(self):
    parsed = self._parsed_endpoint()
    host = parsed.netloc or parsed.path
    if parsed.scheme == "http":
        return http.client.HTTPConnection(host, timeout=self.request_timeout_s)
    return http.client.HTTPSConnection(host, timeout=self.request_timeout_s)
```

**On timeout**: `TimeoutError` / `socket.timeout` is caught in the retry loop. The request is retried (up to 5 attempts) with exponential backoff.

### Layer 2: LLM Total Phase Timeout (`llm_total_timeout_s`)

**Scope**: The entire LLM phase for one offspring, including all retry attempts for both API calls and response parsing.

**Default**: 90 seconds (configured via `Paras.llm_total_timeout_s`). Must be >= `llm_request_timeout_s`.

**Implementation**: Enforced in two places:

1. **In `InterfaceAPI.get_response()`** -- checks elapsed time before each retry attempt:

```python
# eoh/src/eoh/llm/api_general.py:52-61
for attempt in range(1, self.n_trial + 1):
    elapsed_before_attempt = time.monotonic() - start_time
    if elapsed_before_attempt >= self.total_timeout_s:
        self.last_request_meta = {
            "status": "llm_timeout",
            "error_type": "TotalTimeoutExceeded",
        }
        return None
```

2. **In `Evolution._get_alg()`** -- checks elapsed time before each parse-retry:

```python
# eoh/src/eoh/methods/eoh/eoh_evolution.py:197-208
while prompt_attempts < 4:
    elapsed_s = time.monotonic() - start_time
    if elapsed_s >= self.llm_total_timeout_s:
        self._set_last_generation_meta(
            status="llm_timeout",
            error_type="TotalPhaseTimeoutExceeded",
        )
        raise TimeoutError("LLM phase exceeded total timeout budget.")
```

**On timeout**: `TimeoutError` is raised, caught by `get_offspring()`, and recorded as `root_cause="llm_timeout"` in diagnostics.

### Layer 3: Evaluation Subprocess Timeout (`eva_timeout`)

**Scope**: Single evaluation of LLM-generated code in an isolated subprocess.

**Default**: 30 seconds (configured via `Paras.eva_timeout`). Auto-set to 20s for `bp_online` and `tsp_construct`.

**Implementation**: `multiprocessing.Process.join(timeout=self.timeout)` followed by `terminate()` if still alive:

```python
# eoh/src/eoh/methods/eoh/eoh_interface_EC.py:147-156
process.join(timeout=self.timeout)

if process.is_alive():
    process.terminate()
    process.join()
    return None, None, {
        "status": "eval_timeout",
        "elapsed_ms": round((time.monotonic() - start_time) * 1000, 3),
        "detail": f"Evaluation exceeded timeout={self.timeout}s and was terminated.",
    }
```

**On timeout**: Process is terminated, fitness is `None`, and `eval_timeout` is recorded in diagnostics. When `get_offspring()` later maps the failure into a diagnostics `root_cause`, this evaluation status must override any earlier `llm_status="success"`.

### Outer Boundary: Parallel Worker Budget (`parallel_timeout`)

**Scope**: All workers in a `joblib.Parallel` batch for one operator invocation.

**Formula**: `parallel_timeout = llm_total_timeout_s + eva_timeout + 15` (15s safety margin).

```python
# eoh/src/eoh/methods/eoh/eoh_interface_EC.py:84
self.parallel_timeout = self.llm_total_timeout_s + self.timeout + 15
```

**On timeout**: Joblib raises an exception, caught in `get_algorithm()`. Partial results are retained. Recorded as `root_cause="worker_budget_timeout"`.

### Timeout Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  Parallel Worker Budget (llm_total + eval + 15s)            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Per-Offspring (get_offspring)                         │  │
│  │  ┌─────────────────────────┐  ┌────────────────────┐  │  │
│  │  │ LLM Phase               │  │ Eval Phase          │  │  │
│  │  │ (llm_total_timeout_s)   │  │ (eva_timeout)       │  │  │
│  │  │ ┌─────────────────────┐ │  │ ┌────────────────┐  │  │  │
│  │  │ │ Single Request      │ │  │ │ Subprocess     │  │  │  │
│  │  │ │ (request_timeout_s) │ │  │ │ Process.join() │  │  │  │
│  │  │ │ x 5 retries         │ │  │ │ + terminate()  │  │  │  │
│  │  │ └─────────────────────┘ │  │ └────────────────┘  │  │  │
│  │  │ x 4 parse retries      │  │                      │  │  │
│  │  └─────────────────────────┘  └────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│  x pop_size workers                                         │
└─────────────────────────────────────────────────────────────┘
```

### Default Timeout Values

| Parameter | Default | Configured in |
|-----------|---------|---------------|
| `llm_request_timeout_s` | 30s | `Paras.__init__()` line 29 |
| `llm_total_timeout_s` | 90s | `Paras.__init__()` line 30 |
| `eva_timeout` | 30s (20s for bp_online/tsp_construct) | `Paras.__init__()` line 51, `set_evaluation()` line 108 |
| `parallel_timeout` | Computed: `llm_total + eval + 15` | `InterfaceEC.__init__()` line 84 |

---

## Timeout Diagnostics System

When `exp_timeout_diagnostics=True` is set, every offspring attempt writes a structured JSONL record via `_diagnostic_record()` and `_write_timeout_record()`.

### Diagnostic Record Structure

```python
# eoh/src/eoh/methods/eoh/eoh_interface_EC.py:93-126
def _diagnostic_record(self, *, generation, operator, offspring_index, root_cause,
                       llm_status=None, llm_elapsed_ms=None, llm_prompt_attempts=None,
                       llm_api_attempts=None, eval_status=None, eval_elapsed_ms=None,
                       total_elapsed_ms=None, detail=None, event="offspring_result"):
    return {
        "event": event,                    # "offspring_result" or "worker_budget_timeout"
        "generation": generation,          # int: which generation
        "operator": operator,              # str: "i1", "e1", "e2", "m1", "m2", "m3"
        "offspring_index": offspring_index, # int or None (None for budget timeout)
        "root_cause": root_cause,          # str: see root_cause taxonomy below
        "run_id": self.run_id,             # str or None
        "llm_status": llm_status,          # "success", "llm_timeout", "llm_error", "parse_error"
        "llm_elapsed_ms": llm_elapsed_ms,  # float, rounded to 3 decimals
        "llm_prompt_attempts": ...,        # int: number of prompt+parse attempts
        "llm_api_attempts": ...,           # int: number of HTTP attempts in last request
        "eval_status": eval_status,        # "success", "eval_timeout", "eval_error"
        "eval_elapsed_ms": eval_elapsed_ms,# float, rounded to 3 decimals
        "total_elapsed_ms": ...,           # float: wall-clock time for entire offspring
        "detail": detail,                  # str: human-readable error context
        "phase": "offspring" or "worker",  # derived from event type
    }
```

### Root Cause Taxonomy

| Root Cause | Meaning |
|-----------|---------|
| `success` | LLM + eval both succeeded |
| `llm_timeout` | LLM phase hit total timeout budget |
| `parse_error` | LLM returned responses but regex extraction failed on all retries |
| `eval_timeout` | Evaluation subprocess exceeded `eva_timeout` |
| `eval_error` | Evaluation subprocess crashed or returned None |
| `worker_budget_timeout` | Entire joblib parallel batch exceeded `parallel_timeout` |
| `unexpected_error` | Catch-all for errors not in the above categories |

### Where diagnostic records are emitted

`InterfaceEC.get_offspring()` writes a record on both the success path and the failure path. That is the main guarantee that keeps timeout postmortems complete.

Success path:

```python
# eoh/src/eoh/methods/eoh/eoh_interface_EC.py:362-383
fitness, other_inf, eval_meta = self._evaluate_with_timeout(code)
if eval_meta.get("status") != "success":
    raise RuntimeError(eval_meta.get("detail") or "Evaluation phase failed.")

offspring['objective'] = float(np.round(float(fitness), 5))
offspring['other_inf'] = other_inf

self._write_timeout_record(
    self._diagnostic_record(
        generation=generation,
        operator=operator,
        offspring_index=offspring_index,
        root_cause="success",
        llm_status=llm_meta.get("status"),
        eval_status=eval_meta.get("status"),
    )
)
```

Failure path:

```python
# eoh/src/eoh/methods/eoh/eoh_interface_EC.py:385-412
except Exception as e:
    if not llm_meta:
        llm_meta = dict(getattr(self.evol, "last_generation_meta", {}))
    eval_status = eval_meta.get("status")
    llm_status = llm_meta.get("status")
    if eval_status and eval_status != "success":
        root_cause = eval_status
    elif llm_status and llm_status != "success":
        root_cause = llm_status
    else:
        root_cause = "unexpected_error"
    if root_cause not in {"llm_timeout", "parse_error", "llm_error", "eval_timeout", "eval_error"}:
        root_cause = "unexpected_error"

    self._write_timeout_record(
        self._diagnostic_record(
            generation=generation,
            operator=operator,
            offspring_index=offspring_index,
            root_cause=root_cause,
            detail=eval_meta.get("detail") or llm_meta.get("detail") or f"{type(e).__name__}: {e}",
        )
    )

    offspring = _empty_offspring()
```

### JSONL Write Mechanism

```python
# eoh/src/eoh/utils/timeout_diagnostics.py:22-37
def write_timeout_record(path, record, enabled):
    if not enabled or not path:
        return
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, default=str, sort_keys=True)
    with output_path.open("a", encoding="utf-8") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)  # File locking for parallel writes
        handle.write(line + "\n")
        handle.flush()
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
```

### End-of-Run Summary

At the end of evolution, `EOH.run()` prints a summary:

```python
# eoh/src/eoh/methods/eoh/eoh.py:196-203
if self.timeout_diagnostics_enabled and self.timeout_diagnostics_path:
    summary = interface_ec.timeout_summary()
    print("- Timeout diagnostics summary -")
    print(
        " success={success} llm_timeout={llm_timeout} eval_timeout={eval_timeout} "
        "parse_error={parse_error} worker_budget_timeout={worker_budget_timeout}".format(**summary)
    )
```

The summary is computed by `summarize_timeout_records()`:

```python
# eoh/src/eoh/utils/timeout_diagnostics.py:40-66
SUMMARY_ROOT_CAUSES = (
    "success", "llm_timeout", "eval_timeout", "parse_error", "worker_budget_timeout",
)

def summarize_timeout_records(path):
    # Reads JSONL file, counts root_cause for "offspring_result" events
    # and "worker_budget_timeout" events
    return {key: int(counter.get(key, 0)) for key in SUMMARY_ROOT_CAUSES}
```

---

## `last_request_meta` / `last_generation_meta` Tracking

Each layer records structured metadata about its most recent operation for upstream consumers.

### `InterfaceAPI.last_request_meta`

Set after every `get_response()` call:

```python
# eoh/src/eoh/llm/api_general.py:25-30
self.last_request_meta = {
    "status": "not_started",    # "success", "llm_timeout", "llm_error"
    "attempts": 0,              # int: number of HTTP attempts made
    "elapsed_ms": 0.0,          # float: total wall-clock time in milliseconds
    "error_type": None,         # str: exception class name or "TotalTimeoutExceeded"
}
```

### `InterfaceLLM.last_request_meta`

Proxied from the underlying API implementation after each call:

```python
# eoh/src/eoh/llm/interface_LLM.py:81-84
def get_response(self, prompt_content):
    response = self.interface_llm.get_response(prompt_content)
    self.last_request_meta = dict(getattr(self.interface_llm, "last_request_meta", self.last_request_meta))
    return response
```

### `Evolution.last_generation_meta`

Set after each `_get_alg()` call (covers the full prompt+parse cycle):

```python
# eoh/src/eoh/methods/eoh/eoh_evolution.py:34-41
self.last_generation_meta = {
    "status": "not_started",     # "success", "llm_timeout", "parse_error", "llm_error"
    "elapsed_ms": 0.0,           # float: total LLM phase time
    "prompt_attempts": 0,        # int: number of prompt+parse iterations
    "api_attempts": 0,           # int: HTTP attempts from the last API call
    "error_type": None,          # str: exception class name
}
```

---

## Error Propagation Summary

| Layer | Pattern | On Error |
|-------|---------|----------|
| LLM HTTP Request | Per-request timeout + 5 retries | Exponential backoff, sets `last_request_meta` |
| LLM Total Phase | Budget timeout across all retries | `TimeoutError` raised, `last_generation_meta` set |
| Response Parsing | Retry up to 4 times within budget | `ValueError` raised with `parse_error` status |
| Evaluation Subprocess | `Process.join(timeout)` + terminate | Returns `None`, `eval_meta` with status |
| Offspring Creation | Catch-all wrapping LLM+eval | Returns null offspring dict, writes diagnostic |
| Parallel Execution | Joblib timeout (LLM + eval + 15s) | Partial results retained, budget timeout recorded |
| Seed Init | Catch-all per seed | `exit()` (fatal) |
| Population Management | Filter | Removes `None` objectives, deduplicates |
| LLM Config | Validation | `exit()` with descriptive message |
| Main Loop | None | No error handling (relies on lower layers) |

---

## Conventions for New Code

1. **Evaluate methods**: Always wrap in try/except, return `None` on failure
2. **LLM calls**: Use bounded retry (don't use bare `except:` with infinite retry)
3. **Configuration errors**: Use `exit()` with descriptive print message (prefix `>> Stop with ...` or `>> Error in ...`)
4. **Parallel execution**: Always set timeouts on both joblib and subprocess layers
5. **Warnings**: Suppress with `warnings.catch_warnings()` context manager inside evaluate methods
6. **Never raise custom exceptions** -- the framework expects `None` as the error signal
7. **Record diagnostics**: When implementing new evaluation paths, write `_diagnostic_record()` entries on both success and failure
8. **Track meta**: Set `last_request_meta` / `last_generation_meta` after every LLM interaction for upstream diagnostic consumers

---

## Common Mistakes

1. **Forgetting to handle `None` fitness**: When processing evaluation results, always check for `None` before numeric operations
2. **Bare `except:` with infinite retry**: Only acceptable for local LLM (where server restart is expected). Use bounded retries for everything else
3. **Not setting timeouts**: Evaluation of LLM-generated code can hang forever. Always use subprocess with timeout
4. **Using `== None` instead of `is None`**: The codebase uses `== None` throughout (legacy pattern), but `is None` is preferred for new code
5. **Ignoring `last_request_meta`**: Always propagate meta through the chain so `get_offspring()` can record accurate diagnostics
6. **Not terminating subprocess on timeout**: Always call `process.terminate()` + `process.join()` after a timeout to prevent zombie processes

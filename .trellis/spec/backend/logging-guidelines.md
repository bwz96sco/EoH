# Logging Guidelines

> How runtime output, diagnostics, and lightweight structured logging work in EoH.

---

## Overview

EoH still avoids Python's `logging` module in the core runtime. Human-facing status is emitted through `print()`, while machine-facing postmortem data is written as JSON or JSONL files. The main split is:

- Console: lifecycle banners, operator progress, retry warnings, fatal configuration messages
- Files: `config.json`, per-generation population snapshots, best-individual snapshots, and optional timeout-diagnostics JSONL

That split is visible in the core orchestration path:

```python
# eoh/src/eoh/eoh.py:16-28
print("----------------------------------------- ")
print("---              Start EoH            ---")
print("-----------------------------------------")
createFolders.create_folders(paras.exp_output_path)
print("- output folder created -")
config = {k: v for k, v in vars(paras).items() if k not in _sensitive}
config_path = os.path.join(paras.exp_output_path, "config.json")
with open(config_path, "w") as f:
    json.dump(config, f, default=str, indent=2)
```

---

## Output Mechanism

### Console output

The core package uses `print()` exclusively. There is no log-level system, no formatter, and no centralized logger object.

### Structured diagnostics

Timeout postmortems are the one structured "log-like" stream in the core runtime. When enabled, `InterfaceEC` appends JSONL records through `write_timeout_record()`:

```python
# eoh/src/eoh/methods/eoh/eoh_interface_EC.py:86-91
def _write_timeout_record(self, record):
    write_timeout_record(
        self.timeout_diagnostics_path,
        record,
        self.timeout_diagnostics_enabled,
    )
```

```python
# eoh/src/eoh/utils/timeout_diagnostics.py:22-37
def write_timeout_record(path: str | None, record: dict, enabled: bool) -> None:
    if not enabled or not path:
        return

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, default=str, sort_keys=True)
    with output_path.open("a", encoding="utf-8") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(line + "\n")
        handle.flush()
```

---

## Output Categories

### Category A: Lifecycle banners

```python
# eoh/src/eoh/eoh.py:16-21
print("----------------------------------------- ")
print("---              Start EoH            ---")
print("-----------------------------------------")
createFolders.create_folders(paras.exp_output_path)
print("- output folder created -")
```

```python
# eoh/src/eoh/eoh.py:53-56
print("> End of Evolution! ")
print("----------------------------------------- ")
print("---     EoH successfully finished !   ---")
print("-----------------------------------------")
```

### Category B: Initialization status

```python
# eoh/src/eoh/methods/eoh/eoh.py:57-66
self.timeout = paras.eva_timeout
self.llm_request_timeout_s = paras.llm_request_timeout_s
self.llm_total_timeout_s = paras.llm_total_timeout_s
self.timeout_diagnostics_enabled = paras.exp_timeout_diagnostics
self.timeout_diagnostics_path = paras.exp_timeout_diagnostics_path
self.run_id = paras.abr_run_id
print("- EoH parameters loaded -")
```

```python
# eoh/src/eoh/llm/interface_LLM.py:38-52
print("- check LLM API")
if self.llm_use_local:
    print('local llm delopyment is used ...')
else:
    print('remote llm api is used ...')
```

### Category C: Evolutionary progress

Per-operator progress is inline and intentionally compact:

```python
# eoh/src/eoh/methods/eoh/eoh.py:156-165
op = self.operators[i]
print(f" OP: {op}, [{i + 1} / {n_op}] ", end="|")
op_w = self.operator_weights[i]
if (np.random.rand() < op_w):
    parents, offsprings = interface_ec.get_algorithm(population, op, generation=pop + 1)
self.add2pop(population, offsprings)
for off in offsprings:
    print(" Obj: ", off['objective'], end="|")
```

Per-generation summaries print elapsed time plus current objectives:

```python
# eoh/src/eoh/methods/eoh/eoh.py:190-194
print(f"--- {pop + 1} of {self.n_pop} populations finished. Time Cost:  {((time.time()-time_start)/60):.1f} m")
print("Pop Objs: ", end=" ")
for i in range(len(population)):
    print(str(population[i]['objective']) + " ", end="")
print()
```

### Category D: Retry and error messages

Remote API retries distinguish debug and non-debug output:

```python
# eoh/src/eoh/llm/api_general.py:84-102
except Exception as e:
    error_type = type(e).__name__
    is_timeout = isinstance(e, (TimeoutError, socket.timeout))
    self.last_request_meta = {
        "status": "llm_timeout" if is_timeout else "llm_error",
        "attempts": attempt,
        "elapsed_ms": round((time.monotonic() - start_time) * 1000, 3),
        "error_type": error_type,
    }
    if self.debug_mode:
        print(f"Error in API (attempt {attempt}/{self.n_trial}): {e}")
    else:
        print(f"API error (attempt {attempt}/{self.n_trial}): {error_type}: {e}")
```

Common message prefixes in the actual codebase:

- `">> Stop with ..."` for fatal configuration validation, for example `eoh/src/eoh/llm/interface_LLM.py:43-45`
- `">> Error in ..."` for fatal API bootstrap failure, for example `eoh/src/eoh/llm/interface_LLM.py:71-73`
- `"Error: ..."` for recoverable parse/retry diagnostics in debug mode, for example `eoh/src/eoh/methods/eoh/eoh_evolution.py:230-231`
- `"Parallel time out ."` for joblib worker-budget failures, at `eoh/src/eoh/methods/eoh/eoh_interface_EC.py:443-446`
- `"duplicated code, wait 1 second and retrying ... "` for duplicate offspring retries, at `eoh/src/eoh/methods/eoh/eoh_interface_EC.py:330-335`

### Category E: Timeout summary and sink path

When timeout diagnostics are enabled, `EOH.run()` prints a compact end-of-run summary and the JSONL path:

```python
# eoh/src/eoh/methods/eoh/eoh.py:196-203
if self.timeout_diagnostics_enabled and self.timeout_diagnostics_path:
    summary = interface_ec.timeout_summary()
    print("- Timeout diagnostics summary -")
    print(
        " success={success} llm_timeout={llm_timeout} eval_timeout={eval_timeout} "
        "parse_error={parse_error} worker_budget_timeout={worker_budget_timeout}".format(**summary)
    )
    print(f"- Timeout diagnostics log: {self.timeout_diagnostics_path}")
```

In the ABR workflow, that path is derived under the canonical run-local `logs/` tree:

```python
# examples/user_abr/runEoH.py:229-235
run_layout = build_run_layout(repo_root)
output_root = build_eoh_output_root(repo_root, output_name=output_name, run_id=run_layout.run_id)
timeout_diagnostics_path = build_log_path(
    repo_root,
    log_name="timeout_diagnostics",
    run_id=run_layout.run_id,
)
```

---

## Debug Mode (`exp_debug_mode`)

`Paras.exp_debug_mode` defaults to `False` in `eoh/src/eoh/utils/getParas.py:35`.

### What debug mode enables

1. Prompt inspection before each operator request:

```python
# eoh/src/eoh/methods/eoh/eoh_evolution.py:254-269
prompt_content = self.get_prompt_i1()
if self.debug_mode:
    print("\n >>> check prompt for creating algorithm using [ i1 ] : \n", prompt_content)
    print(">>> Press 'Enter' to continue")
    input()
[code_all, algorithm] = self._get_alg(prompt_content)
if self.debug_mode:
    print("\n >>> check designed algorithm: \n", algorithm)
    print("\n >>> check designed code: \n", code_all)
```

The same wrapper pattern is repeated for `e1`, `e2`, `m1`, `m2`, and `m3` in `eoh/src/eoh/methods/eoh/eoh_evolution.py:273-360`.

2. Extra retry detail during parse failures:

```python
# eoh/src/eoh/methods/eoh/eoh_evolution.py:230-231
if self.debug_mode:
    print("Error: algorithm or code not identified, wait 1 seconds and retrying ... ")
```

3. Warning suppression only outside debug mode:

```python
# eoh/src/eoh/methods/eoh/eoh_interface_EC.py:76-77
if not self.debug:
    warnings.filterwarnings("ignore")
```

---

## File-Based Output

### Experiment config snapshot

The runtime writes one sanitized `config.json` at the experiment root:

```python
# eoh/src/eoh/eoh.py:23-28
_sensitive = {"llm_api_key", "llm_local_url"}
config = {k: v for k, v in vars(paras).items() if k not in _sensitive}
config_path = os.path.join(paras.exp_output_path, "config.json")
with open(config_path, "w") as f:
    json.dump(config, f, default=str, indent=2)
```

### Population checkpoints

Per-generation population files remain the primary persisted runtime artifact:

```python
# eoh/src/eoh/methods/eoh/eoh.py:179-187
filename = self.output_path + "/results/pops/population_generation_" + str(pop + 1) + ".json"
with open(filename, 'w') as f:
    json.dump(population, f, indent=5)

filename = self.output_path + "/results/pops_best/population_generation_" + str(pop + 1) + ".json"
with open(filename, 'w') as f:
    json.dump(population[0], f, indent=5)
```

### Timeout diagnostics JSONL

Timeout diagnostics are append-only JSONL records, not pretty-printed JSON arrays. The record shape is defined by `_diagnostic_record()`:

```python
# eoh/src/eoh/methods/eoh/eoh_interface_EC.py:93-126
return {
    "event": event,
    "generation": generation,
    "operator": operator,
    "offspring_index": offspring_index,
    "root_cause": root_cause,
    "run_id": self.run_id,
    "llm_status": llm_status,
    "llm_elapsed_ms": None if llm_elapsed_ms is None else round(float(llm_elapsed_ms), 3),
    "llm_prompt_attempts": llm_prompt_attempts,
    "llm_api_attempts": llm_api_attempts,
    "eval_status": eval_status,
    "eval_elapsed_ms": None if eval_elapsed_ms is None else round(float(eval_elapsed_ms), 3),
    "total_elapsed_ms": None if total_elapsed_ms is None else round(float(total_elapsed_ms), 3),
    "detail": detail,
    "phase": "offspring" if event == "offspring_result" else "worker",
}
```

### In-memory meta snapshots

`last_request_meta` and `last_generation_meta` are not persisted automatically, but they are the structured state that upstream layers consume and then fold into timeout records.

```python
# eoh/src/eoh/llm/interface_LLM.py:68-69,81-84
res = self.interface_llm.get_response("1+1=?")
self.last_request_meta = dict(getattr(self.interface_llm, "last_request_meta", self.last_request_meta))

response = self.interface_llm.get_response(prompt_content)
self.last_request_meta = dict(getattr(self.interface_llm, "last_request_meta", self.last_request_meta))
```

```python
# eoh/src/eoh/methods/eoh/eoh_evolution.py:74-82
def _set_last_generation_meta(self, **kwargs):
    self.last_generation_meta = {
        "status": kwargs.get("status", "unknown"),
        "elapsed_ms": round(float(kwargs.get("elapsed_ms", 0.0)), 3),
        "prompt_attempts": int(kwargs.get("prompt_attempts", 0)),
        "api_attempts": int(kwargs.get("api_attempts", 0)),
        "error_type": kwargs.get("error_type"),
        "detail": kwargs.get("detail"),
    }
```

### Evaluation-side plain text and reports

Legacy evaluation helpers still write plain text result files, for example `examples/bp_online/evaluation/runEval.py:18-19`. Plot and DOCX report generation lives under `eoh/src/eoh/utils/createReport.py` and is not part of the core generation loop.

---

## Conventions for New Code

1. Use `print()` for runtime status instead of introducing `logging`.
2. Keep verbose prompt/code dumps behind `debug_mode`.
3. Preserve the existing fatal-message style: validate early, print a short message, then `exit()`.
4. When adding machine-readable diagnostics, prefer append-only JSONL with stable keys over ad hoc text blobs.
5. Propagate `last_request_meta` and `last_generation_meta` immediately after each LLM call so upstream layers can write accurate timeout records.
6. Keep progress output compact and stable because experiment runners and humans both read it directly.

---

## What Not To Print

- API keys, local URLs, or any other credential material
- Full prompts or generated code outside debug mode
- Exception tracebacks during expected evaluation failures
- One-off per-instance evaluator noise inside hot loops

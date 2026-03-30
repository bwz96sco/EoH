# Cross-Platform Thinking Guide

> **Purpose**: Catch portability risks in EoH scripts, subprocesses, path handling, and LLM endpoint wiring before they become environment-specific bugs.

---

## Why This Matters in EoH

EoH runs untrusted generated code, uses `joblib` and `multiprocessing`, shells out to example runners, and mixes core package code with repo-local experiment wrappers.

The main portability risks are not UI issues. They are:

- process start method differences (`fork` vs `spawn`)
- path resolution from different working directories
- remote endpoint vs local inference URL expectations
- example runners importing external code from `env/`

---

## 1. Multiprocessing and Start Method

The evaluation subprocess path is defined in `eoh/src/eoh/methods/eoh/eoh_interface_EC.py:128-185`.

Key detail:

```python
# eoh/src/eoh/methods/eoh/eoh_interface_EC.py:131-138
start_methods = multiprocessing.get_all_start_methods()
ctx_name = "fork" if "fork" in start_methods else start_methods[0]
ctx = multiprocessing.get_context(ctx_name)
process = ctx.Process(target=_evaluate_worker, args=(self.interface_eval, code, use_details, result_queue))
```

Think before changing this area:

- Linux usually supports `fork`
- Windows is effectively `spawn`-only
- macOS Python defaults changed toward `spawn`, but this code explicitly prefers `fork` when available

Questions:

- Is the problem object picklable if the platform falls back to `spawn`?
- Does the evaluator capture dynamically imported modules or local lambdas?
- Will your new code behave differently if memory is copied (`fork`) versus reconstructed (`spawn`)?

ABR is a good stress case because `ABRProblem` dynamically loads SABR modules from file paths in `examples/user_abr/prob.py:142-174`.

---

## 2. Worker Budget vs Phase Budgets

EoH has nested timeout layers:

- LLM request and total phase budgets in `eoh/src/eoh/llm/api_general.py:22-24` and `eoh/src/eoh/methods/eoh/eoh_evolution.py:32-40`
- evaluation subprocess timeout in `eoh/src/eoh/methods/eoh/eoh_interface_EC.py:147-156`
- parallel worker budget in `eoh/src/eoh/methods/eoh/eoh_interface_EC.py:84-85` and `eoh/src/eoh/methods/eoh/eoh_interface_EC.py:435-459`

If you change one timeout without the others, behavior becomes platform-dependent because slower machines and slower network stacks hit different layers first.

Checklist:

- [ ] `parallel_timeout` still covers `llm_total_timeout_s + eva_timeout + slack`
- [ ] local and remote backends expose compatible retry behavior
- [ ] diagnostics still explain whether the failure was LLM, evaluation, or worker-budget timeout

---

## 3. Path Handling and Working Directory Assumptions

Core EoH mostly uses string paths and `os.path.join`:

- `eoh/src/eoh/utils/getParas.py:97-106`
- `eoh/src/eoh/utils/createFolders.py:3-20`
- `eoh/src/eoh/eoh.py:26-28`

The modern ABR example uses `pathlib.Path` and resolves from `__file__`:

- `.env` loading in `examples/user_abr/runEoH.py:11-18`
- experiment root setup in `examples/user_abr/runEoH.py:217-235`
- cache and temp paths in `examples/user_abr/runEoH.py:280-299`
- evaluation runner path setup in `examples/user_abr/evaluation/runEval.py:16-21`

Portability rules:

- resolve repo-relative files from `Path(__file__).resolve()`, not the caller's shell cwd
- convert `Path` to `str` when passing into legacy `Paras` fields, as ABR does in `examples/user_abr/runEoH.py:315-320`
- do not assume `/` separators or that the process was launched from the repo root

---

## 4. Remote Endpoint vs Local Inference URL

Remote and local LLM adapters do **not** take the same shape of URL.

Remote API path handling:

- `InterfaceAPI._parsed_endpoint()` in `eoh/src/eoh/llm/api_general.py:107-111`
- `InterfaceAPI._request_path()` in `eoh/src/eoh/llm/api_general.py:120-129`

Behavior:

- bare host like `api.deepseek.com` becomes `https://api.deepseek.com`
- `/v1` gets expanded to `/v1/chat/completions`
- existing `/chat/completions` is preserved
- explicit `http://` stays HTTP

Local inference path handling:

- `InterfaceLocalLLM` expects a **full** URL already, for example `http://127.0.0.1:11045/completions`, in `eoh/src/eoh/llm/api_local_llm.py:11-12`

Think before reusing config values between modes:

- a valid remote endpoint may be invalid for local mode
- a valid local URL may be wrong for remote mode because the remote adapter appends `/v1/chat/completions`
- adding a new backend is not just "add a file"; `InterfaceLLM.__init__()` in `eoh/src/eoh/llm/interface_LLM.py:40-65` must learn how to select it

---

## 5. Python Version Features

The repo baseline is Python `>= 3.10`, documented in `.trellis/spec/backend/quality-guidelines.md`, and the newer example code already uses 3.10 syntax:

- union types such as `str | None` in `examples/user_abr/prob.py:72-77`
- generic built-ins such as `list[dict[str, str]]` in `examples/user_abr/runEoH.py:47-49`
- `Path.unlink(missing_ok=True)` in `examples/user_abr/runEoH.py:343-345`

If you write new example or helper code using older compatibility shims, you will drift away from the current style of the actively maintained example paths.

---

## 6. External Environment Imports

ABR pulls code from `env/SABR` by file path, not package install:

- `examples/user_abr/prob.py:80`
- `examples/user_abr/prob.py:142-174`

That means portability depends on repo layout, not just Python dependencies.

Questions:

- Is the external dependency expected to exist under `env/`?
- Are you importing it by absolute path relative to the repo, not relative to the caller's cwd?
- Does the subprocess path see the same files as the parent process?

---

## Cross-Platform Checklist Before Shipping a Script or Backend

- [ ] Path resolution is based on `__file__` or repo root, not shell cwd
- [ ] `multiprocessing` behavior was considered for both `fork`-capable and `spawn`-only platforms
- [ ] Timeout budgets are aligned across request, total LLM phase, evaluation, and joblib worker layers
- [ ] Remote endpoints and local inference URLs are not being treated as the same configuration shape
- [ ] Any external code under `env/` is imported through stable repo-relative paths

**Rule**: In EoH, "cross-platform" usually means process model, path resolution, and endpoint semantics, not UI rendering.

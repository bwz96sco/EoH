# Extending EoH

> **Purpose**: One place to check the actual EoH extension seams before adding a new problem, method, operator, strategy, or LLM backend.

---

## The Runtime Entry Chain You Are Extending

The concrete EoH orchestration path is:

```text
Paras.set_paras()
  -> EVOL.run()
    -> Probs(self.paras).get_problem()
    -> Methods(self.paras, problem).get_method()
      -> EOH.run() / AEL.run() / LS.run()
        -> InterfaceEC.get_algorithm(population, op)
          -> Evolution._get_alg(prompt_content)
            -> InterfaceLLM.get_response(prompt_content)
          -> problem.evaluate(code_string) or problem.evaluate_with_details(code_string)
        -> population_management(population, size_act)
        -> write JSON populations
```

Relevant source points:

- `eoh/src/eoh/utils/getParas.py:116-133`
- `eoh/src/eoh/eoh.py:41-51`
- `eoh/src/eoh/problems/problems.py:6-25`
- `eoh/src/eoh/methods/methods.py:6-51`
- `eoh/src/eoh/methods/eoh/eoh.py:82-203`
- `eoh/src/eoh/methods/eoh/eoh_interface_EC.py:274-470`
- `eoh/src/eoh/methods/eoh/eoh_evolution.py:7-320`

GitNexus currently exposes the same core areas as separate modules such as `Eoh`, `Llm`, `Ael`, `Localsearch`, `Bp_online`, `Tsp_greedy`, and `User_abr`. Those are the boundaries this guide follows.

---

## Extension Point Matrix

| You want to add | Implement here first | Register here | Working example |
|--------------------|----------------------|---------------|-----------------|
| New built-in problem | mirror `bp_online` or `tsp_greedy` under `eoh/src/eoh/problems/optimization/` or `eoh/src/eoh/problems/machinelearning/` | `eoh/src/eoh/problems/problems.py:11-20` | `bp_online`, `tsp_greedy` |
| New user-defined problem | mirror the `examples/user_abr/` layout: `prob.py`, `prompts.py`, `runEoH.py` | no built-in registry required if you pass the object directly | `examples/user_abr/` |
| New evolution method | add a new package beside `eoh/`, `ael/`, and `localsearch/` under `eoh/src/eoh/methods/` | `eoh/src/eoh/methods/methods.py:32-49` | `eoh/`, `ael/`, `localsearch/` |
| New EC operator | method-specific `*_evolution.py` and `*_interface_EC.py` | `Paras.set_ec()`, prompt builder, dispatch branch | `i1`, `e1`, `e2`, `m1`, `m2`, `m3` |
| New selection strategy | add a module under `eoh/src/eoh/methods/selection/` | import + branch in `eoh/src/eoh/methods/methods.py:2-19` | `prob_rank.py` |
| New management strategy | add a module under `eoh/src/eoh/methods/management/` | import + branch in `eoh/src/eoh/methods/methods.py:3-29` | `pop_greedy.py`, `ls_sa.py` |
| New LLM backend | add a module under `eoh/src/eoh/llm/` | selection logic in `eoh/src/eoh/llm/interface_LLM.py:40-65` | `api_general.py`, `api_local_llm.py` |

---

## 1. Add a New Problem Domain

### Fastest Iteration Path: User-Defined Problem Object

Use the ABR pattern when you are still iterating on the problem contract.

Step-by-step:

1. Copy the `examples/user_abr/prompts.py` structure into a new `prompts.py` with a `GetPrompts` class implementing:
   - `get_task()`
   - `get_func_name()`
   - `get_func_inputs()`
   - `get_func_outputs()`
   - `get_inout_inf()`
   - `get_other_inf()`
2. Copy the `examples/user_abr/prob.py` structure into a new `prob.py` with:
   - `self.prompts = GetPrompts()`
   - `evaluate(code_string) -> float | None`
   - optional `evaluate_with_details(code_string) -> tuple[float | None, str | None]`
3. In `runEoH.py`, instantiate the problem object and pass it through `Paras.set_paras(problem=problem, method="eoh")` plus the rest of the run settings.

Real example:

- `examples/user_abr/prob.py:72-139` sets `self.prompts`
- `examples/user_abr/prob.py:347-367` implements `evaluate_with_details()` and `evaluate()`
- `examples/user_abr/runEoH.py:300-337` passes `problem=problem` into `paras.set_paras(problem=problem, method="eoh", ec_operators=["e1", "e2", "m1", "m2", "m3"])` and adds the remaining timeout, output, and LLM fields in the same call
- `Probs.__init__()` accepts non-string problems directly in `eoh/src/eoh/problems/problems.py:8-10`

### Built-In Problem Path

Promote the problem into `eoh/src/eoh/problems/` only when you want a stable string registration.

Step-by-step:

1. Add a package beside `bp_online` or `tsp_greedy` under `eoh/src/eoh/problems/optimization/`, or beside `L_AutoDA` under `eoh/src/eoh/problems/machinelearning/`.
2. Implement a problem class that sets `self.prompts` and exposes `evaluate(code_string)`.
3. Add a branch in `Probs.__init__()` in `eoh/src/eoh/problems/problems.py:11-20`.
4. Add or update an example runner that sets a concrete string such as `problem="bp_online"` or `problem="tsp_construct"`.

Built-in references:

- `eoh/src/eoh/problems/optimization/bp_online/run.py:9-125`
- `eoh/src/eoh/problems/optimization/tsp_greedy/run.py:9-135`
- `examples/bp_online/runEoH.py:13-22`
- `examples/tsp_construct/runEoH.py:8-17`

Checklist:

- [ ] `self.prompts` exists
- [ ] evaluator returns `None` on failure
- [ ] problem can be reached either by string registration or by direct object injection

---

## 2. Add a New Evolution Method

The method registry resolves strings in `eoh/src/eoh/methods/methods.py:32-49`.

Current constructor shape:

Current constructor signature: `def __init__(self, paras, problem, select, manage, **kwargs):`

Examples:

- `EOH` in `eoh/src/eoh/methods/eoh/eoh.py:11-69`
- `AEL` in `eoh/src/eoh/methods/ael/ael.py:11-61`
- `LS` in `eoh/src/eoh/methods/localsearch/ls.py:11-60`

Step-by-step:

1. Create a new package beside `eoh/`, `ael/`, and `localsearch/` under `eoh/src/eoh/methods/`.
2. Add the main class file with the constructor above and a `run()` method.
3. Add the method-specific EC bridge file, following the `eoh_interface_EC.py`, `ael_interface_EC.py`, or `ls_interface_EC.py` pattern.
4. Add the prompt builder / evolution file, following the `eoh_evolution.py`, `ael_evolution.py`, or `ls_evolution.py` pattern.
5. Register the method string in `Methods.get_method()`.
6. Update `Paras.set_ec()` if the new method has different default operators or management.

Questions to answer before coding:

- Can you reuse `EOH` loop structure directly, or is this actually just a new operator set?
- Does the method need feedback-guided mutation like ABR `m1`?
- Does it need a different management signature, like `LS`?

---

## 3. Add a New EC Operator

In the EOH path, an operator is only real when three layers agree on its name.

Current wiring:

- default operator list: `eoh/src/eoh/utils/getParas.py:76-87`
- operator dispatch: `eoh/src/eoh/methods/eoh/eoh_interface_EC.py:281-300`
- prompt builders: `eoh/src/eoh/methods/eoh/eoh_evolution.py:84-189`
- operator wrapper methods: `eoh/src/eoh/methods/eoh/eoh_evolution.py:254-320`

Step-by-step:

1. Decide the operator string, for example `"m4"`.
2. Add it to the default operator list in `Paras.set_ec()` if it should run by default.
3. Add a prompt builder such as `get_prompt_m4(parent)` or `get_prompt_m4(parents)`.
4. Add a wrapper such as `m4(parent)` that calls `_get_alg(prompt_content)`.
5. Add a dispatch branch in `InterfaceEC._get_alg()`.
6. Update any example runner that explicitly sets `ec_operators`, for example `examples/user_abr/runEoH.py:309-321`.

If the operator depends on new evaluator feedback or state fields, stop and also read `cross-layer-thinking-guide.md`.

---

## 4. Add a New Selection Strategy

Selection strategies are imported as modules in `eoh/src/eoh/methods/methods.py:2` and then called through `self.select.parent_selection(pop, self.m)`.

Required function:

Required function signature: `def parent_selection(pop, m):`

Reference implementation:

- `eoh/src/eoh/methods/selection/prob_rank.py:2-6`

Step-by-step:

1. Add a new module under `eoh/src/eoh/methods/selection/`.
2. Implement `parent_selection(pop, m)`.
3. Import the module in `eoh/src/eoh/methods/methods.py:2`.
4. Add a new `paras.selection == "prob_rank"`-style branch in `Methods.__init__()` using the exact string your runner will pass.

Checklist:

- [ ] returns exactly `m` parents
- [ ] works with individuals shaped like `{"algorithm", "code", "objective", "other_inf"}`
- [ ] does not assume a specific method implementation

---

## 5. Add a New Management Strategy

Management strategies look similar, but they do **not** share one signature across all methods.

Current signatures:

- population-style methods: `population_management(pop, size)` in `eoh/src/eoh/methods/management/pop_greedy.py:3-16`
- local-search style methods: `population_management(population, new, temperature)` in `eoh/src/eoh/methods/management/ls_sa.py:9-15`

Call sites:

- `EOH` uses `(population, size_act)` in `eoh/src/eoh/methods/eoh/eoh.py:174-175`
- `AEL` uses `(population, size_act)` in `eoh/src/eoh/methods/ael/ael.py:150-151`
- `LS` uses `(population, offsprings[0], temperature)` in `eoh/src/eoh/methods/localsearch/ls.py:140-143`

Step-by-step:

1. Decide which caller contract you are targeting.
2. Add a new module under `eoh/src/eoh/methods/management/`.
3. Implement the matching `population_management(pop, size)` or `population_management(population, new, temperature)` signature.
4. Import the module in `eoh/src/eoh/methods/methods.py:3`.
5. Add a new `paras.management == "pop_greedy"`-style branch in `Methods.__init__()` using the exact string your runner will pass.

Do not assume a management module written for `EOH` is safe to plug into `LS`.

---

## 6. Add a New LLM Backend

Current backend split:

- remote OpenAI-compatible path: `eoh/src/eoh/llm/api_general.py:8-129`
- local inference server path: `eoh/src/eoh/llm/api_local_llm.py:7-63`
- backend selection wrapper: `eoh/src/eoh/llm/interface_LLM.py:5-85`

Important constraint:

`InterfaceLLM.__init__()` does an immediate health check with `self.interface_llm.get_response("1+1=?")` in `eoh/src/eoh/llm/interface_LLM.py:68-73`.

Step-by-step:

1. Add a new adapter class with `get_response(prompt_content)` and `last_request_meta`.
2. Decide how it will be selected. Today the wrapper only distinguishes `llm_use_local` boolean mode.
3. Wire the selection branch into `InterfaceLLM.__init__()`.
4. Normalize endpoint expectations:
   - remote adapters can accept bare hosts because `InterfaceAPI` normalizes them
   - local adapters usually expect a full URL including path
5. Confirm the constructor health check is valid for the new backend.

Anti-pattern:

- adding a new file under `eoh/src/eoh/llm/` without changing `InterfaceLLM` means the backend is unreachable

---

## Registration Checklist

- [ ] `Paras` knows the new config or operator default
- [ ] `Methods` or `Probs` can resolve the new string, unless you are using direct object injection
- [ ] the example runner sets the same key names that `Paras` expects
- [ ] prompt getters and evaluator function name still match
- [ ] failure behavior still converges on `None` fitness or null offspring, not an uncaught custom path

---

## Verification Procedure

For a new user-defined problem or prompt contract:

```bash
uv run python examples/user_abr/smoke_test.py
uv run python examples/user_abr/runEoH.py
uv run python examples/user_abr/evaluation/runEval.py
```

For a built-in problem or method change, mirror the built-in runner pattern:

```bash
uv run python examples/bp_online/runEoH.py
uv run python examples/tsp_construct/runEoH.py
```

For debugging a new extension, start with the simplest runner settings already present in the repo:

- single-process / small-pop debug flow in `examples/bp_online/runEoH.py:8-22`
- direct problem-object injection flow in `examples/user_abr/runEoH.py:300-337`

**Rule**: In EoH, adding the implementation file is only half the work. The real task is keeping the registry, prompt contract, evaluator, and runner synchronized.

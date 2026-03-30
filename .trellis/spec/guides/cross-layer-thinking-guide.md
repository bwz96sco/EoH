# Cross-Layer Thinking Guide

> **Purpose**: Trace how a change moves through EoH before editing one layer in isolation.

---

## The Real EoH Layer Map

EoH is a backend-only Python framework, but it still has clear runtime layers:

| Layer | Main files | What flows through it |
|-------|------------|-----------------------|
| Config | `eoh/src/eoh/utils/getParas.py:7-133` | method names, problem object / string, operator list, timeouts, output paths |
| Orchestration | `eoh/src/eoh/eoh.py:14-51` | `Paras` into resolved problem and method |
| Registries | `eoh/src/eoh/problems/problems.py:6-25`, `eoh/src/eoh/methods/methods.py:6-51` | string names to concrete problem / method / strategy modules |
| Method loop | `eoh/src/eoh/methods/eoh/eoh.py:82-203` | population lifecycle, operator scheduling, persistence |
| Prompt + LLM bridge | `eoh/src/eoh/methods/eoh/eoh_interface_EC.py:274-470`, `eoh/src/eoh/methods/eoh/eoh_evolution.py:7-320`, `eoh/src/eoh/llm/interface_LLM.py:5-85`, `eoh/src/eoh/llm/api_general.py:32-129` | parent selection, prompt generation, LLM response parsing, retries |
| Evaluation | built-ins in `eoh/src/eoh/problems/optimization/*/run.py`, user problems such as `examples/user_abr/prob.py:72-367` | `code_string` to fitness / feedback |
| Persistence and experiments | `eoh/src/eoh/utils/createFolders.py:3-20`, `eoh/src/eoh/eoh.py:19-28`, `examples/user_abr/runEoH.py:223-341` | config snapshots, populations, seed cache, experiment-specific output roots |

GitNexus currently groups the same runtime areas into clusters such as `Eoh`, `Llm`, `Ael`, `Localsearch`, `Bp_online`, `Tsp_greedy`, and `User_abr`, so those are the boundaries to keep synchronized.

---

## The Main Execution Chain

For the standard EoH path, the concrete call chain is:

```text
Paras.set_paras()
  -> EVOL.run()
    -> Probs(self.paras).get_problem()
    -> Methods(self.paras, problem).get_method()
      -> EOH.run()
        -> InterfaceEC.get_algorithm(population, op)
          -> InterfaceEC.get_offspring(pop, operator, generation, offspring_index)
            -> Evolution._get_alg(prompt_content)
              -> InterfaceLLM.get_response(prompt_content)
                -> InterfaceAPI.get_response(prompt_content)
            -> InterfaceEC._evaluate_with_timeout(code)
              -> problem.evaluate(code_string) or problem.evaluate_with_details(code_string)
        -> population_management(population, size_act)
        -> write JSON populations
```

Relevant locations:

- `Paras.set_paras()` in `eoh/src/eoh/utils/getParas.py:116-133`
- `EVOL.run()` in `eoh/src/eoh/eoh.py:41-51`
- `EOH.run()` in `eoh/src/eoh/methods/eoh/eoh.py:82-203`
- `InterfaceEC.get_offspring()` in `eoh/src/eoh/methods/eoh/eoh_interface_EC.py:304-415`
- `Evolution._get_alg()` in `eoh/src/eoh/methods/eoh/eoh_evolution.py:192-251`
- `ABRProblem.evaluate_with_details()` in `examples/user_abr/prob.py:347-367`

---

## Boundary Checklists

### 1. Config -> Registry Boundary

Check this whenever you add a method name, problem name, operator string, or timeout.

Files to inspect together:

- `eoh/src/eoh/utils/getParas.py:62-95`
- `eoh/src/eoh/problems/problems.py:6-25`
- `eoh/src/eoh/methods/methods.py:6-51`
- the example runner that sets the field, for example `examples/user_abr/runEoH.py:300-334`

Questions:

- Is the value a string-based built-in registration or a direct problem object?
- Does the defaulting logic in `set_ec()` know about the new method?
- Does the runner pass the same key name that `Paras` expects?
- Will a typo be silently ignored because `set_paras()` only applies known attributes?

### 2. Prompt -> Evaluator Boundary

This is the most common EoH drift point.

The prompt contract is assembled in `Evolution.__init__()` from the prompt object getters:

- `eoh/src/eoh/methods/eoh/eoh_evolution.py:11-16`

The evaluator then assumes that the generated code implements the advertised function and field shapes.

ABR is the clearest example of a synchronized contract:

- prompt text: `examples/user_abr/prompts.py:18-45`
- state builder: `examples/user_abr/abr_api.py:9-84`
- context builder: `examples/user_abr/abr_api.py:114-152`
- evaluator call site: `examples/user_abr/prob.py:281-299`
- smoke test fixture: `examples/user_abr/smoke_test.py:24-55`

If you change any one of those, change all of them.

### 3. LLM -> Evaluation Boundary

`InterfaceEC.get_offspring()` treats LLM generation and evaluation as two independent phases:

- LLM phase: `eoh/src/eoh/methods/eoh/eoh_interface_EC.py:311-360`
- evaluation phase: `eoh/src/eoh/methods/eoh/eoh_interface_EC.py:362-415`

Questions:

- What happens if the LLM response is unparseable?
- What happens if `evaluate()` returns `None`?
- Does the caller filter null offspring or `None` objectives afterward?

For the default population method, cleanup happens in `eoh/src/eoh/methods/management/pop_greedy.py:3-16`.

### 4. Method Loop -> Persistence Boundary

Every method writes populations to disk, but the runner may also wrap those outputs.

Inspect together:

- `eoh/src/eoh/eoh.py:19-28`
- `eoh/src/eoh/utils/createFolders.py:3-20`
- `eoh/src/eoh/methods/eoh/eoh.py:145-187`
- experiment-specific wrappers such as `examples/user_abr/runEoH.py:223-341`

Questions:

- Are you changing the timestamped output root or the inner `results/pops/` layout?
- Does any cache or post-processing script depend on the old location?
- Are you writing strings, `Path` objects, or a mix?

---

## Common EoH Cross-Layer Mistakes

### Mistake: Change `Paras` Without Checking All Consumers

`Paras.set_paras()` only applies keys that already exist in the class in `eoh/src/eoh/utils/getParas.py:118-121`. A typo is silently ignored.

Think through:

- default value in `Paras.__init__()`
- derived default in `set_ec()` or `set_evaluation()`
- explicit usage in method / problem code
- example runner input

### Mistake: Add an Operator in One File Only

A new operator is not complete until it exists in all three places:

- default/operator list in `eoh/src/eoh/utils/getParas.py:76-90`
- dispatch in `eoh/src/eoh/methods/eoh/eoh_interface_EC.py:281-300`
- prompt builder and wrapper in `eoh/src/eoh/methods/eoh/eoh_evolution.py:84-189` and `eoh/src/eoh/methods/eoh/eoh_evolution.py:254-320`

### Mistake: Forget That User Problems Bypass the String Registry

`Probs.__init__()` treats non-string `paras.problem` as a ready-made object in `eoh/src/eoh/problems/problems.py:8-10`.

That is how `examples/user_abr/runEoH.py:300-337` works. If you are prototyping, you may not need a built-in registration at all.

### Mistake: Ignore Strategy Signature Differences

`EOH` and `AEL` call `population_management(population, size)`:

- `eoh/src/eoh/methods/eoh/eoh.py:174-175`
- `eoh/src/eoh/methods/ael/ael.py:150-151`

`LS` calls `population_management(population, new, temperature)`:

- `eoh/src/eoh/methods/localsearch/ls.py:140-143`

Do not treat all management modules as drop-in replacements.

---

## Minimal Verification Matrix

| If you changed | Verify this next |
|-------------------|------------------|
| `Paras` fields or defaults | Search `Paras`, runner kwargs, and method/problem consumers |
| Problem registration | Confirm whether the change is string-based built-in or direct object injection |
| Prompt fields or state schema | Check prompt text, evaluator construction, and smoke tests together |
| LLM timeout / endpoint logic | Check `InterfaceLLM`, remote/local adapter, and `InterfaceEC.parallel_timeout` |
| Output layout or seed cache logic | Check core output creation and any experiment wrapper that copies or reuses populations |

**Rule**: If a change crosses `Paras`, registries, prompts, evaluation, and persistence, it is already a cross-layer change even if you only edited one file.

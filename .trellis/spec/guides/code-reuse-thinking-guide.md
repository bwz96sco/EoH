# Code Reuse Thinking Guide

> **Purpose**: Find the existing EoH extension pattern before creating a new file, branch, or prompt contract.

---

## The Main Reuse Traps in EoH

EoH already has reusable patterns for almost every extension point, but they are spread across factories, example runners, and problem modules.

If you skip the search pass, you usually end up with:

- a new file that never gets registered
- a copied run loop that drifts from `EOH`, `AEL`, or `LS`
- a prompt contract that differs from the evaluator contract
- a strategy module whose call signature does not match the caller

---

## Search These Reuse Seams First

| If you are adding | Search here first | Existing pattern to follow |
|----------------------|-------------------|----------------------------|
| New evolution method | `eoh/src/eoh/methods/methods.py:32-51`, `eoh/src/eoh/methods/eoh/eoh.py:11-203`, `eoh/src/eoh/methods/ael/ael.py:11-171`, `eoh/src/eoh/methods/localsearch/ls.py:11-159` | constructor shape `(paras, problem, select, manage, **kwargs)` and `run()` |
| New built-in problem | `eoh/src/eoh/problems/problems.py:6-25`, `eoh/src/eoh/problems/optimization/bp_online/run.py:9-125`, `eoh/src/eoh/problems/optimization/tsp_greedy/run.py:9-135` | `self.prompts` + `evaluate(code_string)` |
| New user-defined problem | `examples/user_abr/prob.py:72-367`, `examples/user_abr/runEoH.py:300-337` | pass a problem object through `Paras.set_paras(problem=problem, method="eoh")` |
| New EC operator | `eoh/src/eoh/utils/getParas.py:62-95`, `eoh/src/eoh/methods/eoh/eoh_interface_EC.py:274-302`, `eoh/src/eoh/methods/eoh/eoh_evolution.py:84-189` | operator string + prompt builder + dispatch branch |
| New selection strategy | `eoh/src/eoh/methods/methods.py:9-19`, `eoh/src/eoh/methods/selection/prob_rank.py:2-6` | module-level `parent_selection(pop, m)` |
| New management strategy | `eoh/src/eoh/methods/methods.py:21-29`, `eoh/src/eoh/methods/management/pop_greedy.py:3-16`, `eoh/src/eoh/methods/management/ls_sa.py:9-15` | module-level `population_management(pop, size)` or `population_management(population, new, temperature)` |
| New prompt contract | `eoh/src/eoh/methods/eoh/eoh_evolution.py:7-52`, `eoh/src/eoh/problems/optimization/bp_online/prompts.py:1-29`, `examples/user_abr/prompts.py:6-65` | six `GetPrompts` getters with matching names and shapes |

---

## Concrete EoH Reuse Patterns

### 1. Factory and Registry Reuse

`EVOL.run()` does not know your concrete problem or method. It only calls:

- `Probs(self.paras).get_problem()` in `eoh/src/eoh/eoh.py:43-45`
- `Methods(self.paras, problem).get_method()` in `eoh/src/eoh/eoh.py:47-49`

That means reuse starts with the registries:

- `Probs.__init__()` in `eoh/src/eoh/problems/problems.py:6-20`
- `Methods.__init__()` and `Methods.get_method()` in `eoh/src/eoh/methods/methods.py:6-51`

If you add a name but do not update the registry, the new code is dead.

### 2. Strategy Modules Are Modules, Not Classes

Selection and management reuse is deliberately lightweight:

```python
# eoh/src/eoh/methods/methods.py:9-26
self.select = prob_rank
self.manage = pop_greedy
```

The call sites expect module-level functions:

- `self.select.parent_selection(pop, self.m)` in `eoh/src/eoh/methods/eoh/eoh_interface_EC.py:285-298`
- `self.manage.population_management(population, size_act)` in `eoh/src/eoh/methods/eoh/eoh.py:174-175`
- `self.manage.population_management(population, offsprings[0], temperature)` in `eoh/src/eoh/methods/localsearch/ls.py:140-143`

Do not wrap new strategies in a class unless you also change every caller.

### 3. Prompt Contracts Reuse a Stable Getter Surface

`Evolution.__init__()` consumes the prompt object through a fixed set of getters in `eoh/src/eoh/methods/eoh/eoh_evolution.py:11-16`:

- `get_task()`
- `get_func_name()`
- `get_func_inputs()`
- `get_func_outputs()`
- `get_inout_inf()`
- `get_other_inf()`

Both built-in problems and ABR reuse that same surface:

- built-in bin packing prompt: `eoh/src/eoh/problems/optimization/bp_online/prompts.py:1-29`
- ABR prompt: `examples/user_abr/prompts.py:6-65`

If a new problem needs richer prompt text, extend the strings, not the getter API.

### 4. Evaluation Reuse Follows the Same Failure Contract

Built-in problems and user problems both converge on the same high-level shape:

- `evaluate(code_string)` returns `float | None`
- optional `evaluate_with_details(code_string)` returns `(fitness, feedback)`

Examples:

- `BPONLINE.evaluate()` in `eoh/src/eoh/problems/optimization/bp_online/run.py:105-125`
- `TSPCONST.evaluate()` in `eoh/src/eoh/problems/optimization/tsp_greedy/run.py:116-135`
- `ABRProblem.evaluate_with_details()` in `examples/user_abr/prob.py:347-367`

If you need feedback-guided mutation, copy the ABR pattern instead of inventing a new side channel.

---

## Anti-Patterns Already Visible in This Repo

### Do Not Add a Factory Branch Without a Real Package

`Methods.get_method()` has `funsearch` and `reevo` branches in `eoh/src/eoh/methods/methods.py:43-48`, but this working tree has no matching `eoh/src/eoh/methods/funsearch/` or `eoh/src/eoh/methods/reevo/` package.

Treat this as a warning: registry drift is easy to create and hard to spot until runtime.

### Do Not Copy Whole Method Loops Unless You Mean to Fork the Contract

`EOH`, `AEL`, and `LS` all carry similar initialization and persistence logic:

- `eoh/src/eoh/methods/eoh/eoh.py:11-203`
- `eoh/src/eoh/methods/ael/ael.py:11-171`
- `eoh/src/eoh/methods/localsearch/ls.py:11-159`

Before copying one more method loop, decide which behavior actually differs:

- operator names
- management signature
- timeout / numba / feedback behavior

### Do Not Invent Near-Miss Config Names

`eoh/src/eoh/utils/getParas.py:86-90` checks `self.ec_operator` while the rest of the file uses `self.ec_operators`.

This is exactly the kind of singular/plural drift that happens when config names are copied instead of searched.

### Do Not Duplicate Prompt Contracts in One Layer Only

ABR shows the full contract surface:

- prompt text: `examples/user_abr/prompts.py:18-45`
- state construction: `examples/user_abr/abr_api.py:9-152`
- evaluator usage: `examples/user_abr/prob.py:281-299` and `examples/user_abr/prob.py:347-367`
- smoke-test fixture: `examples/user_abr/smoke_test.py:24-55`

If you widen `state` or `ctx`, update all of them together.

---

## Reuse Checklist Before Creating a New File

- [ ] Searched the registry and existing example runners with `rg`
- [ ] Confirmed whether this is a built-in problem, user-defined problem, method, operator, strategy, or backend
- [ ] Reused the existing constructor / function signature instead of inventing a new one
- [ ] Checked whether the same change must also land in `Paras`, `Methods`, `Probs`, or `GetPrompts`
- [ ] Verified whether a similar implementation already exists in `examples/user_*`

```bash
rg -n "class (EOH|AEL|LS)|def run\\(" eoh/src/eoh/methods
rg -n "self\\.prompts|def evaluate|def evaluate_with_details" eoh/src/eoh/problems examples
rg -n "get_prompt_|operator ==|ec_operators" eoh/src/eoh
```

**Rule**: In EoH, create a new file only after you know which existing registry and contract it must fit.

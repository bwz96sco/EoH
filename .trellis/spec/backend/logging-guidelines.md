# Logging Guidelines

> How logging and output is done in the EoH project.

---

## Overview

EoH does **not** use Python's `logging` module. All output is done exclusively through `print()` statements. There are no structured log files, no log levels, and no log configuration. Output is controlled by the `exp_debug_mode` parameter.

---

## Output Mechanism

**`print()` only.** The `logging` module is not imported or used anywhere in the core framework (`eoh/src/eoh/`).

---

## Output Categories

### Category A: Lifecycle Banners

```python
# eoh/src/eoh/eoh.py:14-16 (startup)
print("----------------------------------------- ")
print("---              Start EoH            ---")
print("-----------------------------------------")

# eoh/src/eoh/eoh.py:44-47 (completion)
print("> End of Evolution! ")
print("---     EoH successfully finished !   ---")
```

### Category B: Initialization Status

```python
# eoh/src/eoh/methods/eoh/eoh.py:61
print("- EoH parameters loaded -")

# eoh/src/eoh/llm/interface_LLM.py:13
print("- check LLM API")

# eoh/src/eoh/llm/interface_LLM.py:27
print('remote llm api is used ...')
```

### Category C: Evolutionary Progress (Most Important)

This is the primary output during a run. Pattern is identical across EOH, AEL, and LS methods.

**Per-operator inline progress:**
```python
# eoh/src/eoh/methods/eoh/eoh.py:148
print(f" OP: {op}, [{i + 1} / {n_op}] ", end="|")
```

**Per-generation summary:**
```python
# eoh/src/eoh/methods/eoh/eoh.py:180-184
print(f"--- {pop + 1} of {self.n_pop} populations finished. Time Cost:  {((time.time()-time_start)/60):.1f} m")
print("Pop Objs: ", end=" ")
for i in range(len(population)):
    print(str(population[i]['objective']) + " ", end="")
print()
```

**Typical console output during a run:**
```
- EoH parameters loaded -
- Evolution Start -
creating initial population:
Pop initial:
 Obj: 0.12345| Obj: 0.23456| Obj: 0.34567|
initial population has been created!
 OP: e1, [1 / 4] | Obj: 0.12345| Obj: None|
 OP: m1, [2 / 4] | Obj: 0.45678|
--- 1 of 10 populations finished. Time Cost:  2.3 m
Pop Objs:  0.12345 0.23456 0.34567
```

### Category D: Error Messages

```python
# eoh/src/eoh/llm/api_general.py:46-49
if self.debug_mode:
    print(f"Error in API (attempt {n_trial}/{self.n_trial}): {e}")
else:
    print(f"API error: {type(e).__name__}: {e}")
```

Error prefixes used in the codebase:
- `">> Stop with ..."` -- Fatal configuration errors
- `">> Error in ..."` -- Fatal runtime errors
- `"Error: ..."` -- Recoverable errors
- `"Parallel time out ."` -- Timeout errors
- `"duplicated result, retrying ..."` -- Retry messages
- `"Warning! ..."` -- Soft validation warnings

---

## Debug Mode (`exp_debug_mode`)

Defined in `eoh/src/eoh/utils/getParas.py` line 33. Default: `False`.

### What Debug Mode Enables

**1. Interactive step-through** -- Pauses after each LLM prompt and response:

```python
# eoh/src/eoh/methods/eoh/eoh_evolution.py:198-209
if self.debug_mode:
    print("\n >>> check prompt for creating algorithm using [ i1 ] : \n", prompt_content)
    print(">>> Press 'Enter' to continue")
    input()

# ... after LLM response ...

if self.debug_mode:
    print("\n >>> check designed algorithm: \n", algorithm)
    print("\n >>> check designed code: \n", code_all)
    print(">>> Press 'Enter' to continue")
    input()
```

This repeats for every evolutionary operator (i1, e1, e2, m1, m2, m3).

**2. Detailed error output** -- Shows retry messages and error details:

```python
if self.debug_mode:
    print("Error: algorithm or code not identified, wait 1 seconds and retrying ... ")
```

**3. Warning visibility** -- When NOT in debug mode, Python warnings are suppressed:

```python
# eoh/src/eoh/methods/eoh/eoh_interface_EC.py:21-22
if not self.debug:
    warnings.filterwarnings("ignore")
```

---

## File-Based Output

### JSON Population Files (Primary Output)

Written at end of every generation:

```
{exp_output_path}/results/pops/population_generation_{N}.json     # Full population
{exp_output_path}/results/pops_best/population_generation_{N}.json # Best individual
```

JSON schema per individual:
```json
{
    "algorithm": "Natural language description",
    "code": "def heuristic(...):\n    ...",
    "objective": 0.12345,
    "other_inf": null
}
```

### Evaluation Results (Post-Evolution)

Evaluation scripts write to plain text:
```python
# examples/bp_online/evaluation/runEval.py:18
with open("results.txt", "w") as file:
    file.write(result + "\n")
```

### Report Generation (Utility)

`eoh/src/eoh/utils/createReport.py` generates convergence plots (PNG/PDF) and Word document reports. Not called automatically during evolution.

---

## Conventions for New Code

1. **Use `print()` for output** -- do not introduce `logging` module (maintain consistency)
2. **Gate verbose output behind `debug_mode`** -- normal runs should show only progress and errors
3. **Use `>>` prefix for fatal errors** that call `exit()`
4. **Objective values**: Round to 5 decimal places via `np.round(float(fitness), 5)`
5. **Progress output**: Use `end="|"` for inline operator progress
6. **No progress bars**: The codebase does not use tqdm or similar libraries
7. **JSON results**: Always save population snapshots per generation with `indent=5`

---

## What NOT to Print

- LLM API keys or credentials
- Full LLM prompts (only in debug mode)
- Full exception tracebacks (only in debug mode)
- Individual evaluation errors (they're expected and frequent)

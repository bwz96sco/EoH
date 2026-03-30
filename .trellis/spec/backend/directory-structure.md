# Directory Structure

> How backend code is organized in the EoH project.

---

## Overview

EoH is a Python package using `setuptools` with the source root at `eoh/src/`. The installable package lives at `eoh/src/eoh/` (configured in `pyproject.toml` line 19: `package-dir = {"" = "eoh/src"}`). Examples live outside the package in `examples/`.

---

## Top-Level Layout

```
EoH/
├── pyproject.toml          # Build config (setuptools, Python >=3.10)
├── CLAUDE.md               # AI assistant instructions
├── eoh/                    # Core package
│   ├── setup.py            # Legacy setup.py (duplicates pyproject.toml)
│   └── src/eoh/            # Installable package source
├── examples/               # Ready-to-run example problems
├── baseline/               # Baseline implementations (FunSearch)
├── experiments/            # Canonical experiment workflows and summaries
├── scripts/                # Standalone utility scripts
├── docs/                   # Documentation and experiment results
├── env/                    # External environment files (e.g., SABR)
├── results/                # Generated evolution outputs (JSON snapshots)
├── test_results/           # Generated evaluation outputs
└── build/                  # Stale build artifacts (can be ignored)
```

---

## Core Framework (`eoh/src/eoh/`)

```
eoh/src/eoh/
├── __init__.py             # Empty (enables package import)
├── eoh.py                  # EVOL class - main orchestrator entry point
│
├── llm/                    # LLM interface layer
│   ├── interface_LLM.py    # InterfaceLLM - router for remote/local
│   ├── api_general.py      # InterfaceAPI - HTTPS API calls (OpenAI-compatible)
│   ├── api_local_llm.py    # InterfaceLocalLLM - local LLM deployment
│   └── api_hf_inter.py     # InterfaceHF - HuggingFace inference API
│
├── llm_local_server/       # Standalone local LLM server scripts (NOT a package)
│   ├── gemma_instruct_server.py
│   ├── codellama_server.py
│   ├── codellama_instruct_server.py
│   ├── deepseek_coder_server.py
│   ├── starcoder_server.py
│   └── request.py
│
├── methods/                # Evolutionary methods
│   ├── methods.py          # Methods class - factory for selecting method
│   ├── eoh/                # Evolution of Heuristics method
│   │   ├── eoh.py          # EOH class - main evolution loop
│   │   ├── eoh_evolution.py      # Evolution class - LLM prompts & response parsing
│   │   ├── eoh_interface_EC.py   # InterfaceEC - bridges LLM with evaluation
│   │   └── evaluator_accelerate.py  # AST utilities for numba decoration
│   ├── ael/                # Alternative Evolutionary Learning method
│   │   ├── ael.py
│   │   ├── ael_evolution.py
│   │   ├── ael_interface_EC.py
│   │   └── evaluator_accelerate.py
│   ├── localsearch/        # Local Search / Simulated Annealing method
│   │   ├── ls.py
│   │   ├── ls_evolution.py
│   │   ├── ls_interface_EC.py
│   │   └── evaluator_accelerate.py
│   ├── selection/          # Parent selection strategies (module-level functions)
│   │   ├── prob_rank.py    # Probability rank (default)
│   │   ├── equal.py        # Uniform random
│   │   ├── roulette_wheel.py
│   │   └── tournament.py
│   └── management/         # Population management strategies (module-level functions)
│       ├── pop_greedy.py   # Top-N greedy (for population methods)
│       ├── ls_greedy.py    # Replace if better (for local search)
│       └── ls_sa.py        # Simulated annealing acceptance
│
├── problems/               # Problem definitions
│   ├── problems.py         # Probs class - factory for selecting problem
│   ├── optimization/       # Optimization problems
│   │   ├── bp_online/      # Online bin packing
│   │   │   ├── run.py      # BPONLINE class
│   │   │   ├── prompts.py  # GetPrompts class
│   │   │   └── get_instance.py
│   │   └── tsp_greedy/     # TSP greedy construction
│   │       ├── run.py      # TSPCONST class
│   │       ├── prompts.py
│   │       └── get_instance.py
│   └── machinelearning/    # ML problems
│       └── L_AutoDA/       # Automated data augmentation
│
├── utils/                  # Utility modules
│   ├── getParas.py         # Paras class - parameter configuration
│   ├── createFolders.py    # Output folder creation
│   ├── createReport.py     # Word document report generation
│   ├── timeout_diagnostics.py  # JSONL timeout diagnostic logging
│   ├── get_all_results.py  # Results visualization
│   └── get_algorithm&code_pop.py  # Population data extraction
│
└── test/
    └── run.py              # Manual smoke test (not pytest)
```

---

## Evolution Operator Module Layout

The evolution operator system is split across three files in each method directory. This section documents the EoH variant (`methods/eoh/`) in detail.

### File Responsibilities

| File | Class | Responsibility |
|------|-------|----------------|
| `eoh.py` | `EOH` | Main evolution loop: init pop, iterate operators, save checkpoints |
| `eoh_evolution.py` | `Evolution` | Prompt construction (`get_prompt_XX`) + response parsing (`_get_alg`) for each operator |
| `eoh_interface_EC.py` | `InterfaceEC` | EC-LLM bridge: parent selection dispatch, parallel evaluation, timeout diagnostics |
| `evaluator_accelerate.py` | (functions) | AST-based numba `@jit` decorator injection |

### Operator Dispatch Chain

The operator dispatch follows a three-layer call chain:

```
EOH.run()                              # eoh/src/eoh/methods/eoh/eoh.py:154-176
  -> InterfaceEC.get_algorithm()        # eoh/src/eoh/methods/eoh/eoh_interface_EC.py:435-470
       -> joblib.Parallel(get_offspring)
            -> InterfaceEC._get_alg()   # eoh/src/eoh/methods/eoh/eoh_interface_EC.py:274-302
                 -> Evolution.{i1,e1,e2,m1,m2,m3}()
                      -> Evolution.get_prompt_XX()
                      -> Evolution._get_alg()  # LLM call + parse
            -> InterfaceEC._evaluate_with_timeout()  # subprocess evaluation
```

### GitNexus Flow Cross-Check

GitNexus groups the runtime symbols above into the `Eoh` and `Llm` modules. The indexed process strings include the pairs `Get_prompt_i1 -> Get_offspring`, `Get_prompt_e1 -> Get_offspring`, `Get_prompt_e2 -> Get_offspring`, `Get_prompt_m1 -> Get_offspring`, `Get_response -> Get_offspring`, and `Request -> Get_response`, which matches the source-level flow:

`EOH.run()` -> `InterfaceEC.get_offspring()` -> `Evolution.get_prompt_*()` / `Evolution._get_alg()` -> `InterfaceLLM.get_response()` -> HTTP request transport.

### Operator Definitions (6 Operators)

Each operator is implemented as:

- one prompt-construction method in `eoh/src/eoh/methods/eoh/eoh_evolution.py`
- one wrapper method in the same file that calls `_get_alg(prompt_content)`
- one dispatch branch in `InterfaceEC._get_alg()` inside `eoh/src/eoh/methods/eoh/eoh_interface_EC.py:274-302`

| Operator | Prompt builder | Wrapper | Parent count | Distinguishing contract |
|----------|----------------|---------|--------------|-------------------------|
| `i1` | `get_prompt_i1()` at `eoh/src/eoh/methods/eoh/eoh_evolution.py:84-93` | `i1()` at `eoh/src/eoh/methods/eoh/eoh_evolution.py:254-271` | 0 | Create a brand-new algorithm from the task description only |
| `e1` | `get_prompt_e1()` at `eoh/src/eoh/methods/eoh/eoh_evolution.py:96-111` | `e1()` at `eoh/src/eoh/methods/eoh/eoh_evolution.py:273-290` | `self.m` | Ask for a totally different form from the provided parents |
| `e2` | `get_prompt_e2()` at `eoh/src/eoh/methods/eoh/eoh_evolution.py:113-128` | `e2()` at `eoh/src/eoh/methods/eoh/eoh_evolution.py:292-309` | `self.m` | Ask for a new algorithm motivated by the shared parent backbone |
| `m1` | `get_prompt_m1()` at `eoh/src/eoh/methods/eoh/eoh_evolution.py:130-166` | `m1()` at `eoh/src/eoh/methods/eoh/eoh_evolution.py:311-328` | 1 | Mutation prompt can include `other_inf` evaluator feedback |
| `m2` | `get_prompt_m2()` at `eoh/src/eoh/methods/eoh/eoh_evolution.py:168-181` | `m2()` at `eoh/src/eoh/methods/eoh/eoh_evolution.py:330-347` | 1 | Mutate algorithm parameters/settings while preserving function contract |
| `m3` | `get_prompt_m3()` at `eoh/src/eoh/methods/eoh/eoh_evolution.py:183-189` | `m3()` at `eoh/src/eoh/methods/eoh/eoh_evolution.py:349-366` | 1 | Simplify potentially overfit components for better generalization |

Real example: `m1` is the only prompt builder that conditionally injects evaluator feedback:

```python
# eoh/src/eoh/methods/eoh/eoh_evolution.py:130-147
def get_prompt_m1(self, indiv1):
    feedback = ""
    other_inf = indiv1.get("other_inf")
    if isinstance(other_inf, str) and other_inf.strip():
        feedback = "\nEvaluation feedback (for guidance):\n" + other_inf.strip() + "\n"

    prompt_content = (
        self.prompt_task
        + "\n"
        + "I have one algorithm with its code as follows. "
```

### Parent Selection per Operator

The `InterfaceEC._get_alg()` method dispatches parent selection differently per operator:

```python
# eoh/src/eoh/methods/eoh/eoh_interface_EC.py:274-302
def _get_alg(self, pop, operator):
    if operator == "i1":
        parents = None                              # No parents needed
    elif operator == "e1":
        parents = self.select.parent_selection(pop, self.m)  # m parents
    elif operator == "e2":
        parents = self.select.parent_selection(pop, self.m)  # m parents
    elif operator == "m1":
        parents = self.select.parent_selection(pop, 1)       # 1 parent
    elif operator == "m2":
        parents = self.select.parent_selection(pop, 1)       # 1 parent
    elif operator == "m3":
        parents = self.select.parent_selection(pop, 1)       # 1 parent
```

### Operator Configuration

Operators are configured via `Paras` at initialization:

```python
# eoh/src/eoh/utils/getParas.py:17-19
self.ec_operators = None       # default: ['e1','e2','m1','m2'] for eoh
self.ec_operator_weights = None # default: [1,1,1,1] (all equally likely)

# eoh/src/eoh/utils/getParas.py:76-87 -- Defaults set in set_ec():
if self.method == 'eoh':
    self.ec_operators = ['e1','e2','m1','m2']
elif self.method == 'ael':
    self.ec_operators = ['crossover','mutation']
elif self.method in ['ls', 'sa']:
    self.ec_operators = ['m1']
```

Operator weights control the probability of executing each operator in a generation:

```python
# eoh/src/eoh/methods/eoh/eoh.py:159-161
op_w = self.operator_weights[i]
if (np.random.rand() < op_w):
    parents, offsprings = interface_ec.get_algorithm(population, op, generation=pop + 1)
```

---

## Selection and Management Plugin Directories

### `methods/selection/` -- Parent Selection Strategies

Each file exports a single module-level function: `parent_selection(pop, m) -> list[dict]`.

| File | Strategy | Algorithm |
|------|----------|-----------|
| `prob_rank.py` | Probability rank (default) | Weight = `1 / (rank + 1 + len(pop))`, uses `random.choices()` |
| `equal.py` | Uniform random | `random.choices(population, k=m)` |
| `roulette_wheel.py` | Fitness-proportional | Weight = `1 / (objective + 1e-6)`, normalized |
| `tournament.py` | Tournament selection | Binary tournament (`tournament_size=2`), min fitness wins |

Selection strategy is resolved in `Methods.__init__()`:

```python
# eoh/src/eoh/methods/methods.py:9-19
if paras.selection == "prob_rank":
    self.select = prob_rank       # imports the module itself
elif paras.selection == "equal":
    self.select = equal
elif paras.selection == 'roulette_wheel':
    self.select = roulette_wheel
elif paras.selection == 'tournament':
    self.select = tournament
```

### `methods/management/` -- Population Management Strategies

Each file exports a module-level function. The signature differs by method type:

| File | Strategy | Signature | Algorithm |
|------|----------|-----------|-----------|
| `pop_greedy.py` | Top-N greedy | `population_management(pop, size)` | Filter `None`, deduplicate by objective, keep top N via `heapq.nsmallest` |
| `ls_greedy.py` | Replace if better | `population_management(population, new, temperature)` | Replace `population[0]` if `new.objective < population[0].objective` |
| `ls_sa.py` | Simulated annealing | `population_management(population, new, temperature)` | Replace with SA acceptance probability: `exp((old - new) / old / T)` |

Management strategy is resolved in `Methods.__init__()`:

```python
# eoh/src/eoh/methods/methods.py:21-29
if paras.management == "pop_greedy":
    self.manage = pop_greedy
elif paras.management == 'ls_greedy':
    self.manage = ls_greedy
elif paras.management == 'ls_sa':
    self.manage = ls_sa
```

Default strategy is auto-set based on method:

```python
# eoh/src/eoh/utils/getParas.py:64-70
if self.method in ['ael','eoh']:
    self.management = 'pop_greedy'
elif self.method == 'ls':
    self.management = 'ls_greedy'
elif self.method == 'sa':
    self.management = 'ls_sa'
```

---

## Examples Organization

### Two Categories

**Built-in problem examples** (use string-based problem names):
```
examples/bp_online/runEoH.py           # paras.set_paras(problem="bp_online")
examples/tsp_construct/runEoH.py       # paras.set_paras(problem="tsp_construct")
examples/bp_online_localLLM/runEoH.py  # Local LLM variant
```

**User-defined problem examples** (pass problem object directly):
```
examples/user_bp_online/               # User-level bin packing
examples/user_tsp_gls/                 # TSP with Guided Local Search
examples/user_fssp_gls/                # Flow Shop Scheduling with GLS
examples/user_bo_caf/                  # Bayesian Optimization CAF
examples/user_abr/                     # Adaptive Bitrate Streaming
```

### User-Defined Problem Folder Pattern

Every `user_*` example follows this layout:

```
examples/user_<name>/
├── runEoH.py       # Entry point: imports prob.py, creates Paras, runs EVOL
├── prob.py         # Problem class with evaluate(code_string) and self.prompts
├── prompts.py      # GetPrompts class (task description, function signatures)
└── [domain files]  # Optional: domain-specific code, data, utilities
```

Minimal local-problem wiring is visible in `examples/user_bp_online/`:

```python
# examples/user_bp_online/runEoH.py:6-25
paras = Paras()
problem_local = BPONLINE()
paras.set_paras(
    method="eoh",
    problem=problem_local,
    llm_api_endpoint="XXX",
    llm_api_key="XXX",
    llm_model="gpt-3.5-turbo",
    ec_pop_size=4,
    ec_n_pop=4,
    exp_n_proc=4,
    exp_output_path="./results/",
)
evolution = eoh.EVOL(paras)
```

That local problem object must provide both `self.prompts` and an evaluator:

```python
# examples/user_bp_online/prob.py:9-14,105-125
class BPONLINE():
    def __init__(self):
        getdate = GetData()
        self.instances, self.lb = getdate.get_instances()
        self.prompts = GetPrompts()

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

The prompt-side contract is a simple getter-based object:

```python
# examples/user_bp_online/prompts.py:1-29
class GetPrompts():
    def __init__(self):
        self.prompt_task = "I need help designing a novel score function..."
        self.prompt_func_name = "score"
        self.prompt_func_inputs = ['item', 'bins']
        self.prompt_func_outputs = ['scores']
```

### Evaluation Subfolder Pattern

Built-in examples include post-evolution evaluation:

```
examples/<problem>/evaluation/
├── runEval.py          # Evaluation runner
├── evaluation.py       # Evaluation logic
├── heuristic.py        # Best evolved heuristic (copy from results)
├── get_instance.py     # Test instance loading
└── testingdata/        # Pickle files with test instances
```

### ABR Experiment Output Pattern

`examples/user_abr/` uses a canonical experiment run tree instead of writing final outputs directly into `examples/user_abr/` or the repo-root `results/` directory.

```
experiments/
├── run_experiment.sh       # Canonical ABR pipeline entry point
├── collect_results.py      # Summary CSV generation
├── plot_results.py         # Plot generation
├── generate_run_report.py  # Per-run markdown report generation
├── run_layout.py           # Canonical path helpers
├── update_experiment_tracker.py  # Rebuilds the repo-level run ledger
├── private/                # Gitignored private experiment metadata
│   ├── experiment_index.md # Generated private tracker of canonical runs
│   └── backup.env          # Optional local backup defaults (untracked)
└── results/
    └── <run-id>/
```

Per-run outputs live under:

```
experiments/results/<run-id>/
├── raw/
│   └── eoh/
│       ├── ABRBench-3G/
│       │   └── eoh_ABRProblem_<timestamp>/
│       │       ├── config.json
│       │       └── results/
│       │           ├── history/
│       │           ├── pops/
│       │           └── pops_best/
│       └── ABRBench-4G+/
├── analysis/
│   ├── results_summary.csv
│   ├── run_report.md
│   └── plots/
└── logs/
```

`examples/user_abr/seed_cache/<dataset>/` is cache-only for seed population reuse and is not part of the canonical result bundle.
`experiments/private/experiment_index.md` is the generated private cross-run ledger. It summarizes every canonical run currently present under `experiments/results/` without putting run metadata into tracked source files.
`experiments/private/backup.env` may define local defaults such as `ABR_BACKUP_REMOTE_DEFAULT` and `ABR_BACKUP_SEED_CACHE_DEFAULT` without committing personal remote paths into the repo.
If `ABR_BACKUP_REMOTE` is set, or if `experiments/private/backup.env` provides `ABR_BACKUP_REMOTE_DEFAULT`, the workflow mirrors canonical artifacts to an external remote using the same repo-relative layout, for example `.../experiments/results/<run-id>/` and `.../experiments/private/experiment_index.md`.

---

## Naming Conventions

| Category | Convention | Examples |
|----------|-----------|----------|
| Files (most) | snake_case | `api_general.py`, `pop_greedy.py`, `prob_rank.py` |
| Files (utils) | camelCase (legacy) | `getParas.py`, `createFolders.py`, `createReport.py` |
| Files (method-prefixed) | `{method}_*.py` | `eoh_evolution.py`, `ael_interface_EC.py`, `ls_evolution.py` |
| Classes | PascalCase / ALLCAPS | `EVOL`, `EOH`, `AEL`, `LS`, `InterfaceEC`, `BPONLINE`, `GetPrompts` |
| Module-level functions | snake_case | `parent_selection()`, `population_management()` |

---

## How to Add New Components

### New Evolution Operator

1. Add `get_prompt_XX()` method to `eoh/src/eoh/methods/eoh/eoh_evolution.py` returning the prompt string
2. Add `XX()` method to `eoh/src/eoh/methods/eoh/eoh_evolution.py` wrapping `_get_alg()` with debug logging
3. Add `elif operator == "XX":` branch in `eoh/src/eoh/methods/eoh/eoh_interface_EC.py` method `_get_alg()` with the appropriate parent selection (1 parent for mutation, `self.m` parents for crossover)
4. Include operator name in `ec_operators` list when configuring `Paras`

Example -- adding a hypothetical `m4` operator:

```python
# Step 1: In eoh_evolution.py -- add prompt constructor
def get_prompt_m4(self, indiv1):
    prompt_content = self.prompt_task + "\n" + "..."
    return prompt_content

# Step 2: In eoh_evolution.py -- add execution wrapper
def m4(self, parents):
    prompt_content = self.get_prompt_m4(parents)
    if self.debug_mode:
        print("\n >>> check prompt for creating algorithm using [ m4 ] : \n", prompt_content)
        print(">>> Press 'Enter' to continue")
        input()
    [code_all, algorithm] = self._get_alg(prompt_content)
    if self.debug_mode:
        print("\n >>> check designed algorithm: \n", algorithm)
        print("\n >>> check designed code: \n", code_all)
        print(">>> Press 'Enter' to continue")
        input()
    return [code_all, algorithm]

# Step 3: In eoh_interface_EC.py _get_alg() -- add dispatch
elif operator == "m4":
    parents = self.select.parent_selection(pop, 1)
    [offspring['code'], offspring['algorithm']] = self.evol.m4(parents[0])

# Step 4: In runEoH.py -- include in operator list
paras.set_paras(ec_operators=['e1','e2','m1','m2','m4'])
```

### New Method

1. Create `eoh/src/eoh/methods/<method_name>/` with: `<name>.py`, `<name>_evolution.py`, `<name>_interface_EC.py`, `evaluator_accelerate.py`
2. Main class must accept `(paras, problem, select, manage)` and have `run()`
3. Add `elif` branch in `methods/methods.py` `get_method()`

### New Built-in Problem

1. Create `eoh/src/eoh/problems/optimization/<name>/` with: `run.py`, `prompts.py`, `get_instance.py`
2. Problem class must have `self.prompts` (GetPrompts) and `evaluate(code_string)`
3. Add `elif` branch in `problems/problems.py`

### New User-Defined Problem (preferred)

1. Create `examples/user_<name>/` with: `runEoH.py`, `prob.py`, `prompts.py`
2. Pass problem object directly: `paras.set_paras(problem=problem_obj)`
3. No core framework changes needed

### New Selection Strategy

1. Create `.py` file in `methods/selection/`
2. Define module-level function `parent_selection(pop, m) -> list[dict]`
3. Add `elif` branch in `methods/methods.py` `__init__()`
4. The `pop` argument is a sorted list of individual dicts (best first); `m` is the number of parents to return

### New Management Strategy

1. Create `.py` file in `methods/management/`
2. For population methods: `population_management(pop, size) -> list[dict]`
3. For local search methods: `population_management(population, new, temperature) -> None` (mutates in place)
4. Add `elif` branch in `methods/methods.py` `__init__()`

---

## Key Architecture: Data Flow

```
runEoH.py -> EVOL(paras).run()
  -> Probs(paras).get_problem()       # Resolve problem
  -> Methods(paras, problem).get_method()  # Resolve method + selection + management
  -> method.run()                      # Evolution loop
       -> InterfaceEC                  # Bridges LLM <-> Evaluation
            -> Evolution (LLM prompts) # Generate/mutate heuristics via LLM
            -> problem.evaluate(code)  # Evaluate heuristic fitness
       -> Results saved under the configured experiment root, e.g.
          experiments/results/<run-id>/raw/eoh/<name>/eoh_<Problem>_<timestamp>/results/pops/*.json
```

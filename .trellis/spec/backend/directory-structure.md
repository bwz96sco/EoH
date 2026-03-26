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
│   ├── get_all_results.py  # Results visualization
│   └── get_algorithm&code_pop.py  # Population data extraction
│
└── test/
    └── run.py              # Manual smoke test (not pytest)
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
├── run_layout.py           # Canonical path helpers
├── update_experiment_tracker.py  # Rebuilds the repo-level run ledger
├── experiment_index.md     # Generated tracker of canonical runs
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
│   └── plots/
└── logs/
```

`examples/user_abr/seed_cache/<dataset>/` is cache-only for seed population reuse and is not part of the canonical result bundle.
`experiments/experiment_index.md` is the generated cross-run ledger. It summarizes every canonical run currently present under `experiments/results/`.

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

### New Selection/Management Strategy

1. Create `.py` file in `methods/selection/` or `methods/management/`
2. Define module-level function `parent_selection(pop, m)` or `population_management(...)`
3. Add `elif` branch in `methods/methods.py`

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

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

EoH (Evolution of Heuristics) is a platform that combines Evolutionary Computation (EC) with Large Language Models (LLMs) for automatic algorithm design. It leverages the synergy between LLMs and EC to evolve heuristics and algorithms for optimization problems.

## Installation and Setup

**Using uv (recommended):**
```bash
uv sync
```

**Traditional method:**
```bash
cd eoh
pip install .
```

**Prerequisites:**
- Python >= 3.10
- uv package manager (recommended) or pip
- Required packages: numpy, numba, joblib

## Core Architecture

### Main Components

**Core Framework (`eoh/src/eoh/`):**
- `eoh.py` - Main EVOL class that orchestrates the entire evolution process
- `methods/` - Contains different evolutionary methods (eoh, ael, localsearch)
- `problems/` - Problem definitions for optimization and machine learning tasks
- `llm/` - LLM interface and API management
- `utils/` - Utility functions for parameters, folders, and reporting

**Methods:**
- **EoH** (`methods/eoh/`) - Main evolution of heuristics method
- **AEL** (`methods/ael/`) - Alternative evolutionary learning approach
- **Local Search** (`methods/localsearch/`) - Local search-based optimization

**Problems:**
- **Optimization** (`problems/optimization/`) - TSP, Bin Packing, etc.
- **Machine Learning** (`problems/machinelearning/`) - Attack algorithms

## Common Development Tasks

### Running Examples

**Online Bin Packing:**
```bash
uv run python examples/bp_online/runEoH.py
```

**TSP Construction:**
```bash
uv run python examples/tsp_construct/runEoH.py
```

**Custom Problems:**
```bash
uv run python examples/user_XXX/runEoH.py
```

### Evaluation

After running EoH, evaluate results:
```bash
# Copy your evolved heuristic to examples/{problem}/evaluation/heuristic.py
uv run python examples/{problem}/evaluation/runEval.py
```

### LLM Configuration

**Before running any example, configure your LLM settings in runEoH.py:**

For remote APIs:
```python
paras.set_paras(
    llm_api_endpoint = "api.openai.com",  # or "api.deepseek.com"
    llm_api_key = "your-api-key",
    llm_model = "gpt-3.5-turbo"  # or "deepseek-chat"
)
```

For local LLMs:
```bash
uv run python eoh/src/eoh/llm_local_server/gemma_instruct_server.py  # or other server scripts
# Then set llm_api_endpoint to your local server URL
```

## Key Parameters

When configuring `paras.set_paras()`:
- `method` - Evolution method: "eoh", "ael", "localsearch"
- `problem` - Target problem: "bp_online", "tsp_construct", etc.
- `ec_pop_size` - Population size for evolutionary computation
- `ec_n_pop` - Number of populations/generations
- `exp_n_proc` - Number of parallel processes
- `exp_debug_mode` - Enable/disable debug output

## Project Structure

- `baseline/funsearch/` - FunSearch baseline implementation for comparison
- `examples/` - Ready-to-run examples for different problems
- `eoh/src/eoh/` - Main EoH framework source code
- `docs/` - Documentation (minimal, mostly placeholder)

## SABR Dependency (ABR experiments)

The ABR (Adaptive Bitrate) experiments depend on [SABR](https://github.com/luopeng69131/SABR), which lives as a separate repo inside `env/SABR`. It is **not** a submodule — it's `.gitignore`d and must be cloned independently.

**Setup:**
```bash
# Clone the SABR fork into env/SABR
git clone https://github.com/bwz96sco/SABR.git env/SABR

# Build the C++ simulation environment
cd env/SABR
bash build.sh

# Create and activate a Python venv for SABR (uses its own dependencies)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Git remotes (for both EoH and SABR):**
- `origin` — upstream repo (for pulling updates)
- `myfork` — your fork at `bwz96sco/{EoH,SABR}` (for pushing work)

## Important Notes

- Always set LLM credentials before running examples
- Results and logs are saved to automatically created output folders
- The framework supports both remote LLM APIs and local LLM deployment
- Each problem requires specific heuristic function signatures for evaluation

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **EoH** (2157 symbols, 5485 relationships, 167 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## When Debugging

1. `gitnexus_query({query: "<error or symptom>"})` — find execution flows related to the issue
2. `gitnexus_context({name: "<suspect function>"})` — see all callers, callees, and process participation
3. `READ gitnexus://repo/EoH/process/{processName}` — trace the full execution flow step by step
4. For regressions: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})` — see what your branch changed

## When Refactoring

- **Renaming**: MUST use `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` first. Review the preview — graph edits are safe, text_search edits need manual review. Then run with `dry_run: false`.
- **Extracting/Splitting**: MUST run `gitnexus_context({name: "target"})` to see all incoming/outgoing refs, then `gitnexus_impact({target: "target", direction: "upstream"})` to find all external callers before moving code.
- After any refactor: run `gitnexus_detect_changes({scope: "all"})` to verify only expected files changed.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Tools Quick Reference

| Tool | When to use | Command |
|------|-------------|---------|
| `query` | Find code by concept | `gitnexus_query({query: "auth validation"})` |
| `context` | 360-degree view of one symbol | `gitnexus_context({name: "validateUser"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "X", direction: "upstream"})` |
| `detect_changes` | Pre-commit scope check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe multi-file rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |
| `cypher` | Custom graph queries | `gitnexus_cypher({query: "MATCH ..."})` |

## Impact Risk Levels

| Depth | Meaning | Action |
|-------|---------|--------|
| d=1 | WILL BREAK — direct callers/importers | MUST update these |
| d=2 | LIKELY AFFECTED — indirect deps | Should test |
| d=3 | MAY NEED TESTING — transitive | Test if critical path |

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/EoH/context` | Codebase overview, check index freshness |
| `gitnexus://repo/EoH/clusters` | All functional areas |
| `gitnexus://repo/EoH/processes` | All execution flows |
| `gitnexus://repo/EoH/process/{name}` | Step-by-step execution trace |

## Self-Check Before Finishing

Before completing any code modification task, verify:
1. `gitnexus_impact` was run for all modified symbols
2. No HIGH/CRITICAL risk warnings were ignored
3. `gitnexus_detect_changes()` confirms changes match expected scope
4. All d=1 (WILL BREAK) dependents were updated

## Keeping the Index Fresh

After committing code changes, the GitNexus index becomes stale. Re-run analyze to update it:

```bash
npx gitnexus analyze
```

If the index previously included embeddings, preserve them by adding `--embeddings`:

```bash
npx gitnexus analyze --embeddings
```

To check whether embeddings exist, inspect `.gitnexus/meta.json` — the `stats.embeddings` field shows the count (0 means no embeddings). **Running analyze without `--embeddings` will delete any previously generated embeddings.**

> Claude Code users: A PostToolUse hook handles this automatically after `git commit` and `git merge`.

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

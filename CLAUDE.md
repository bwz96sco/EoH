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

## Important Notes

- Always set LLM credentials before running examples
- Results and logs are saved to automatically created output folders
- The framework supports both remote LLM APIs and local LLM deployment
- Each problem requires specific heuristic function signatures for evaluation
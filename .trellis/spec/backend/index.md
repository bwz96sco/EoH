# Backend Development Guidelines

> Best practices for backend development in the EoH project.

---

## Overview

EoH (Evolution of Heuristics) is a Python framework that combines Evolutionary Computation with LLMs for automatic algorithm design. The core package lives at `eoh/src/eoh/`. These guidelines document the actual conventions observed in the codebase.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Package layout, operator/module split, plugin directories, custom-problem examples | Filled |
| [Data Persistence](./database-guidelines.md) | File-backed runtime artifacts, checkpoint/resume, canonical ABR run trees, seed cache | Filled |
| [Error Handling](./error-handling.md) | Layered timeouts, subprocess isolation, diagnostics JSONL, None/error propagation | Filled |
| [Quality Guidelines](./quality-guidelines.md) | Code style, operator-extension contracts, strategy-module patterns, review checklist | Filled |
| [Logging Guidelines](./logging-guidelines.md) | print()-based console output, debug mode, structured diagnostics, meta tracking | Filled |

---

## Quick Reference

- **Python**: >= 3.10, managed with `uv`
- **No database**: File-based JSON storage only
- **No logging module**: `print()` exclusively
- **No test framework**: Manual testing only
- **Error signal**: `None` (not exceptions)
- **Config**: `Paras` class with `set_paras(**kwargs)`
- **Parallelism**: joblib + `multiprocessing.Process`
- **Operator system**: `Evolution.get_prompt_*()` + `InterfaceEC._get_alg()` + configurable `ec_operators`
- **Diagnostics**: optional timeout JSONL plus `last_request_meta` / `last_generation_meta`

---

**Language**: All documentation is written in **English**.

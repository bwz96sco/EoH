# Backend Development Guidelines

> Best practices for backend development in the EoH project.

---

## Overview

EoH (Evolution of Heuristics) is a Python framework that combines Evolutionary Computation with LLMs for automatic algorithm design. The core package lives at `eoh/src/eoh/`. These guidelines document the actual conventions observed in the codebase.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Package layout, module organization, how to add components | Filled |
| [Data Persistence](./database-guidelines.md) | File-based storage (JSON/pickle), output structure, checkpointing | Filled |
| [Error Handling](./error-handling.md) | Layered error suppression, None as error signal, retry patterns | Filled |
| [Quality Guidelines](./quality-guidelines.md) | Code style, architecture patterns, forbidden patterns, review checklist | Filled |
| [Logging Guidelines](./logging-guidelines.md) | print()-based output, debug mode, file output formats | Filled |

---

## Quick Reference

- **Python**: >= 3.10, managed with `uv`
- **No database**: File-based JSON storage only
- **No logging module**: `print()` exclusively
- **No test framework**: Manual testing only
- **Error signal**: `None` (not exceptions)
- **Config**: `Paras` class with `set_paras(**kwargs)`
- **Parallelism**: joblib + concurrent.futures

---

**Language**: All documentation is written in **English**.

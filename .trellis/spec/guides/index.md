# Thinking Guides

> **Purpose**: EoH-specific pre-implementation checklists for extension work, experiment runners, and runtime contract changes.

---

## Why These Guides Exist

EoH bugs usually come from **missed registration points and drift between layers**, not from syntax errors:

- `Paras` changes do not automatically propagate into factories or runners
- prompt contracts can drift away from evaluator expectations
- method and strategy modules look interchangeable until their call signatures diverge
- example runners often carry the only working integration path for a feature

These guides are short decision aids for the actual seams in this repo: `Paras`, `EVOL`, `Probs`, `Methods`, `EOH`/`AEL`/`LS`, `InterfaceEC`, `Evolution`, `InterfaceLLM`, and the example problems under `examples/`.

---

## Available Guides

| Guide | Purpose | When to Use |
|-------|---------|-------------|
| [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md) | Find the existing EoH pattern before copying files or loops | New method/problem/operator/backend, or repeated logic in `eoh/src/eoh/` and `examples/` |
| [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md) | Trace config, prompt, LLM, evaluation, and persistence boundaries | Any change that crosses `Paras`, registries, prompts, evaluation, or output layout |
| [Cross-Platform Thinking Guide](./cross-platform-thinking-guide.md) | Catch multiprocessing, path, env, and endpoint portability risks | Scripts, subprocesses, `joblib`, local/remote LLM backends, path handling |
| [Extending EoH](./extending-eoh.md) | Central checklist for adding new extension points | New problem domain, method, operator, strategy, or LLM backend |

---

## Quick Reference: Thinking Triggers

### When to Think About Cross-Layer Issues

- [ ] You are changing any field or default in `eoh/src/eoh/utils/getParas.py:7-133`
- [ ] You are registering or renaming a problem in `eoh/src/eoh/problems/problems.py:6-25`
- [ ] You are registering or renaming a method, selection strategy, or management strategy in `eoh/src/eoh/methods/methods.py:6-51`
- [ ] You are widening a prompt/evaluator contract such as ABR `state` / `ctx`
- [ ] You are changing output layout, checkpoint paths, or experiment wrappers

→ Read [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md)

### When to Think About Code Reuse

- [ ] You are adding a new method and are tempted to copy `EOH`, `AEL`, or `LS`
- [ ] You are adding a new problem and there is already a similar one in `eoh/src/eoh/problems/` or `examples/user_*`
- [ ] You are adding a new operator string or prompt builder
- [ ] You are creating a new selection or management module
- [ ] You are modifying config names, output schema, or helper utilities

→ Read [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md)

### When to Think About Cross-Platform Issues

- [ ] You are touching `multiprocessing`, `joblib`, or subprocess-based evaluation
- [ ] You are adding or changing path logic in example runners or experiment scripts
- [ ] You are switching between local and remote LLM backends
- [ ] You are loading `.env` files or importing external code from `env/`

→ Read [Cross-Platform Thinking Guide](./cross-platform-thinking-guide.md)

### When to Read Extending EoH

- [ ] You are adding a new built-in problem
- [ ] You are adding a new user-defined problem example
- [ ] You are adding a new evolution method or EC operator
- [ ] You are adding a new selection / management strategy
- [ ] You are adding a new LLM adapter or backend selection branch

→ Read [Extending EoH](./extending-eoh.md)

---

## Pre-Modification Rule

> **Search the registry, dispatch point, and example runner before editing.**

```bash
# Registry and strategy wiring
rg -n "get_method|selection ==|management ==" eoh/src/eoh/methods eoh/src/eoh/utils

# Problem registration and prompt/evaluator contracts
rg -n "self\\.prompts|def evaluate|def evaluate_with_details|problem =" eoh/src/eoh/problems examples

# Operator strings and prompt builders
rg -n "ec_operators|get_prompt_|operator ==" eoh/src/eoh examples
```

This catches most "updated one layer, forgot the other two" failures.

---

## How to Use This Directory

1. Skim the relevant guide before editing code or example runners.
2. Use the file-and-line references to inspect the current working pattern, not a remembered one.
3. If you discover a new repo-specific trap, add it here as a checklist item with a concrete file reference.

---

**Core Principle**: In EoH, search-before-edit is cheaper than debugging factory drift later.

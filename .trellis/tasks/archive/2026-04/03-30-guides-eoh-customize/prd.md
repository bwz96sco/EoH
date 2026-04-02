# Customize Thinking Guides for EoH-Specific Patterns

## Goal

Transform the generic thinking guides under `.trellis/spec/guides/` into EoH-specific development guides. Replace generic advice with real examples from the EoH codebase using ABCoder and GitNexus analysis.

## Context

EoH (Evolution of Heuristics) is a Python framework combining Evolutionary Computation with LLMs. The core source lives at `eoh/src/eoh/`.

### Key Extension Points (Where Developers Add Code)

1. **New Evolution Method**: Add to `methods/` — implement a class with `run()`, register in `Methods.get_method()` factory
2. **New Problem Domain**: Add to `problems/optimization/` or `problems/machinelearning/` — implement evaluation + prompts, register in `Probs.__init__()`
3. **New EC Operator**: Add `get_prompt_XX()` to `Evolution`, add case to `InterfaceEC._get_alg()`, register in `Paras.set_ec()`
4. **New Selection Strategy**: Add module to `methods/selection/`, import in `Methods.__init__()`
5. **New Management Strategy**: Add module to `methods/management/`, import in `Methods.__init__()`
6. **New LLM Backend**: Add to `llm/`, integrate in `InterfaceLLM.__init__()`

### Architecture Call Chain

```
EVOL.run()
  → Probs(paras).get_problem()
  → Methods(paras, problem).get_method()
    → EOH.__init__(paras, problem, select, manage)
    → EOH.run()
      → InterfaceEC.__init__(...)
      → InterfaceEC.population_generation()  [or seed/continue]
      → for each generation:
          → InterfaceEC.get_algorithm(population, operator)
            → Parallel: InterfaceEC.get_offspring(...)
              → Evolution._get_alg(prompt)
                → InterfaceLLM.get_response(prompt)
                  → InterfaceAPI.get_response(prompt)  [HTTP + retry]
                → regex parse → [code, algorithm]
              → _evaluate_with_timeout(code)
                → subprocess: interface_eval.evaluate(code)
              → fitness, other_inf → offspring dict
          → add2pop(population, offsprings)
          → population_management(population, size)
          → save population JSON
```

### Common Code Patterns in EoH

1. **Factory Pattern**: `Methods.get_method()`, `Probs.__init__()` — if/elif chains selecting implementations
2. **Strategy Pattern**: Selection and Management modules plugged via `self.select` / `self.manage`
3. **Prompt Template Pattern**: `Evolution.get_prompt_XX()` methods building LLM prompts from problem metadata
4. **Subprocess Evaluation**: `multiprocessing.Process` + `Queue` for safe code execution with timeout
5. **None-as-error**: Functions return `None` on failure instead of raising exceptions

## Tools Available

You have two MCP servers configured — use both for accurate specs:

### ABCoder MCP (symbol-level: AST nodes, signatures, cross-file deps)
| Tool | Purpose | Example |
|------|---------|---------|
| `list_repos` | List parsed repositories | `list_repos()` |
| `get_repo_structure` | Full file listing | `get_repo_structure({repo_name: "/Users/zhangbowen/Projects/EoH/eoh/src/eoh"})` |
| `get_package_structure` | Nodes within a package | `get_package_structure({repo_name: "...", mod_path: "current", package_path: "methods.eoh.eoh"})` |
| `get_file_structure` | All nodes in a file | `get_file_structure({repo_name: "...", file_path: "methods/eoh/eoh.py"})` |
| `get_ast_node` | Code + deps + refs | `get_ast_node({repo_name: "...", node_ids: [{mod_path: "current", pkg_path: "methods.eoh.eoh", name: "EOH"}]})` |

### GitNexus MCP (architecture-level: clusters, execution flows, impact)
| Tool | Purpose | Example |
|------|---------|---------|
| `gitnexus_query` | Find execution flows by concept | `gitnexus_query({query: "add new problem"})` |
| `gitnexus_context` | 360-degree symbol view | `gitnexus_context({name: "Methods"})` |
| `gitnexus_impact` | Blast radius analysis | `gitnexus_impact({target: "Probs", direction: "upstream"})` |
| `gitnexus_cypher` | Direct graph queries | `gitnexus_cypher({query: "MATCH (n:Class) RETURN n.name, n.file LIMIT 30"})` |

### Recommended Workflow
1. GitNexus first — find execution flows for each extension point
2. ABCoder second — get exact signatures and code for referenced classes
3. Read example files — `examples/bp_online/`, `examples/tsp_construct/`, `examples/user_abr/`
4. Write guides — with real code from steps 2-3

## Files to Create/Update

### `.trellis/spec/guides/code-reuse-thinking-guide.md` (rewrite)
Replace generic advice with EoH-specific reuse patterns:
- The factory pattern reuse (Methods, Probs)
- The strategy pattern reuse (Selection, Management)
- The prompt template pattern reuse (Evolution.get_prompt_XX)
- Common anti-pattern: copy-pasting operator code instead of extending the pattern
- Checklist: before creating a new file, search for existing similar patterns

### `.trellis/spec/guides/cross-layer-thinking-guide.md` (rewrite)
Replace generic advice with EoH-specific layer boundaries:
- Layer 1: Config (`Paras`) → Layer 2: Orchestration (`EVOL`, `Methods`, `Probs`) → Layer 3: Evolution (`EOH`, `InterfaceEC`) → Layer 4: LLM (`Evolution`, `InterfaceLLM`) → Layer 5: Evaluation (`interface_eval`)
- Data flow: how `Paras` config flows through all layers
- Common mistakes: modifying `Paras` after init, forgetting to register new methods in the factory

### `.trellis/spec/guides/cross-platform-thinking-guide.md` (create NEW)
Note: The index references this file but it doesn't exist yet. Create it for EoH:
- Python 3.10+ features used (`match` not used, but `|` type unions are)
- `multiprocessing.fork` vs `spawn` (macOS default changed to spawn)
- File path handling (current code uses string concatenation, not `pathlib`)
- LLM API endpoint URL handling (http vs https)

### `.trellis/spec/guides/extending-eoh.md` (create NEW)
Central guide for extending EoH:
- Step-by-step: Adding a new problem domain
- Step-by-step: Adding a new evolution method
- Step-by-step: Adding a new EC operator
- Step-by-step: Adding a new LLM backend
- Registration points checklist (which factories to update)
- Test procedure (how to verify with `runEoH.py`)

### `.trellis/spec/guides/index.md` (update)
- Update the index to reflect the actual files created
- Remove references to files that don't exist
- Add new files

## Important Rules

### Spec files are NOT fixed — adapt to reality
- Delete template files that don't apply
- Create new files for patterns the templates don't cover
- Rename files if template names don't fit
- Update index.md to reflect the final set

### Parallel agents — stay in your lane
- ONLY modify files under `.trellis/spec/guides/`
- DO NOT modify source code, other spec directories, or task files
- DO NOT run git commands
- You may read any file for analysis

## Acceptance Criteria

- [ ] Real code examples from the actual codebase (with file paths and line numbers)
- [ ] All 6 extension points documented with step-by-step instructions
- [ ] Call chain documented with actual class/method names
- [ ] Anti-patterns documented (based on existing code smells)
- [ ] Cross-platform guide created (multiprocessing fork/spawn, file paths, etc.)
- [ ] No placeholder text remaining
- [ ] index.md reflects actual file set

## Technical Notes

- **Language**: Python >= 3.10
- **Package manager**: `uv`
- **Run examples**: `uv run python examples/<problem>/runEoH.py`
- **ABCoder repo_name**: `/Users/zhangbowen/Projects/EoH/eoh/src/eoh`
- **Key examples to reference**: `examples/bp_online/`, `examples/tsp_construct/`, `examples/user_abr/`

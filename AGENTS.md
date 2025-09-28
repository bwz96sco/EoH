# Repository Guidelines

## Project Structure & Module Organization
- Source code: `eoh/src/eoh/` (core framework).
  - `methods/` (eoh, ael, localsearch), `problems/` (optimization, machinelearning), `llm/`, `utils/`, `test/`.
- Examples: `examples/` (e.g., `tsp_construct`, `bp_online`, `user_*`).
- Docs & assets: `docs/`.
- Baselines: `baseline/` (for comparisons).
- Outputs: `results/` (created by runs/evaluations).

## Build, Test, and Development Commands
- Setup env: `uv sync`
- Install project (editable): `uv pip install -e eoh`
- Run example (bin packing): `uv run python examples/bp_online/runEoH.py`
- Run example (TSP): `uv run python examples/tsp_construct/runEoH.py`
- Evaluate results: copy your heuristic to `examples/{problem}/evaluation/heuristic.py`, then run
  `uv run python examples/{problem}/evaluation/runEval.py`
- Start local LLM server (example):
  `uv run python eoh/src/eoh/llm_local_server/gemma_instruct_server.py`

## Coding Style & Naming Conventions
- Python ≥ 3.10; follow PEP 8; 4‑space indentation.
- Names: modules/functions `snake_case`, classes `CamelCase`, constants `UPPER_SNAKE_CASE`.
- Place new problems under `eoh/src/eoh/problems/<domain>/<problem>/` and examples under `examples/user_<task>/`.
- Keep heuristics’ function signatures consistent with each evaluation block.

## Testing Guidelines
- Primary checks are example evaluations under `examples/*/evaluation/` and the smoke script via `uv run python eoh/src/eoh/test/run.py` (set API creds before running).
- Prefer deterministic seeds where possible; include small test datasets in `examples/.../TestingData`.
- Add minimal repro instructions in PRs (commands used, files touched).

## Commit & Pull Request Guidelines
- Commits: concise, imperative (e.g., "Add bp_online heuristic", "Refactor selection.roulette_wheel").
- PRs must include: clear description, linked issues, commands to reproduce runs, brief result summary (metrics/logs), and paths changed.
- Exclude secrets and large artifacts; keep outputs in `results/` or example‑local folders.

## Security & Configuration Tips
- Never hardcode LLM keys. Prefer env vars (e.g., `LLM_API_ENDPOINT`, `LLM_API_KEY`, `LLM_MODEL`) and pass them to `Paras.set_paras(...)`.
- For local models, run a server from `llm_local_server/` and point `llm_api_endpoint` to the local URL.

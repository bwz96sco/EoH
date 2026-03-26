from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from eoh import eoh
from eoh.utils.getParas import Paras

from prob import ABRProblem


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    experiments_dir = repo_root / "experiments"
    if str(experiments_dir) not in sys.path:
        sys.path.insert(0, str(experiments_dir))

    from run_layout import build_eoh_output_root, build_run_layout

    seed_path: Path | None = None

    dataset = os.environ.get("DATASET", "FCC-18")
    output_name = os.environ.get("ABR_OUTPUT_NAME", dataset)
    run_layout = build_run_layout(repo_root)
    output_root = build_eoh_output_root(repo_root, output_name=output_name, run_id=run_layout.run_id)

    print(f"Dataset: {dataset}")
    print(f"ABR run id: {run_layout.run_id}")
    print(f"Canonical EoH output root: {output_root}")

    problem = ABRProblem(
        trace_split="train",
        dataset=dataset,
    )
    paras = Paras()

    # Seed cache: skip expensive seed evaluation if we already have results.
    cache_dir = Path(__file__).resolve().parent / "seed_cache" / dataset
    cache_file = cache_dir / "population_generation_0.json"
    use_cache = cache_file.exists() and not _env_flag("SEED_NO_CACHE")

    if use_cache:
        print(f"Using cached seed population: {cache_file}")

    # Seed population via the built-in `exp_use_seed` mechanism.
    seeds = problem.prompts.get_seed_heuristics()
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix="-user-abr-seeds.json",
        encoding="utf-8",
        delete=False,
    ) as seed_file:
        json.dump(seeds, seed_file, indent=2)
        seed_path = Path(seed_file.name)

    try:
        paras_kwargs = dict(
            method="eoh",
            problem=problem,
            llm_use_local=_env_flag("LLM_USE_LOCAL", default=False),
            llm_local_url=os.environ.get("LLM_LOCAL_URL"),
            llm_api_endpoint=os.environ.get("LLM_API_ENDPOINT"),
            llm_api_key=os.environ.get("LLM_API_KEY"),
            llm_model=os.environ.get("LLM_MODEL"),
            ec_pop_size=len(seeds),
            ec_n_pop=int(os.environ.get("EC_N_POP", "10")),
            ec_operators=["e1", "e2", "m1", "m2", "m3"],
            exp_n_proc=int(os.environ.get("EXP_N_PROC", "4")),
            exp_debug_mode=_env_flag("EXP_DEBUG_MODE", default=False),
            eva_timeout=int(os.environ.get("EVA_TIMEOUT", "300")),
            exp_output_path=str(output_root),
            eva_numba_decorator=False,
        )

        if use_cache:
            # Load cached seed population, skip seed evaluation entirely.
            paras_kwargs["exp_use_seed"] = False
            paras_kwargs["exp_use_continue"] = True
            paras_kwargs["exp_continue_path"] = str(cache_file)
            paras_kwargs["exp_continue_id"] = 1  # start from gen 1
        else:
            paras_kwargs["exp_use_seed"] = True
            paras_kwargs["exp_seed_path"] = str(seed_path)

        paras.set_paras(**paras_kwargs)

        evolution = eoh.EVOL(paras)
        evolution.run()

        # After first successful run, cache the seed population for future runs.
        if not use_cache:
            _cache_seed_population(paras_kwargs["exp_output_path"], cache_dir)

    finally:
        if seed_path is not None:
            seed_path.unlink(missing_ok=True)


def _cache_seed_population(output_path: str, cache_dir: Path) -> None:
    """Copy population_generation_0.json to cache for future reuse."""
    import glob

    # Find the actual output directory (EoH creates a timestamped subfolder)
    pattern = os.path.join(output_path, "*/results/pops/population_generation_0.json")
    matches = sorted(glob.glob(pattern))
    if not matches:
        print("Warning: could not find population_generation_0.json to cache")
        return

    src = Path(matches[-1])  # latest run
    cache_dir.mkdir(parents=True, exist_ok=True)
    dst = cache_dir / "population_generation_0.json"
    shutil.copy2(src, dst)
    print(f"Seed population cached to {dst}")


if __name__ == "__main__":
    main()

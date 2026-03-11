from __future__ import annotations

import json
import os
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
    seed_path: Path | None = None

    dataset = os.environ.get("DATASET", "FCC-18")
    print(f"Dataset: {dataset}")

    problem = ABRProblem(
        trace_split="train",
        dataset=dataset,
    )
    paras = Paras()

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
        paras.set_paras(
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
            eva_timeout=int(os.environ.get("EVA_TIMEOUT", "120")),
            exp_use_seed=True,
            exp_seed_path=str(seed_path),
            exp_output_path=str(repo_root),
            eva_numba_decorator=False,
        )

        evolution = eoh.EVOL(paras)
        evolution.run()
    finally:
        if seed_path is not None:
            seed_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()

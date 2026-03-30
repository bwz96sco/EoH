from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from eoh import eoh
from eoh.utils.getParas import Paras

from prob import ABRProblem


_SAFE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9._+\-]+")


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _sanitize_component(value: str | None, default: str) -> str:
    if not value:
        return default

    sanitized = _SAFE_COMPONENT_RE.sub("-", value.strip())
    sanitized = sanitized.strip(".-_+")
    return sanitized or default


def _split_env_list(name: str) -> list[str]:
    value = os.environ.get(name)
    if value is None:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _resolve_selected_seeds(
    seeds: list[dict[str, str]],
) -> tuple[list[dict[str, str]], str, str]:
    selected_names = _split_env_list("ABR_SEED_NAME")
    selected_indices_raw = _split_env_list("ABR_SEED_INDEX")

    if selected_names and selected_indices_raw:
        raise ValueError("Set only one of ABR_SEED_NAME or ABR_SEED_INDEX.")

    if not selected_names and not selected_indices_raw:
        return seeds, "all built-in seeds", "all-seeds"

    if selected_names:
        seeds_by_name = {
            str(seed.get("name", "")).strip(): dict(seed)
            for seed in seeds
            if str(seed.get("name", "")).strip()
        }
        selected: list[dict[str, str]] = []
        resolved_names: list[str] = []
        seen_names: set[str] = set()

        for raw_name in selected_names:
            if raw_name not in seeds_by_name:
                available = ", ".join(sorted(seeds_by_name))
                raise ValueError(
                    f"Unknown ABR_SEED_NAME '{raw_name}'. Available seed names: {available}"
                )
            if raw_name in seen_names:
                continue
            selected.append(dict(seeds_by_name[raw_name]))
            resolved_names.append(raw_name)
            seen_names.add(raw_name)

        mode_label = f"seed name(s): {', '.join(resolved_names)}"
        mode_slug = "name-" + "-".join(
            _sanitize_component(name, "seed") for name in resolved_names
        )
        return selected, mode_label, mode_slug

    selected: list[dict[str, str]] = []
    resolved_indices: list[int] = []
    seen_indices: set[int] = set()

    for raw_index in selected_indices_raw:
        try:
            index = int(raw_index)
        except ValueError as exc:
            raise ValueError(
                f"ABR_SEED_INDEX must be an integer, got '{raw_index}'."
            ) from exc

        if index < 0 or index >= len(seeds):
            raise ValueError(
                f"ABR_SEED_INDEX {index} is out of range for {len(seeds)} seeds."
            )
        if index in seen_indices:
            continue

        selected.append(dict(seeds[index]))
        resolved_indices.append(index)
        seen_indices.add(index)

    selected_seed_names = [
        str(seed.get("name", f"seed-{index}"))
        for index, seed in zip(resolved_indices, selected)
    ]
    mode_label = (
        f"seed index(es): {', '.join(str(index) for index in resolved_indices)} "
        f"({', '.join(selected_seed_names)})"
    )
    mode_slug = "idx-" + "-".join(str(index) for index in resolved_indices)
    return selected, mode_label, mode_slug


def _build_seed_cache_dir(dataset: str, seed_mode_slug: str) -> Path:
    seed_cache_root = Path(__file__).resolve().parent / "seed_cache"
    if seed_mode_slug == "all-seeds":
        return seed_cache_root / dataset
    return seed_cache_root / dataset / seed_mode_slug


def _resolve_target_pop_size(default_pop_size: int) -> int:
    raw_value = os.environ.get("EC_POP_SIZE")
    if raw_value is None or not raw_value.strip():
        return default_pop_size

    try:
        pop_size = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"EC_POP_SIZE must be an integer, got '{raw_value}'.") from exc

    if pop_size < 1:
        raise ValueError(f"EC_POP_SIZE must be >= 1, got {pop_size}.")
    return pop_size


def _expand_seed_population(
    seeds: list[dict[str, str]],
    target_pop_size: int,
) -> list[dict[str, str]]:
    if not seeds:
        raise ValueError("At least one seed is required to build the initial population.")

    if target_pop_size == len(seeds):
        return [dict(seed) for seed in seeds]

    expanded: list[dict[str, str]] = []
    name_counts: dict[str, int] = {}
    for index in range(target_pop_size):
        seed = dict(seeds[index % len(seeds)])
        base_name = str(seed.get("name", f"seed-{index % len(seeds)}")).strip() or f"seed-{index % len(seeds)}"
        copy_count = name_counts.get(base_name, 0) + 1
        name_counts[base_name] = copy_count
        if copy_count > 1:
            seed["name"] = f"{base_name}-copy-{copy_count}"
        expanded.append(seed)
    return expanded


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    experiments_dir = repo_root / "experiments"
    if str(experiments_dir) not in sys.path:
        sys.path.insert(0, str(experiments_dir))

    from run_layout import build_eoh_output_root, build_log_path, build_run_layout

    seed_path: Path | None = None

    dataset = os.environ.get("DATASET", "FCC-18")
    output_name = os.environ.get("ABR_OUTPUT_NAME", dataset)
    run_layout = build_run_layout(repo_root)
    output_root = build_eoh_output_root(repo_root, output_name=output_name, run_id=run_layout.run_id)
    timeout_diagnostics_path = build_log_path(
        repo_root,
        log_name="timeout_diagnostics",
        run_id=run_layout.run_id,
    )

    print(f"Dataset: {dataset}")
    print(f"ABR run id: {run_layout.run_id}")
    print(f"Canonical EoH output root: {output_root}")

    problem = ABRProblem(
        trace_split="train",
        dataset=dataset,
    )
    paras = Paras()

    all_seeds = [dict(seed) for seed in problem.prompts.get_seed_heuristics()]
    seeds, seed_mode_label, seed_mode_slug = _resolve_selected_seeds(all_seeds)
    target_pop_size = _resolve_target_pop_size(len(seeds))
    if target_pop_size != len(seeds):
        seed_mode_label = f"{seed_mode_label}; expanded to population size {target_pop_size}"
        seed_mode_slug = f"{seed_mode_slug}-pop-{target_pop_size}"
        seeds = _expand_seed_population(seeds, target_pop_size)

    selected_seed_names = [
        str(seed.get("name", f"seed-{index}")) for index, seed in enumerate(seeds)
    ]

    # Seed cache: skip expensive seed evaluation if we already have results.
    cache_dir = _build_seed_cache_dir(dataset, seed_mode_slug)
    cache_file = cache_dir / "population_generation_0.json"
    use_cache = cache_file.exists() and not _env_flag("SEED_NO_CACHE")

    print(f"Seed mode: {seed_mode_label}")
    print(f"Selected seed names: {', '.join(selected_seed_names)}")
    print(f"Seed cache directory: {cache_dir}")

    if use_cache:
        print(f"Using cached seed population: {cache_file}")

    # Seed population via the built-in `exp_use_seed` mechanism.
    temp_seed_dir = (
        Path(__file__).resolve().parent
        / "seed_cache"
        / "_seed_specs"
        / dataset
        / seed_mode_slug
    )
    temp_seed_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=temp_seed_dir,
        prefix="selected-",
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
            ec_pop_size=target_pop_size,
            ec_n_pop=int(os.environ.get("EC_N_POP", "10")),
            ec_operators=["e1", "e2", "m1", "m2", "m3"],
            exp_n_proc=int(os.environ.get("EXP_N_PROC", "4")),
            exp_debug_mode=_env_flag("EXP_DEBUG_MODE", default=False),
            eva_timeout=int(os.environ.get("EVA_TIMEOUT", "300")),
            exp_output_path=str(output_root),
            exp_timeout_diagnostics=_env_flag("EOH_TIMEOUT_DIAGNOSTICS", default=False),
            exp_timeout_diagnostics_path=str(timeout_diagnostics_path),
            abr_run_id=run_layout.run_id,
            llm_request_timeout_s=int(os.environ.get("LLM_REQUEST_TIMEOUT_S", "30")),
            llm_total_timeout_s=int(os.environ.get("LLM_TOTAL_TIMEOUT_S", "90")),
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

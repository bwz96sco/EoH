"""Evaluate an evolved ABR heuristic on test traces.

Usage:
    1. Copy your evolved heuristic into evaluation/heuristic.py
    2. Set DATASET in .env (or leave default from SABR config)
    3. Run: uv run python examples/user_abr/evaluation/runEval.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Ensure the parent directory is importable.
_PARENT = str(Path(__file__).resolve().parent.parent)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from prob import ABRProblem


def main() -> None:
    dataset = os.environ.get("DATASET")
    problem = ABRProblem(trace_split="test", dataset=dataset)

    code = (Path(__file__).resolve().parent / "heuristic.py").read_text()
    fitness, feedback = problem.evaluate_with_details(code)

    if fitness is None:
        print("Evaluation FAILED — heuristic returned invalid results.")
        return

    print(f"Dataset:           {dataset or '(SABR config default)'}")
    print(f"Fitness (neg QoE): {fitness:.5f}")
    print(f"QoE:               {-fitness:.5f}")
    print()
    print(feedback)


if __name__ == "__main__":
    main()

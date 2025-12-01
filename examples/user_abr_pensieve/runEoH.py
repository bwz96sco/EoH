"""
EoH runner for evolving Pensieve state features and network architecture.

This script configures and runs the Evolution of Heuristics (EoH) framework
to automatically discover optimal state representations and neural network
architectures for adaptive bitrate streaming.

Usage:
    python runEoH.py

Note: Each evaluation requires full RL training (~110K epochs), so this
process takes significant time. Consider running overnight or on a server.
"""

import os

from eoh import eoh
from eoh.utils.getParas import Paras
from prob import ABRPensieve

# Parameter initialization
paras = Paras()

# Set your local problem instance
problem_local = ABRPensieve()

# Get seed path relative to this file
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_SEED_PATH = os.path.join(_THIS_DIR, "seed.json")

# Configure parameters
# Note: Conservative settings due to expensive evaluations (full RL training per candidate)
paras.set_paras(
    method="eoh",                    # Evolution of Heuristics
    problem=problem_local,
    llm_api_endpoint="aihubmix.com", # Set your LLM endpoint
    llm_api_key="sk-mESrY9qAd0QiCBPTA4607c1a4f794bF69085948f6cD09a01",      # Set your API key
    llm_model="o3-mini",             # LLM model to use
    ec_pop_size=4,                   # Small population (each eval takes hours)
    ec_n_pop=4,                      # Few generations
    exp_n_proc=1,                    # Single process (training is resource-intensive)
    exp_debug_mode=False,
    eva_numba_decorator=False,       # No numba (PyTorch code)
    exp_use_seed=True,               # Use seed heuristic for initial population
    exp_seed_path=_SEED_PATH,        # Path to seed.json
    eva_timeout=36000,               # 10 hours timeout (RL training takes long)
)

# Initialization
evolution = eoh.EVOL(paras)

# Run evolution
if __name__ == "__main__":
    print("=" * 60)
    print("EoH: Evolving Pensieve State Features & Network Architecture")
    print("=" * 60)
    print(f"Population size: {paras.ec_pop_size}")
    print(f"Number of generations: {paras.ec_n_pop}")
    print("Training epochs per evaluation: 10,000")
    print("=" * 60)
    print("\nStarting evolution... (this will take a long time)")
    print()
    
    evolution.run()


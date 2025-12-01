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

from eoh import eoh
from eoh.utils.getParas import Paras
from prob import ABRPensieve

# Parameter initialization
paras = Paras()

# Set your local problem instance
problem_local = ABRPensieve()

# Configure parameters
# Note: Conservative settings due to expensive evaluations (full RL training per candidate)
paras.set_paras(
    method="eoh",                    # Evolution of Heuristics
    problem=problem_local,
    llm_api_endpoint="aihubmix.com", # Set your LLM endpoint
    llm_api_key="YOUR_API_KEY",      # Set your API key
    llm_model="o3-mini",             # LLM model to use
    ec_pop_size=2,                   # Small population (each eval takes hours)
    ec_n_pop=4,                      # Few generations
    exp_n_proc=1,                    # Single process (training is resource-intensive)
    exp_debug_mode=False,
    eva_numba_decorator=False,       # No numba (PyTorch code)
)

# Initialization
evolution = eoh.EVOL(paras)

# Run evolution
if __name__ == "__main__":
    print("=" * 60)
    print("EoH: Evolving Pensieve State Features & Network Architecture")
    print("=" * 60)
    print(f"Population size: {paras.pop_size}")
    print(f"Number of generations: {paras.n_pop}")
    print(f"Training epochs per evaluation: 110,000")
    print("=" * 60)
    print("\nStarting evolution... (this will take a long time)")
    print()
    
    evolution.run()


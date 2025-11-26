from eoh import eoh
from eoh.utils.getParas import Paras
from prob import ABRBuffer

# Parameter initialization
paras = Paras()

# Set your local problem instance
problem_local = ABRBuffer()

# Configure parameters
paras.set_paras(
    method="eoh",  # ['ael', 'eoh']
    problem=problem_local,
    llm_api_endpoint="aihubmix.com",  # set your LLM endpoint
    llm_api_key="sk-mESrY9qAd0QiCBPTA4607c1a4f794bF69085948f6cD09a01",  # set your key
    llm_model="o3-mini",
    ec_pop_size=4,  # number of samples in each population
    ec_n_pop=4,  # number of populations
    exp_n_proc=4,  # multi-core parallel
    exp_debug_mode=False,
    eva_numba_decorator=False,
)

# Initialization
evolution = eoh.EVOL(paras)

# Run
evolution.run()


import os
from eoh import eoh
from eoh.utils.getParas import Paras

# Parameter initilization #
paras = Paras()

# Adjust parameters for debugging if environment variable is set
#debug_single_proc = os.getenv('EOH_DEBUG_SINGLE_PROC', '0') == '1'
debug_single_proc = True

# Set parameters #
paras.set_paras(method = "eoh",    # ['ael','eoh']
                problem = "bp_online", #['tsp_construct','bp_online']
                llm_api_endpoint = "aihubmix.com", # set your LLM endpoint
                llm_api_key = "sk-mESrY9qAd0QiCBPTA4607c1a4f794bF69085948f6cD09a01",   # set your key
                llm_model = "gpt-3.5-turbo",
                ec_pop_size = 1 if debug_single_proc else 4, # smaller for debugging
                ec_n_pop = 1 if debug_single_proc else 4,  # smaller for debugging
                exp_n_proc = 1 if debug_single_proc else 4,  # single process for debugging
                exp_debug_mode = debug_single_proc)

# initilization
evolution = eoh.EVOL(paras)

# run 
evolution.run()
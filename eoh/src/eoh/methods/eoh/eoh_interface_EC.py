import numpy as np
import multiprocessing
import time
from .eoh_evolution import Evolution
import warnings
from joblib import Parallel, delayed
from .evaluator_accelerate import add_numba_decorator
import re
from ...utils.timeout_diagnostics import summarize_timeout_records, write_timeout_record


def _empty_offspring():
    return {
        'algorithm': None,
        'code': None,
        'objective': None,
        'other_inf': None
    }


def _evaluate_worker(interface_eval, code, use_details, result_queue):
    try:
        if use_details:
            fitness, other_inf = interface_eval.evaluate_with_details(code)
        else:
            fitness = interface_eval.evaluate(code)
            other_inf = None
        result_queue.put(("ok", fitness, other_inf, None))
    except Exception as exc:
        result_queue.put(("error", None, None, f"{type(exc).__name__}: {exc}"))

class InterfaceEC():
    def __init__(
        self,
        pop_size,
        m,
        api_endpoint,
        api_key,
        llm_model,
        llm_use_local,
        llm_local_url,
        debug_mode,
        interface_prob,
        select,
        n_p,
        timeout,
        use_numba,
        **kwargs,
    ):

        # LLM settings
        self.pop_size = pop_size
        self.interface_eval = interface_prob
        prompts = interface_prob.prompts
        self.llm_request_timeout_s = max(1, int(kwargs.get("llm_request_timeout_s", 60)))
        self.llm_total_timeout_s = max(self.llm_request_timeout_s, int(kwargs.get("llm_total_timeout_s", 180)))
        self.timeout_diagnostics_enabled = bool(kwargs.get("timeout_diagnostics_enabled", False))
        self.timeout_diagnostics_path = kwargs.get("timeout_diagnostics_path")
        self.run_id = kwargs.get("run_id")
        evolution_kwargs = dict(kwargs)
        evolution_kwargs["llm_request_timeout_s"] = self.llm_request_timeout_s
        evolution_kwargs["llm_total_timeout_s"] = self.llm_total_timeout_s
        self.evol = Evolution(
            api_endpoint,
            api_key,
            llm_model,
            llm_use_local,
            llm_local_url,
            debug_mode,
            prompts,
            **evolution_kwargs,
        )
        self.m = m
        self.debug = debug_mode

        if not self.debug:
            warnings.filterwarnings("ignore")

        self.select = select
        self.n_p = n_p
        
        self.timeout = timeout
        self.use_numba = use_numba
        self.parallel_timeout = self.llm_total_timeout_s + self.timeout + 15

    def _write_timeout_record(self, record):
        write_timeout_record(
            self.timeout_diagnostics_path,
            record,
            self.timeout_diagnostics_enabled,
        )

    def _diagnostic_record(
        self,
        *,
        generation,
        operator,
        offspring_index,
        root_cause,
        llm_status=None,
        llm_elapsed_ms=None,
        llm_prompt_attempts=None,
        llm_api_attempts=None,
        eval_status=None,
        eval_elapsed_ms=None,
        total_elapsed_ms=None,
        detail=None,
        event="offspring_result",
    ):
        return {
            "event": event,
            "generation": generation,
            "operator": operator,
            "offspring_index": offspring_index,
            "root_cause": root_cause,
            "run_id": self.run_id,
            "llm_status": llm_status,
            "llm_elapsed_ms": None if llm_elapsed_ms is None else round(float(llm_elapsed_ms), 3),
            "llm_prompt_attempts": llm_prompt_attempts,
            "llm_api_attempts": llm_api_attempts,
            "eval_status": eval_status,
            "eval_elapsed_ms": None if eval_elapsed_ms is None else round(float(eval_elapsed_ms), 3),
            "total_elapsed_ms": None if total_elapsed_ms is None else round(float(total_elapsed_ms), 3),
            "detail": detail,
            "phase": "offspring" if event == "offspring_result" else "worker",
        }

    def _evaluate_with_timeout(self, code):
        start_time = time.monotonic()
        use_details = hasattr(self.interface_eval, "evaluate_with_details")
        start_methods = multiprocessing.get_all_start_methods()
        ctx_name = "fork" if "fork" in start_methods else start_methods[0]
        ctx = multiprocessing.get_context(ctx_name)
        result_queue = ctx.Queue()
        process = ctx.Process(
            target=_evaluate_worker,
            args=(self.interface_eval, code, use_details, result_queue),
        )
        try:
            process.start()
        except Exception as exc:
            return None, None, {
                "status": "eval_error",
                "elapsed_ms": round((time.monotonic() - start_time) * 1000, 3),
                "detail": f"Failed to start evaluation subprocess ({ctx_name}): {type(exc).__name__}: {exc}",
            }
        process.join(timeout=self.timeout)

        if process.is_alive():
            process.terminate()
            process.join()
            return None, None, {
                "status": "eval_timeout",
                "elapsed_ms": round((time.monotonic() - start_time) * 1000, 3),
                "detail": f"Evaluation exceeded timeout={self.timeout}s and was terminated.",
            }

        if result_queue.empty():
            return None, None, {
                "status": "eval_error",
                "elapsed_ms": round((time.monotonic() - start_time) * 1000, 3),
                "detail": "Evaluation subprocess exited without returning a result.",
            }

        status, fitness, other_inf, detail = result_queue.get()
        elapsed_ms = round((time.monotonic() - start_time) * 1000, 3)
        if status != "ok":
            return None, None, {
                "status": "eval_error",
                "elapsed_ms": elapsed_ms,
                "detail": detail,
            }

        if fitness is None:
            return None, None, {
                "status": "eval_error",
                "elapsed_ms": elapsed_ms,
                "detail": "Evaluation returned None.",
            }

        return fitness, other_inf, {
            "status": "success",
            "elapsed_ms": elapsed_ms,
            "detail": None,
        }

    def timeout_summary(self):
        return summarize_timeout_records(self.timeout_diagnostics_path)
        
    def code2file(self,code):
        with open("./ael_alg.py", "w") as file:
        # Write the code to the file
            file.write(code)
        return 
    
    def add2pop(self,population,offspring):
        for ind in population:
            if ind['objective'] == offspring['objective']:
                if self.debug:
                    print("duplicated result, retrying ... ")
                return False
        population.append(offspring)
        return True
    
    def check_duplicate(self,population,code):
        for ind in population:
            if code == ind['code']:
                return True
        return False

    # def population_management(self,pop):
    #     # Delete the worst individual
    #     pop_new = heapq.nsmallest(self.pop_size, pop, key=lambda x: x['objective'])
    #     return pop_new
    
    # def parent_selection(self,pop,m):
    #     ranks = [i for i in range(len(pop))]
    #     probs = [1 / (rank + 1 + len(pop)) for rank in ranks]
    #     parents = random.choices(pop, weights=probs, k=m)
    #     return parents

    def population_generation(self):
        
        n_create = 2
        
        population = []

        for i in range(n_create):
            _,pop = self.get_algorithm([],'i1')
            for p in pop:
                population.append(p)
             
        return population
    
    def population_generation_seed(self,seeds,n_p):

        population = []
        if hasattr(self.interface_eval, "evaluate_with_details"):
            results = Parallel(n_jobs=n_p)(
                delayed(self.interface_eval.evaluate_with_details)(seed["code"])
                for seed in seeds
            )
            fitness = [r[0] for r in results]
            other_infs = [r[1] for r in results]
        else:
            fitness = Parallel(n_jobs=n_p)(
                delayed(self.interface_eval.evaluate)(seed["code"]) for seed in seeds
            )
            other_infs = [None for _ in seeds]

        for i in range(len(seeds)):
            try:
                seed_alg = {
                    'algorithm': seeds[i]['algorithm'],
                    'code': seeds[i]['code'],
                    'objective': None,
                    'other_inf': None
                }

                obj = float(fitness[i])
                seed_alg['objective'] = float(np.round(obj, 5))
                seed_alg['other_inf'] = other_infs[i]
                population.append(seed_alg)

            except Exception as e:
                print("Error in seed algorithm")
                exit()

        print("Initiliazation finished! Get "+str(len(seeds))+" seed algorithms")

        return population
    

    def _get_alg(self,pop,operator):
        offspring = {
            'algorithm': None,
            'code': None,
            'objective': None,
            'other_inf': None
        }
        if operator == "i1":
            parents = None
            [offspring['code'],offspring['algorithm']] =  self.evol.i1()            
        elif operator == "e1":
            parents = self.select.parent_selection(pop,self.m)
            [offspring['code'],offspring['algorithm']] = self.evol.e1(parents)
        elif operator == "e2":
            parents = self.select.parent_selection(pop,self.m)
            [offspring['code'],offspring['algorithm']] = self.evol.e2(parents) 
        elif operator == "m1":
            parents = self.select.parent_selection(pop,1)
            [offspring['code'],offspring['algorithm']] = self.evol.m1(parents[0])   
        elif operator == "m2":
            parents = self.select.parent_selection(pop,1)
            [offspring['code'],offspring['algorithm']] = self.evol.m2(parents[0]) 
        elif operator == "m3":
            parents = self.select.parent_selection(pop,1)
            [offspring['code'],offspring['algorithm']] = self.evol.m3(parents[0]) 
        else:
            print(f"Evolution operator [{operator}] has not been implemented ! \n") 

        return parents, offspring

    def get_offspring(self, pop, operator, generation, offspring_index):
        start_time = time.monotonic()
        p = None
        offspring = _empty_offspring()
        llm_meta = {}
        eval_meta = {}

        try:
            llm_phase_start = time.monotonic()
            p, offspring = self._get_alg(pop, operator)
            llm_meta = dict(getattr(self.evol, "last_generation_meta", {}))
            
            if self.use_numba:
                
                # Regular expression pattern to match function definitions
                pattern = r"def\s+(\w+)\s*\(.*\):"

                # Search for function definitions in the code
                match = re.search(pattern, offspring['code'])

                function_name = match.group(1)

                code = add_numba_decorator(program=offspring['code'], function_name=function_name)
            else:
                    code = offspring['code']

            n_retry= 1
            while llm_meta.get("status") == "success" and self.check_duplicate(pop, offspring['code']):
                
                n_retry += 1
                if self.debug:
                    print("duplicated code, wait 1 second and retrying ... ")
                    
                p, offspring = self._get_alg(pop, operator)
                llm_meta = dict(getattr(self.evol, "last_generation_meta", {}))

                if self.use_numba:
                    # Regular expression pattern to match function definitions
                    pattern = r"def\s+(\w+)\s*\(.*\):"

                    # Search for function definitions in the code
                    match = re.search(pattern, offspring['code'])

                    function_name = match.group(1)

                    code = add_numba_decorator(program=offspring['code'], function_name=function_name)
                else:
                    code = offspring['code']
                    
                if n_retry > 1:
                    break

            llm_meta["elapsed_ms"] = round((time.monotonic() - llm_phase_start) * 1000, 3)
            llm_meta["duplicate_retries"] = max(0, n_retry - 1)

            if llm_meta.get("status") != "success":
                raise RuntimeError(llm_meta.get("detail") or "LLM phase failed.")

            fitness, other_inf, eval_meta = self._evaluate_with_timeout(code)
            if eval_meta.get("status") != "success":
                raise RuntimeError(eval_meta.get("detail") or "Evaluation phase failed.")

            offspring['objective'] = float(np.round(float(fitness), 5))
            offspring['other_inf'] = other_inf

            self._write_timeout_record(
                self._diagnostic_record(
                    generation=generation,
                    operator=operator,
                    offspring_index=offspring_index,
                    root_cause="success",
                    llm_status=llm_meta.get("status"),
                    llm_elapsed_ms=llm_meta.get("elapsed_ms"),
                    llm_prompt_attempts=llm_meta.get("prompt_attempts"),
                    llm_api_attempts=llm_meta.get("api_attempts"),
                    eval_status=eval_meta.get("status"),
                    eval_elapsed_ms=eval_meta.get("elapsed_ms"),
                    total_elapsed_ms=(time.monotonic() - start_time) * 1000,
                )
            )

        except Exception as e:
            if not llm_meta:
                llm_meta = dict(getattr(self.evol, "last_generation_meta", {}))
                if "elapsed_ms" not in llm_meta:
                    llm_meta["elapsed_ms"] = round((time.monotonic() - start_time) * 1000, 3)
            eval_status = eval_meta.get("status")
            llm_status = llm_meta.get("status")
            if eval_status and eval_status != "success":
                root_cause = eval_status
            elif llm_status and llm_status != "success":
                root_cause = llm_status
            else:
                root_cause = "unexpected_error"
            if root_cause not in {"llm_timeout", "parse_error", "llm_error", "eval_timeout", "eval_error"}:
                root_cause = "unexpected_error"

            self._write_timeout_record(
                self._diagnostic_record(
                    generation=generation,
                    operator=operator,
                    offspring_index=offspring_index,
                    root_cause=root_cause,
                    llm_status=llm_meta.get("status"),
                    llm_elapsed_ms=llm_meta.get("elapsed_ms"),
                    llm_prompt_attempts=llm_meta.get("prompt_attempts"),
                    llm_api_attempts=llm_meta.get("api_attempts"),
                    eval_status=eval_meta.get("status"),
                    eval_elapsed_ms=eval_meta.get("elapsed_ms"),
                    total_elapsed_ms=(time.monotonic() - start_time) * 1000,
                    detail=eval_meta.get("detail") or llm_meta.get("detail") or f"{type(e).__name__}: {e}",
                )
            )

            offspring = _empty_offspring()
            p = None

        # Round the objective values
        return p, offspring
    # def process_task(self,pop, operator):
    #     result =  None, {
    #             'algorithm': None,
    #             'code': None,
    #             'objective': None,
    #             'other_inf': None
    #         }
    #     with concurrent.futures.ThreadPoolExecutor() as executor:
    #         future = executor.submit(self.get_offspring, pop, operator)
    #         try:
    #             result = future.result(timeout=self.timeout)
    #             future.cancel()
    #             #print(result)
    #         except:
    #             future.cancel()
                
    #     return result

    
    def get_algorithm(self, pop, operator, generation=0):
        results = []
        start_time = time.monotonic()
        try:
            results = Parallel(n_jobs=self.n_p,timeout=self.parallel_timeout)(
                delayed(self.get_offspring)(pop, operator, generation, offspring_index)
                for offspring_index in range(self.pop_size)
            )
        except Exception as e:
            error_detail = f"{type(e).__name__}: {e}"
            is_timeout = isinstance(e, (TimeoutError, multiprocessing.TimeoutError))
            failure_label = "Parallel worker timeout" if is_timeout else "Parallel worker failure"
            print(f"{failure_label} (budget={self.parallel_timeout}s): {error_detail}")
            self._write_timeout_record(
                self._diagnostic_record(
                    generation=generation,
                    operator=operator,
                    offspring_index=None,
                    root_cause="worker_budget_timeout" if is_timeout else "unexpected_error",
                    total_elapsed_ms=(time.monotonic() - start_time) * 1000,
                    detail=error_detail,
                    event="worker_budget_timeout" if is_timeout else "worker_failure",
                )
            )
            
        time.sleep(2)


        out_p = []
        out_off = []

        for p, off in results:
            out_p.append(p)
            out_off.append(off)
            if self.debug:
                print(f">>> check offsprings: \n {off}")
        return out_p, out_off
    # def get_algorithm(self,pop,operator, pop_size, n_p):
        
    #     # perform it pop_size times with n_p processes in parallel
    #     p,offspring = self._get_alg(pop,operator)
    #     while self.check_duplicate(pop,offspring['code']):
    #         if self.debug:
    #             print("duplicated code, wait 1 second and retrying ... ")
    #         time.sleep(1)
    #         p,offspring = self._get_alg(pop,operator)
    #     self.code2file(offspring['code'])
    #     try:
    #         fitness= self.interface_eval.evaluate()
    #     except:
    #         fitness = None
    #     offspring['objective'] =  fitness
    #     #offspring['other_inf'] =  first_gap
    #     while (fitness == None):
    #         if self.debug:
    #             print("warning! error code, retrying ... ")
    #         p,offspring = self._get_alg(pop,operator)
    #         while self.check_duplicate(pop,offspring['code']):
    #             if self.debug:
    #                 print("duplicated code, wait 1 second and retrying ... ")
    #             time.sleep(1)
    #             p,offspring = self._get_alg(pop,operator)
    #         self.code2file(offspring['code'])
    #         try:
    #             fitness= self.interface_eval.evaluate()
    #         except:
    #             fitness = None
    #         offspring['objective'] =  fitness
    #         #offspring['other_inf'] =  first_gap
    #     offspring['objective'] = np.round(offspring['objective'],5) 
    #     #offspring['other_inf'] = np.round(offspring['other_inf'],3)
    #     return p,offspring

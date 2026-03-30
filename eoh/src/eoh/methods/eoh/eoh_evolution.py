import re
import time
from ...llm.interface_LLM import InterfaceLLM

class Evolution():

    def __init__(self, api_endpoint, api_key, model_LLM,llm_use_local,llm_local_url, debug_mode,prompts, **kwargs):

        # set prompt interface
        #getprompts = GetPrompts()
        self.prompt_task         = prompts.get_task()
        self.prompt_func_name    = prompts.get_func_name()
        self.prompt_func_inputs  = prompts.get_func_inputs()
        self.prompt_func_outputs = prompts.get_func_outputs()
        self.prompt_inout_inf    = prompts.get_inout_inf()
        self.prompt_other_inf    = prompts.get_other_inf()
        if len(self.prompt_func_inputs) > 1:
            self.joined_inputs = ", ".join("'" + s + "'" for s in self.prompt_func_inputs)
        else:
            self.joined_inputs = "'" + self.prompt_func_inputs[0] + "'"

        if len(self.prompt_func_outputs) > 1:
            self.joined_outputs = ", ".join("'" + s + "'" for s in self.prompt_func_outputs)
        else:
            self.joined_outputs = "'" + self.prompt_func_outputs[0] + "'"

        # set LLMs
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.model_LLM = model_LLM
        self.debug_mode = debug_mode # close prompt checking
        self.llm_total_timeout_s = max(1, int(kwargs.get("llm_total_timeout_s", 90)))
        self.llm_request_timeout_s = max(1, int(kwargs.get("llm_request_timeout_s", 30)))
        self.last_generation_meta = {
            "status": "not_started",
            "elapsed_ms": 0.0,
            "prompt_attempts": 0,
            "api_attempts": 0,
            "error_type": None,
        }


        self.interface_llm = InterfaceLLM(
            self.api_endpoint,
            self.api_key,
            self.model_LLM,
            llm_use_local,
            llm_local_url,
            self.debug_mode,
            request_timeout_s=self.llm_request_timeout_s,
            total_timeout_s=self.llm_total_timeout_s,
        )

    @staticmethod
    def _extract_algorithm_and_code(response):
        if not isinstance(response, str):
            return [], []

        algorithm = re.findall(r"\{(.*)\}", response, re.DOTALL)
        if len(algorithm) == 0:
            if 'python' in response:
                algorithm = re.findall(r'^.*?(?=python)', response,re.DOTALL)
            elif 'import' in response:
                algorithm = re.findall(r'^.*?(?=import)', response,re.DOTALL)
            else:
                algorithm = re.findall(r'^.*?(?=def)', response,re.DOTALL)

        code = re.findall(r"import.*return", response, re.DOTALL)
        if len(code) == 0:
            code = re.findall(r"def.*return", response, re.DOTALL)

        return algorithm, code

    def _set_last_generation_meta(self, **kwargs):
        self.last_generation_meta = {
            "status": kwargs.get("status", "unknown"),
            "elapsed_ms": round(float(kwargs.get("elapsed_ms", 0.0)), 3),
            "prompt_attempts": int(kwargs.get("prompt_attempts", 0)),
            "api_attempts": int(kwargs.get("api_attempts", 0)),
            "error_type": kwargs.get("error_type"),
            "detail": kwargs.get("detail"),
        }

    def get_prompt_i1(self):
        
        prompt_content = self.prompt_task+"\n"\
"First, describe your new algorithm and main steps in one sentence. \
The description must be inside a brace. Next, implement it in Python as a function named \
"+self.prompt_func_name +". This function should accept "+str(len(self.prompt_func_inputs))+" input(s): "\
+self.joined_inputs+". The function should return "+str(len(self.prompt_func_outputs))+" output(s): "\
+self.joined_outputs+". "+self.prompt_inout_inf+" "\
+self.prompt_other_inf+"\n"+"Do not give additional explanations."
        return prompt_content

        
    def get_prompt_e1(self,indivs):
        prompt_indiv = ""
        for i in range(len(indivs)):
            prompt_indiv=prompt_indiv+"No."+str(i+1) +" algorithm and the corresponding code are: \n" + indivs[i]['algorithm']+"\n" +indivs[i]['code']+"\n"

        prompt_content = self.prompt_task+"\n"\
"I have "+str(len(indivs))+" existing algorithms with their codes as follows: \n"\
+prompt_indiv+\
"Please help me create a new algorithm that has a totally different form from the given ones. \n"\
"First, describe your new algorithm and main steps in one sentence. \
The description must be inside a brace. Next, implement it in Python as a function named \
"+self.prompt_func_name +". This function should accept "+str(len(self.prompt_func_inputs))+" input(s): "\
+self.joined_inputs+". The function should return "+str(len(self.prompt_func_outputs))+" output(s): "\
+self.joined_outputs+". "+self.prompt_inout_inf+" "\
+self.prompt_other_inf+"\n"+"Do not give additional explanations."
        return prompt_content
    
    def get_prompt_e2(self,indivs):
        prompt_indiv = ""
        for i in range(len(indivs)):
            prompt_indiv=prompt_indiv+"No."+str(i+1) +" algorithm and the corresponding code are: \n" + indivs[i]['algorithm']+"\n" +indivs[i]['code']+"\n"

        prompt_content = self.prompt_task+"\n"\
"I have "+str(len(indivs))+" existing algorithms with their codes as follows: \n"\
+prompt_indiv+\
"Please help me create a new algorithm that has a totally different form from the given ones but can be motivated from them. \n"\
"Firstly, identify the common backbone idea in the provided algorithms. Secondly, based on the backbone idea describe your new algorithm in one sentence. \
The description must be inside a brace. Thirdly, implement it in Python as a function named \
"+self.prompt_func_name +". This function should accept "+str(len(self.prompt_func_inputs))+" input(s): "\
+self.joined_inputs+". The function should return "+str(len(self.prompt_func_outputs))+" output(s): "\
+self.joined_outputs+". "+self.prompt_inout_inf+" "\
+self.prompt_other_inf+"\n"+"Do not give additional explanations."
        return prompt_content
    
    def get_prompt_m1(self,indiv1):
        feedback = ""
        other_inf = indiv1.get("other_inf")
        if isinstance(other_inf, str) and other_inf.strip():
            feedback = "\nEvaluation feedback (for guidance):\n" + other_inf.strip() + "\n"

        prompt_content = (
            self.prompt_task
            + "\n"
            + "I have one algorithm with its code as follows. "
            + "Algorithm description: "
            + indiv1["algorithm"]
            + "\n"
            + "Code:\n"
            + indiv1["code"]
            + "\n"
            + feedback
            + "Please assist me in creating a new algorithm that has a different form but can be a modified version of the algorithm provided. \n"
            + "First, describe your new algorithm and main steps in one sentence. "
            + "The description must be inside a brace. Next, implement it in Python as a function named "
            + self.prompt_func_name
            + ". This function should accept "
            + str(len(self.prompt_func_inputs))
            + " input(s): "
            + self.joined_inputs
            + ". The function should return "
            + str(len(self.prompt_func_outputs))
            + " output(s): "
            + self.joined_outputs
            + ". "
            + self.prompt_inout_inf
            + " "
            + self.prompt_other_inf
            + "\n"
            + "Do not give additional explanations."
        )
        return prompt_content
    
    def get_prompt_m2(self,indiv1):
        prompt_content = self.prompt_task+"\n"\
"I have one algorithm with its code as follows. \
Algorithm description: "+indiv1['algorithm']+"\n\
Code:\n\
"+indiv1['code']+"\n\
Please identify the main algorithm parameters and assist me in creating a new algorithm that has a different parameter settings of the score function provided. \n"\
"First, describe your new algorithm and main steps in one sentence. \
The description must be inside a brace. Next, implement it in Python as a function named \
"+self.prompt_func_name +". This function should accept "+str(len(self.prompt_func_inputs))+" input(s): "\
+self.joined_inputs+". The function should return "+str(len(self.prompt_func_outputs))+" output(s): "\
+self.joined_outputs+". "+self.prompt_inout_inf+" "\
+self.prompt_other_inf+"\n"+"Do not give additional explanations."
        return prompt_content
    
    def get_prompt_m3(self,indiv1):
        prompt_content = "First, you need to identify the main components in the function below. \
Next, analyze whether any of these components can be overfit to the in-distribution instances. \
Then, based on your analysis, simplify the components to enhance the generalization to potential out-of-distribution instances. \
Finally, provide the revised code, keeping the function name, inputs, and outputs unchanged. \n"+indiv1['code']+"\n"\
+self.prompt_inout_inf+"\n"+"Do not give additional explanations."
        return prompt_content


    def _get_alg(self,prompt_content):
        start_time = time.monotonic()
        prompt_attempts = 0
        last_error_type = None

        while prompt_attempts < 4:
            elapsed_s = time.monotonic() - start_time
            if elapsed_s >= self.llm_total_timeout_s:
                self._set_last_generation_meta(
                    status="llm_timeout",
                    elapsed_ms=elapsed_s * 1000,
                    prompt_attempts=prompt_attempts,
                    api_attempts=self.interface_llm.last_request_meta.get("attempts", 0),
                    error_type="TotalPhaseTimeoutExceeded",
                    detail="LLM phase exceeded total timeout budget before a parseable response was produced.",
                )
                raise TimeoutError("LLM phase exceeded total timeout budget.")

            prompt_attempts += 1
            response = self.interface_llm.get_response(prompt_content)
            llm_meta = dict(getattr(self.interface_llm, "last_request_meta", {}))
            last_error_type = llm_meta.get("error_type")
            algorithm, code = self._extract_algorithm_and_code(response)

            if len(algorithm) > 0 and len(code) > 0:
                self._set_last_generation_meta(
                    status="success",
                    elapsed_ms=(time.monotonic() - start_time) * 1000,
                    prompt_attempts=prompt_attempts,
                    api_attempts=llm_meta.get("attempts", 0),
                    error_type=None,
                    detail=None,
                )
                algorithm = algorithm[0]
                code = code[0]
                code_all = code+" "+", ".join(s for s in self.prompt_func_outputs) 
                return [code_all, algorithm]

            if self.debug_mode:
                print("Error: algorithm or code not identified, wait 1 seconds and retrying ... ")

            status = llm_meta.get("status")
            if status in {"llm_timeout", "llm_error"} and response is None:
                last_error_type = llm_meta.get("error_type")

        final_status = "parse_error"
        detail = "LLM response was received but the algorithm or code block could not be parsed."
        if response is None and last_error_type is not None:
            final_status = "llm_timeout" if llm_meta.get("status") == "llm_timeout" else "llm_error"
            detail = "LLM failed before returning a parseable response."

        self._set_last_generation_meta(
            status=final_status,
            elapsed_ms=(time.monotonic() - start_time) * 1000,
            prompt_attempts=prompt_attempts,
            api_attempts=llm_meta.get("attempts", 0),
            error_type=last_error_type,
            detail=detail,
        )
        raise ValueError(detail)


    def i1(self):

        prompt_content = self.get_prompt_i1()

        if self.debug_mode:
            print("\n >>> check prompt for creating algorithm using [ i1 ] : \n", prompt_content )
            print(">>> Press 'Enter' to continue")
            input()
      
        [code_all, algorithm] = self._get_alg(prompt_content)

        if self.debug_mode:
            print("\n >>> check designed algorithm: \n", algorithm)
            print("\n >>> check designed code: \n", code_all)
            print(">>> Press 'Enter' to continue")
            input()

        return [code_all, algorithm]
    
    def e1(self,parents):
      
        prompt_content = self.get_prompt_e1(parents)

        if self.debug_mode:
            print("\n >>> check prompt for creating algorithm using [ e1 ] : \n", prompt_content )
            print(">>> Press 'Enter' to continue")
            input()
      
        [code_all, algorithm] = self._get_alg(prompt_content)

        if self.debug_mode:
            print("\n >>> check designed algorithm: \n", algorithm)
            print("\n >>> check designed code: \n", code_all)
            print(">>> Press 'Enter' to continue")
            input()

        return [code_all, algorithm]
    
    def e2(self,parents):
      
        prompt_content = self.get_prompt_e2(parents)

        if self.debug_mode:
            print("\n >>> check prompt for creating algorithm using [ e2 ] : \n", prompt_content )
            print(">>> Press 'Enter' to continue")
            input()
      
        [code_all, algorithm] = self._get_alg(prompt_content)

        if self.debug_mode:
            print("\n >>> check designed algorithm: \n", algorithm)
            print("\n >>> check designed code: \n", code_all)
            print(">>> Press 'Enter' to continue")
            input()

        return [code_all, algorithm]
    
    def m1(self,parents):
      
        prompt_content = self.get_prompt_m1(parents)

        if self.debug_mode:
            print("\n >>> check prompt for creating algorithm using [ m1 ] : \n", prompt_content )
            print(">>> Press 'Enter' to continue")
            input()
      
        [code_all, algorithm] = self._get_alg(prompt_content)

        if self.debug_mode:
            print("\n >>> check designed algorithm: \n", algorithm)
            print("\n >>> check designed code: \n", code_all)
            print(">>> Press 'Enter' to continue")
            input()

        return [code_all, algorithm]
    
    def m2(self,parents):
      
        prompt_content = self.get_prompt_m2(parents)

        if self.debug_mode:
            print("\n >>> check prompt for creating algorithm using [ m2 ] : \n", prompt_content )
            print(">>> Press 'Enter' to continue")
            input()
      
        [code_all, algorithm] = self._get_alg(prompt_content)

        if self.debug_mode:
            print("\n >>> check designed algorithm: \n", algorithm)
            print("\n >>> check designed code: \n", code_all)
            print(">>> Press 'Enter' to continue")
            input()

        return [code_all, algorithm]
    
    def m3(self,parents):
      
        prompt_content = self.get_prompt_m3(parents)

        if self.debug_mode:
            print("\n >>> check prompt for creating algorithm using [ m3 ] : \n", prompt_content )
            print(">>> Press 'Enter' to continue")
            input()
      
        [code_all, algorithm] = self._get_alg(prompt_content)

        if self.debug_mode:
            print("\n >>> check designed algorithm: \n", algorithm)
            print("\n >>> check designed code: \n", code_all)
            print(">>> Press 'Enter' to continue")
            input()

        return [code_all, algorithm]

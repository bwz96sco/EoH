from ..llm.api_general import InterfaceAPI
from ..llm.api_local_llm import InterfaceLocalLLM

class InterfaceLLM:
    def __init__(
        self,
        api_endpoint,
        api_key,
        model_LLM,
        llm_use_local=False,
        llm_local_url=None,
        debug_mode=None,
        request_timeout_s=30,
        total_timeout_s=90,
    ):
        if debug_mode is None:
            # Backward-compatible 4-arg shape:
            # InterfaceLLM(api_endpoint, api_key, model, debug_mode)
            debug_mode = bool(llm_use_local)
            llm_use_local = False
            llm_local_url = None

        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.model_LLM = model_LLM
        self.debug_mode = debug_mode
        self.llm_use_local = llm_use_local
        self.llm_local_url = llm_local_url
        self.request_timeout_s = request_timeout_s
        self.total_timeout_s = total_timeout_s
        self.last_request_meta = {
            "status": "not_started",
            "attempts": 0,
            "elapsed_ms": 0.0,
            "error_type": None,
        }

        print("- check LLM API")

        if self.llm_use_local:
            print('local llm delopyment is used ...')
            
            if self.llm_local_url == None or self.llm_local_url == 'xxx' :
                print(">> Stop with empty url for local llm !")
                exit()

            self.interface_llm = InterfaceLocalLLM(
                self.llm_local_url
            )

        else:
            print('remote llm api is used ...')

            if self.api_key == None or self.api_endpoint ==None or self.api_key == 'xxx' or self.api_endpoint == 'xxx':
                print(">> Stop with wrong API setting: Set api_endpoint (e.g., api.chat...) and api_key (e.g., kx-...) !")
                exit()

            self.interface_llm = InterfaceAPI(
                self.api_endpoint,
                self.api_key,
                self.model_LLM,
                self.debug_mode,
                request_timeout_s=self.request_timeout_s,
                total_timeout_s=self.total_timeout_s,
            )

            
        res = self.interface_llm.get_response("1+1=?")
        self.last_request_meta = dict(getattr(self.interface_llm, "last_request_meta", self.last_request_meta))

        if res == None:
            print(">> Error in LLM API, wrong endpoint, key, model or local deployment!")
            exit()

        # choose LLMs
        # if self.type == "API2D-GPT":
        #     self.interface_llm = InterfaceAPI2D(self.key,self.model_LLM,self.debug_mode)
        # else:
        #     print(">>> Wrong LLM type, only API2D-GPT is available! \n")

    def get_response(self, prompt_content):
        response = self.interface_llm.get_response(prompt_content)
        self.last_request_meta = dict(getattr(self.interface_llm, "last_request_meta", self.last_request_meta))

        return response

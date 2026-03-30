# This file includes classe to get response from deployed local LLM
import json
import time
import requests


class InterfaceLocalLLM:
    """Language model that predicts continuation of provided source code.
    """

    def __init__(self, url):
        self._url = url  # 'http://127.0.0.1:11045/completions'
        self.last_request_meta = {
            "status": "not_started",
            "attempts": 0,
            "elapsed_ms": 0.0,
            "error_type": None,
        }

    def get_response(self, content: str) -> str:
        start_time = time.monotonic()
        attempts = 0
        while True:
            try:
                attempts += 1
                response = self._do_request(content)
                self.last_request_meta = {
                    "status": "success",
                    "attempts": attempts,
                    "elapsed_ms": round((time.monotonic() - start_time) * 1000, 3),
                    "error_type": None,
                }
                return response
            except Exception as exc:
                self.last_request_meta = {
                    "status": "llm_error",
                    "attempts": attempts,
                    "elapsed_ms": round((time.monotonic() - start_time) * 1000, 3),
                    "error_type": type(exc).__name__,
                }
                continue

    def _do_request(self, content: str) -> str:
        content = content.strip('\n').strip()
        # repeat the prompt for batch inference (inorder to decease the sample delay)
        data = {
            'prompt': content,
            'repeat_prompt': 1,
            'params': {
                'do_sample': True,
                'temperature': None,
                'top_k': None,
                'top_p': None,
                'add_special_tokens': False,
                'skip_special_tokens': True,
            }
        }
        headers = {'Content-Type': 'application/json'}
        response = requests.post(self._url, data=json.dumps(data), headers=headers)
        print(response)
        if response.status_code == 200:
            response = response.json()['content'][0]
            return response

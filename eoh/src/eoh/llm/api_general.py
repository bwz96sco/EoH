import http.client
import json
import socket
import time
from urllib.parse import urlparse


class InterfaceAPI:
    def __init__(
        self,
        api_endpoint,
        api_key,
        model_LLM,
        debug_mode,
        request_timeout_s=30,
        total_timeout_s=90,
    ):
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.model_LLM = model_LLM
        self.debug_mode = debug_mode
        self.n_trial = 5
        self.request_timeout_s = max(1, int(request_timeout_s))
        self.total_timeout_s = max(self.request_timeout_s, int(total_timeout_s))
        self._parsed_endpoint_cache = self._parsed_endpoint()
        self._request_path_cache = self._build_request_path(self._parsed_endpoint_cache)
        self._connection = None
        self.last_request_meta = {
            "status": "not_started",
            "attempts": 0,
            "elapsed_ms": 0.0,
            "error_type": None,
        }

    def get_response(self, prompt_content):
        payload_explanation = json.dumps(
            {
                "model": self.model_LLM,
                "stream": False,
                "messages": [
                    {"role": "user", "content": prompt_content}
                ],
            }
        )

        headers = {
            "Authorization": "Bearer " + self.api_key,
            "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "x-api2d-no-cache": 1,
        }

        response = None
        start_time = time.monotonic()
        for attempt in range(1, self.n_trial + 1):
            elapsed_before_attempt = time.monotonic() - start_time
            if elapsed_before_attempt >= self.total_timeout_s:
                self.last_request_meta = {
                    "status": "llm_timeout",
                    "attempts": attempt - 1,
                    "elapsed_ms": round(elapsed_before_attempt * 1000, 3),
                    "error_type": "TotalTimeoutExceeded",
                }
                return None

            attempt_start = time.monotonic()
            try:
                conn = self._get_connection()
                conn.request("POST", self._request_path_cache, payload_explanation, headers)
                res = conn.getresponse()
                data = res.read()
                if res.status >= 400:
                    raise RuntimeError(
                        f"HTTP {res.status} from LLM API. Body: {data[:500]}"
                    )
                json_data = json.loads(data)
                if "choices" not in json_data:
                    raise KeyError(
                        f"'choices' not in API response. "
                        f"Keys: {list(json_data.keys())}. "
                        f"Body: {data[:500]}"
                    )
                response = json_data["choices"][0]["message"]["content"]
                self.last_request_meta = {
                    "status": "success",
                    "attempts": attempt,
                    "elapsed_ms": round((time.monotonic() - start_time) * 1000, 3),
                    "error_type": None,
                }
                break
            except Exception as e:
                self._reset_connection()
                error_type = type(e).__name__
                is_timeout = isinstance(e, (TimeoutError, socket.timeout))
                self.last_request_meta = {
                    "status": "llm_timeout" if is_timeout else "llm_error",
                    "attempts": attempt,
                    "elapsed_ms": round((time.monotonic() - start_time) * 1000, 3),
                    "error_type": error_type,
                }
                if self.debug_mode:
                    print(f"Error in API (attempt {attempt}/{self.n_trial}): {e}")
                else:
                    print(f"API error (attempt {attempt}/{self.n_trial}): {error_type}: {e}")
                if attempt < self.n_trial:
                    attempt_elapsed = time.monotonic() - attempt_start
                    if is_timeout and attempt_elapsed >= self.request_timeout_s:
                        time.sleep(0)
                    else:
                        time.sleep(min(2 ** attempt, 16))
                continue

        return response

    def _parsed_endpoint(self):
        endpoint = self.api_endpoint.strip()
        if "://" not in endpoint:
            endpoint = f"https://{endpoint}"
        return urlparse(endpoint)

    def _get_connection(self):
        if self._connection is None:
            self._connection = self._make_connection()
        return self._connection

    def _reset_connection(self):
        if self._connection is None:
            return
        try:
            self._connection.close()
        except Exception:
            pass
        self._connection = None

    def _make_connection(self):
        parsed = self._parsed_endpoint_cache
        host = parsed.netloc or parsed.path
        if parsed.scheme == "http":
            return http.client.HTTPConnection(host, timeout=self.request_timeout_s)
        return http.client.HTTPSConnection(host, timeout=self.request_timeout_s)

    def _request_path(self):
        return self._request_path_cache

    def _build_request_path(self, parsed):
        base_path = parsed.path.rstrip("/")
        if not base_path:
            return "/v1/chat/completions"
        if base_path.endswith("/chat/completions"):
            return base_path
        if base_path.endswith("/v1"):
            return f"{base_path}/chat/completions"
        return f"{base_path}/v1/chat/completions"

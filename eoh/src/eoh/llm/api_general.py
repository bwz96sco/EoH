import http.client
import json
import os
import socket
import subprocess
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
        self._auth_mode = self._resolve_auth_mode()
        self._access_token = None
        self._access_token_deadline = 0.0
        self.last_request_meta = {
            "status": "not_started",
            "attempts": 0,
            "elapsed_ms": 0.0,
            "error_type": None,
        }

    def __getstate__(self):
        """Drop live connection state so joblib workers can unpickle safely."""
        state = self.__dict__.copy()
        state["_connection"] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._connection = None

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
                headers = self._build_headers()
                conn.request("POST", self._request_path_cache, payload_explanation, headers)
                res = conn.getresponse()
                data = res.read()
                if res.status >= 400:
                    if res.status in {401, 403}:
                        self._invalidate_access_token()
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

    def _resolve_auth_mode(self):
        mode = os.environ.get("LLM_API_AUTH_MODE", "").strip().lower()
        if mode:
            return mode

        api_key = (self.api_key or "").strip().lower()
        if api_key in {"gcloud-adc", "vertex-adc", "adc", "gcp-adc"}:
            return "gcloud-adc"

        return "static"

    def _build_headers(self):
        return {
            "Authorization": "Bearer " + self._resolve_bearer_token(),
            "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "x-api2d-no-cache": 1,
        }

    def _resolve_bearer_token(self):
        if self._auth_mode != "gcloud-adc":
            return self.api_key

        now = time.monotonic()
        if self._access_token and now < self._access_token_deadline:
            return self._access_token

        command_timeout_s = max(5, min(self.request_timeout_s, 30))
        try:
            completed = subprocess.run(
                ["gcloud", "auth", "application-default", "print-access-token"],
                capture_output=True,
                check=False,
                text=True,
                timeout=command_timeout_s,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to refresh Google Cloud access token: {exc}"
            ) from exc

        token = completed.stdout.strip()
        if completed.returncode != 0 or not token:
            detail = completed.stderr.strip() or completed.stdout.strip() or "empty output"
            raise RuntimeError(
                f"Failed to refresh Google Cloud access token via gcloud ADC: {detail}"
            )

        ttl_raw = os.environ.get("LLM_GCLOUD_ACCESS_TOKEN_TTL_S", "3000")
        try:
            ttl_s = max(60, int(ttl_raw))
        except ValueError:
            ttl_s = 3000

        self._access_token = token
        self._access_token_deadline = time.monotonic() + ttl_s
        return token

    def _invalidate_access_token(self):
        if self._auth_mode != "gcloud-adc":
            return
        self._access_token = None
        self._access_token_deadline = 0.0

    def _build_request_path(self, parsed):
        base_path = parsed.path.rstrip("/")
        if not base_path:
            return "/v1/chat/completions"
        if base_path.endswith("/chat/completions"):
            return base_path
        if base_path.endswith("/openapi"):
            return f"{base_path}/chat/completions"
        if base_path.endswith("/v1"):
            return f"{base_path}/chat/completions"
        return f"{base_path}/v1/chat/completions"

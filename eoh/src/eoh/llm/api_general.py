import http.client
import json
import time
from urllib.parse import urlparse


class InterfaceAPI:
    def __init__(self, api_endpoint, api_key, model_LLM, debug_mode):
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.model_LLM = model_LLM
        self.debug_mode = debug_mode
        self.n_trial = 5

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
            "x-api2d-no-cache": 1,
        }

        response = None
        for attempt in range(1, self.n_trial + 1):
            try:
                conn = self._make_connection()
                conn.request("POST", self._request_path(), payload_explanation, headers)
                res = conn.getresponse()
                data = res.read()
                json_data = json.loads(data)
                if "choices" not in json_data:
                    raise KeyError(
                        f"'choices' not in API response. "
                        f"Keys: {list(json_data.keys())}. "
                        f"Body: {data[:500]}"
                    )
                response = json_data["choices"][0]["message"]["content"]
                break
            except Exception as e:
                if self.debug_mode:
                    print(f"Error in API (attempt {attempt}/{self.n_trial}): {e}")
                else:
                    print(f"API error (attempt {attempt}/{self.n_trial}): {type(e).__name__}: {e}")
                if attempt < self.n_trial:
                    time.sleep(min(2 ** attempt, 16))
                continue

        return response

    def _parsed_endpoint(self):
        endpoint = self.api_endpoint.strip()
        if "://" not in endpoint:
            endpoint = f"https://{endpoint}"
        return urlparse(endpoint)

    def _make_connection(self):
        parsed = self._parsed_endpoint()
        host = parsed.netloc or parsed.path
        if parsed.scheme == "http":
            return http.client.HTTPConnection(host)
        return http.client.HTTPSConnection(host)

    def _request_path(self):
        parsed = self._parsed_endpoint()
        base_path = parsed.path.rstrip("/")
        if not base_path:
            return "/v1/chat/completions"
        if base_path.endswith("/chat/completions"):
            return base_path
        if base_path.endswith("/v1"):
            return f"{base_path}/chat/completions"
        return f"{base_path}/v1/chat/completions"

import os
import time
import requests
import ssl
from typing import Dict, Any, Optional, cast
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager


class TLSAdapter(HTTPAdapter):
    """
    HTTP adapter that enforces a minimum TLS version.
    """

    def __init__(self, min_tls_version: int = ssl.TLSVersion.TLSv1_2, **kwargs: Any):
        self.min_tls_version = min_tls_version
        super().__init__(**kwargs)

    def init_poolmanager(self, *args: Any, **kwargs: Any) -> Any:
        context = ssl.create_default_context()
        context.minimum_version = self.min_tls_version
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)


class APIClient:
    """Client for interacting with the ContextAnchor API."""

    def __init__(self, endpoint: str, retry_attempts: int = 3, timeout: int = 30):
        self.endpoint = endpoint.rstrip("/")
        self.retry_attempts = retry_attempts
        self.timeout = timeout
        self.api_key = self._load_api_key()
        self.session = requests.Session()
        # Enforce TLS 1.2+ for security (TLS 1.3 preferred)
        self.session.mount("https://", TLSAdapter(min_tls_version=ssl.TLSVersion.TLSv1_2))

    def _load_api_key(self) -> str:
        """Load API key from credentials file."""
        creds_path = os.path.expanduser("~/.contextanchor/credentials")
        try:
            with open(creds_path, "r") as f:
                return f.read().strip()
        except Exception:
            return ""

    def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute HTTP request with retries and exponential backoff."""
        url = f"{self.endpoint}{path}"
        headers = kwargs.pop("headers", {})
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        for attempt in range(self.retry_attempts + 1):
            try:
                response = self.session.request(
                    method, url, headers=headers, timeout=self.timeout, **kwargs
                )
                response.raise_for_status()
                return cast(Dict[str, Any], response.json())
            except requests.exceptions.Timeout:
                if attempt == self.retry_attempts:
                    from .errors import NetworkError
                    raise NetworkError(f"Request timed out after {self.timeout}s")
            except requests.exceptions.ConnectionError:
                if attempt == self.retry_attempts:
                    from .errors import NetworkError
                    raise NetworkError("Network is unavailable or server is unreachable")
            except requests.exceptions.HTTPError as e:
                # Only retry 5xx errors
                if 500 <= e.response.status_code < 600 and attempt < self.retry_attempts:
                    pass
                else:
                    from .errors import NetworkError, ConfigurationError, DataError
                    if e.response.status_code == 401 or e.response.status_code == 403:
                        raise ConfigurationError("Invalid or missing API key")
                    elif 400 <= e.response.status_code < 500:
                        raise DataError(f"Invalid request ({e.response.status_code}): {e.response.text}")
                    else:
                        raise NetworkError(f"API Error {e.response.status_code}: {e.response.text}")

            if attempt < self.retry_attempts:
                # Exponential backoff (1s, 2s, 4s...)
                time.sleep(2**attempt)

        from .errors import NetworkError
        raise NetworkError("Max retries exceeded")

    def create_context(
        self,
        repository_id: str,
        branch: str,
        developer_intent: str,
        signals: Dict[str, Any],
        developer_id: str = "unknown",
    ) -> Dict[str, Any]:
        """POST /v1/contexts"""
        payload = {
            "repository_id": repository_id,
            "branch": branch,
            "developer_id": developer_id,
            "developer_intent": developer_intent,
            "signals": signals,
        }
        return self._request("POST", "/v1/contexts", json=payload)

    def get_latest_context(self, repository_id: str, branch: str) -> Dict[str, Any]:
        """GET /v1/contexts/latest"""
        return self._request(
            "GET", "/v1/contexts/latest", params={"repository_id": repository_id, "branch": branch}
        )

    def get_context_by_id(self, snapshot_id: str) -> Dict[str, Any]:
        """GET /v1/contexts/{id}"""
        return self._request("GET", f"/v1/contexts/{snapshot_id}")

    def list_contexts(
        self,
        repository_id: str,
        branch: Optional[str] = None,
        limit: int = 20,
        next_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """GET /v1/contexts"""
        params: Dict[str, Any] = {"repository_id": repository_id, "limit": limit}
        if branch:
            params["branch"] = branch
        if next_token:
            params["next_token"] = next_token
        return self._request("GET", "/v1/contexts", params=params)

    def delete_context(self, snapshot_id: str) -> Dict[str, Any]:
        """DELETE /v1/contexts/{id}"""
        return self._request("DELETE", f"/v1/contexts/{snapshot_id}")

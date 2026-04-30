"""Sklik API HTTP client over JSON endpoint."""
from __future__ import annotations

import logging
from typing import Any

import requests

from sklik_mcp.core.errors import SessionError, SklikError, error_for_status
from sklik_mcp.core.session import SessionState

logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "https://api.sklik.cz/drak/json/v5"


class SklikClient:
    def __init__(
        self,
        token: str,
        endpoint: str = DEFAULT_ENDPOINT,
        timeout_s: int = 30,
        http: requests.Session | None = None,
    ):
        if not token:
            raise ValueError("Sklik API token is required")
        self.token = token
        self.endpoint = endpoint.rstrip("/")
        self.timeout_s = timeout_s
        self.session = SessionState()
        self._http = http or requests.Session()
        self._http.headers.update({"Content-Type": "application/json", "Accept": "application/json"})

    def login(self) -> None:
        """POST /client.loginByToken; store the returned session string."""
        resp = self._post("client.loginByToken", {"token": self.token})
        sess = resp.get("session")
        if not sess:
            raise SessionError("Login response missing session", status=resp.get("status"))
        self.session.session_token = sess
        # token_owner_user_id may be available via resp["user"]["userId"] — set if present
        user_obj = resp.get("user") or {}
        if "userId" in user_obj:
            self.session.token_owner_user_id = int(user_obj["userId"])
        logger.info("Sklik login OK (token_owner=%s)", self.session.token_owner_user_id)

    def set_active_account(self, user_id: int | None) -> None:
        """Set or clear the impersonation target for subsequent calls."""
        self.session.active_user_id = user_id

    def call(self, method: str, *params: dict[str, Any]) -> dict[str, Any]:
        """Make a Sklik JSON call. Auto-prepends the auth struct.

        On 401 SessionError this will be augmented with retry in Task 7.
        """
        if not self.session.is_authenticated:
            self.login()
        body = [self.session.auth_struct(), *params]
        return self._post(method, *body, raw_body=True)

    def _post(self, method: str, *body: dict[str, Any], raw_body: bool = False) -> dict[str, Any]:
        url = f"{self.endpoint}/{method}"
        # For login, the body is a single struct; for other calls it's an array of structs.
        payload: list[dict[str, Any]] | dict[str, Any]
        if raw_body:
            payload = list(body)
        else:
            # login-style: single struct
            payload = body[0] if len(body) == 1 else list(body)
        logger.debug("POST %s payload=%s", url, payload)
        try:
            r = self._http.post(url, json=payload, timeout=self.timeout_s)
        except requests.RequestException as e:
            raise SklikError(f"HTTP error calling {method}: {e}") from e
        try:
            data = r.json()
        except ValueError as e:
            raise SklikError(f"Non-JSON response from {method}: {r.text[:200]}") from e
        status = int(data.get("status", r.status_code))
        message = data.get("statusMessage", "")
        details = data.get("errors")
        err = error_for_status(status, message or f"Sklik {method} failed", details)
        if err is not None:
            raise err
        return data

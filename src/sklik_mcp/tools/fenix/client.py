"""Thin REST client for Sklik Fénix (shopping) API."""
from __future__ import annotations

from typing import Any

import requests

from sklik_mcp.core.errors import SklikError, error_for_status


class FenixClient:
    """Thin REST client for Sklik Fénix (shopping) API.

    NOTE: As of 2026-04-30 the Fénix API public docs are sparse. Endpoint paths
    and the Bearer auth scheme are best-effort and may need adjustment. Verify
    against: https://api.sklik.cz/fenix/
    """

    def __init__(
        self,
        token: str,
        endpoint: str = "https://api.sklik.cz/fenix/v1",
        timeout_s: int = 30,
    ) -> None:
        self.token = token
        self.endpoint = endpoint.rstrip("/")
        self.timeout_s = timeout_s
        self._http = requests.Session()
        self._http.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def _check(self, r: requests.Response) -> dict:
        try:
            data: dict = r.json()
        except ValueError as e:
            raise SklikError(f"Non-JSON Fénix response: {r.text[:200]}") from e
        # NOTE: Fénix error envelope is undocumented; assume `{message, errors}` like Drak.
        # Smoke testing in Task 22 will verify and we'll refine here if needed.
        err = error_for_status(
            r.status_code, data.get("message", ""), data.get("errors")
        )
        if err:
            raise err
        return data

    def get(self, path: str, **params: Any) -> dict:
        r = self._http.get(
            f"{self.endpoint}/{path}", params=params, timeout=self.timeout_s
        )
        return self._check(r)

    def post(self, path: str, json: dict | None = None) -> dict:
        r = self._http.post(
            f"{self.endpoint}/{path}", json=json or {}, timeout=self.timeout_s
        )
        return self._check(r)

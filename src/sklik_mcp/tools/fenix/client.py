"""REST client for the unified Sklik /v1/ API (Fénix / Nákupy).

Unlike the Drak v5 JSON-RPC API, the v1 API uses standard REST and OAuth2.
Authentication is a two-step flow:

1. The user obtains a *refresh token* (a JWT) from sklik.cz once.
2. The client exchanges the refresh token for a short-lived *access token*
   via `POST /v1/user/token` (form-encoded, `grant_type=client_credentials`).
3. Every subsequent request goes out as `Authorization: Bearer {access_token}`.

The OpenAPI spec is published at https://api.sklik.cz/v1/openapi.json.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from sklik_mcp.core.errors import SklikError, error_for_status

logger = logging.getLogger(__name__)

# Refresh slightly before the server-claimed expiry to avoid races.
_REFRESH_LEEWAY_S = 30


class FenixClient:
    """REST client for `https://api.sklik.cz/v1/` (Nákupy / Fénix).

    Holds the long-lived refresh token, lazily exchanges it for a short
    access token on first use, and re-exchanges when the cached access
    token nears its expiry.
    """

    def __init__(
        self,
        refresh_token: str,
        endpoint: str = "https://api.sklik.cz/v1",
        timeout_s: int = 30,
        http: requests.Session | None = None,
    ) -> None:
        if not refresh_token:
            raise ValueError("Sklik /v1 refresh token is required")
        self.refresh_token = refresh_token
        self.endpoint = endpoint.rstrip("/")
        self.timeout_s = timeout_s
        self._http = http or requests.Session()
        # Default headers for JSON paths; the token header is set per-request.
        self._http.headers.update({"Accept": "application/json"})
        self._access_token: str | None = None
        self._access_expires_at: float = 0.0

    def _ensure_access_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        now = time.time()
        if self._access_token is not None and now < self._access_expires_at - _REFRESH_LEEWAY_S:
            return self._access_token
        # Exchange refresh → access. The refresh token goes in Authorization,
        # `grant_type=client_credentials` in the form body.
        r = self._http.post(
            f"{self.endpoint}/user/token",
            headers={
                "Authorization": f"Bearer {self.refresh_token}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
            timeout=self.timeout_s,
        )
        try:
            payload: dict[str, Any] = r.json()
        except ValueError as e:
            raise SklikError(f"Non-JSON token-exchange response: {r.text[:200]}") from e
        if r.status_code != 200 or "access_token" not in payload:
            detail = payload.get("detail") or payload
            raise SklikError(
                f"Token exchange failed ({r.status_code}): {detail}", status=r.status_code
            )
        self._access_token = str(payload["access_token"])
        # `expires_in` is server-provided in seconds; default to 1h if missing.
        expires_in = int(payload.get("expires_in") or 3600)
        self._access_expires_at = now + expires_in
        logger.info("Sklik /v1 access token refreshed (expires_in=%ss)", expires_in)
        return self._access_token

    def _auth_header(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._ensure_access_token()}"}

    def _check(self, r: requests.Response) -> Any:
        # FastAPI/RFC7807 errors come as `{detail: ...}` with HTTP status.
        if r.status_code == 204 or not r.content:
            return None
        try:
            data = r.json()
        except ValueError as e:
            raise SklikError(f"Non-JSON /v1 response: {r.text[:200]}") from e
        if r.status_code >= 400:
            message = ""
            details: Any = None
            if isinstance(data, dict):
                detail = data.get("detail")
                if isinstance(detail, str):
                    message = detail
                elif isinstance(detail, list) and detail:
                    first = detail[0]
                    if isinstance(first, dict):
                        message = (first.get("msg") or "").strip()
                    else:
                        message = str(first)
                    details = detail
            err = error_for_status(r.status_code, message or f"Sklik /v1 {r.status_code}", details)
            if err is not None:
                raise err
            raise SklikError(message or f"Sklik /v1 {r.status_code}", status=r.status_code)
        return data

    def get(self, path: str, **params: Any) -> dict[str, Any]:
        # Strip None values so optional query params don't get sent as ?x=None.
        clean = {k: v for k, v in params.items() if v is not None}
        r = self._http.get(
            f"{self.endpoint}/{path.lstrip('/')}",
            params=clean,
            headers=self._auth_header(),
            timeout=self.timeout_s,
        )
        result = self._check(r)
        return _as_dict(result)

    def post(
        self,
        path: str,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        r = self._http.post(
            f"{self.endpoint}/{path.lstrip('/')}",
            params=clean_params,
            json=json,
            headers={**self._auth_header(), "Content-Type": "application/json"},
            timeout=self.timeout_s,
        )
        result = self._check(r)
        return _as_dict(result)

    def patch(
        self,
        path: str,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        r = self._http.patch(
            f"{self.endpoint}/{path.lstrip('/')}",
            params=clean_params,
            json=json,
            headers={**self._auth_header(), "Content-Type": "application/json"},
            timeout=self.timeout_s,
        )
        result = self._check(r)
        return _as_dict(result)


def _as_dict(payload: Any) -> dict[str, Any]:
    """Coerce a /v1 response into a dict for MCP tool return types.

    Most endpoints return objects; a few (e.g. enumeration listings) return
    arrays. Wrap arrays in a `{"items": [...]}` envelope so every MCP tool
    can declare a consistent dict[str, Any] return shape.
    """
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, list):
        return {"items": payload}
    return {"value": payload}

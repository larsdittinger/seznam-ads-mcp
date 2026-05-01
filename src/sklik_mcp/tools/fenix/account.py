"""Sklik /v1 (Fénix) authorization sanity-check tool.

Wraps `GET /v1/user/me` so users can verify their refresh token works
and inspect what scopes were granted, without first having to know
their `premise_id` (which the rest of the Nákupy tools require).
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.core.errors import with_sklik_error_handling
from sklik_mcp.tools.fenix.client import FenixClient


def register(mcp: FastMCP, client: SklikClient, fenix: FenixClient | None = None) -> None:
    if fenix is None:
        return

    @mcp.tool()
    @with_sklik_error_handling
    def get_fenix_user_info() -> dict[str, Any]:
        """Return the currently authorized Sklik /v1 user.

        Calls `GET /v1/user/me` and returns `{userId, userName, actor, scope}`.
        Use this as a first step when setting up the Fénix integration to
        confirm `SKLIK_FENIX_TOKEN` is valid and to see what `scope` was
        granted (e.g. whether Nákupy access is included).

        Returns:
            Raw `CurrentUserResponse` from Sklik.
        """
        return fenix.get("/user/me")

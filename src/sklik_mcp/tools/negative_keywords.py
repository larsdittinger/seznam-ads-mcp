"""Negative-keyword tools (vylučující klíčová slova) — campaign or group scope."""
from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient

Scope = Literal["campaign", "group"]
_PREFIX: dict[str, str] = {"campaign": "campaigns", "group": "groups"}


def register(mcp: FastMCP, client: SklikClient) -> None:
    @mcp.tool()
    def list_negative_keywords(scope: Scope, scope_id: int) -> dict:
        """List negative keywords (vylučující klíčová slova) for a campaign or group.

        Args:
            scope: "campaign" or "group" — which entity to query.
            scope_id: ID of the campaign or group.

        Returns:
            {"negative_keywords": [...]}
        """
        method = f"{_PREFIX[scope]}.getNegativeKeywords"
        resp = client.call(method, {"id": scope_id})
        return {"negative_keywords": resp.get("negativeKeywords", [])}

    @mcp.tool()
    def add_negative_keywords(
        scope: Scope, scope_id: int, keywords: list[str]
    ) -> dict:
        """Add negative keywords to a campaign or group.

        Args:
            scope: "campaign" or "group".
            scope_id: ID of the campaign or group.
            keywords: List of keyword strings to add as negatives.

        Returns:
            {"added": int, "ids": [int, ...]}
        """
        method = f"{_PREFIX[scope]}.addNegativeKeywords"
        body = [{"keyword": k} for k in keywords]
        resp = client.call(method, {"id": scope_id}, body)
        return {"added": len(keywords), "ids": resp.get("negativeKeywordIds", [])}

    @mcp.tool()
    def remove_negative_keyword(
        scope: Scope, scope_id: int, negative_keyword_id: int
    ) -> dict:
        """Remove one negative keyword from a campaign or group.

        Args:
            scope: "campaign" or "group".
            scope_id: ID of the parent campaign or group.
            negative_keyword_id: ID of the negative keyword to remove.

        Returns:
            {"removed": true}
        """
        method = f"{_PREFIX[scope]}.removeNegativeKeyword"
        client.call(method, {"id": scope_id, "negativeKeywordId": negative_keyword_id})
        return {"removed": True}

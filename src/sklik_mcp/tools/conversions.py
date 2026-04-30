"""Conversion tools (konverze) — list defined conversions and fetch stats."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.core.formatting import add_kc_field


def register(mcp: FastMCP, client: SklikClient) -> None:
    @mcp.tool()
    def list_conversions() -> dict[str, Any]:
        """List all conversion definitions (konverze) on the active account.

        Returns:
            {"conversions": [{"id": int, "name": str, ...}, ...]}
        """
        resp = client.call("conversions.list", {})
        return {"conversions": resp.get("conversions", [])}

    @mcp.tool()
    def get_conversion_stats(
        conversion_id: int,
        date_from: str,
        date_to: str,
    ) -> dict[str, Any]:
        """Get conversion stats for a single conversion in a date window.

        Args:
            conversion_id: ID of the conversion definition.
            date_from: ISO date YYYY-MM-DD (inclusive).
            date_to: ISO date YYYY-MM-DD (inclusive).

        Returns:
            Conversion stats dict. Money fields are augmented with `_kc` (Kč) versions
            when present (e.g. `spend_kc`).
        """
        filt = {"id": conversion_id, "dateFrom": date_from, "dateTo": date_to}
        resp = client.call("conversions.stats", filt)
        stats = resp.get("stats", {})
        return add_kc_field(stats)

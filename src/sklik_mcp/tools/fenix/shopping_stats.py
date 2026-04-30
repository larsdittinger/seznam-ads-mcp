"""Fénix shopping stats tool."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.tools.fenix.client import FenixClient


def register(mcp: FastMCP, client: SklikClient, fenix: FenixClient | None = None) -> None:
    if fenix is None:
        return

    @mcp.tool()
    def get_shopping_stats(
        date_from: str,
        date_to: str,
        group_by: Literal["day", "campaign", "productGroup"] = "day",
    ) -> dict[str, Any]:
        """Shopping (Fénix) performance stats.

        Args:
            date_from: ISO date (YYYY-MM-DD), inclusive.
            date_to: ISO date (YYYY-MM-DD), inclusive.
            group_by: Aggregation level — "day", "campaign", or "productGroup".

        Returns:
            Raw shopping stats response from Fénix.
        """
        resp = fenix.get(
            "stats/shopping",
            dateFrom=date_from,
            dateTo=date_to,
            groupBy=group_by,
        )
        return resp

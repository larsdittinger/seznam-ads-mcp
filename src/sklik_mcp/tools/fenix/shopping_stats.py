"""Fénix shopping stats tool."""

# UNVERIFIED: The Fénix path in this module (stats/shopping) is a best-effort
# guess based on Fénix's documentation conventions. It has NOT been verified
# against the live API yet. If a call returns 404, consult api.sklik.cz/fenix/
# and adjust the path string. Tracked for v0.1.1.

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.core.errors import with_sklik_error_handling
from sklik_mcp.tools.fenix.client import FenixClient


def register(mcp: FastMCP, client: SklikClient, fenix: FenixClient | None = None) -> None:
    if fenix is None:
        return

    @mcp.tool()
    @with_sklik_error_handling
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

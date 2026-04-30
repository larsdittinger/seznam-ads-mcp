"""Stats tools — account overview only.

IMPORTANT: Per-entity stats (campaigns/groups/ads/keywords) are NOT available
synchronously in Sklik. The API uses an asynchronous report-query model:

    1. <entity>.createReport(filter)  → returns reportId
    2. stats.status(reportId)          → poll until ready
    3. <entity>.readReport(reportId)   → fetch the data

This is a meaningful chunk of work (queue management, polling, retry, pagination)
and is tracked for v0.2. The previous synchronous `get_stats` tool that mapped
each entity to `<entity>.stats` was incorrect — those endpoints don't exist.

Until v0.2 lands, the only working stats tool here is `get_account_overview`,
which uses Sklik's synchronous `client.stats` method.
"""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.core.errors import with_sklik_error_handling
from sklik_mcp.core.formatting import add_kc_field

Granularity = Literal["hourly", "daily", "weekly", "monthly", "total"]


def register(mcp: FastMCP, client: SklikClient) -> None:
    @mcp.tool()
    @with_sklik_error_handling
    def get_account_overview(
        date_from: str,
        date_to: str,
        granularity: Granularity = "total",
    ) -> dict[str, Any]:
        """Account-level performance overview (přehled celého účtu).

        Synchronous — returns immediately. For per-entity breakdowns,
        per-entity report tools will land in v0.2.

        Args:
            date_from: ISO date YYYY-MM-DD (inclusive).
            date_to: ISO date YYYY-MM-DD (inclusive).
            granularity: hourly, daily, weekly, monthly, or total. Required by Sklik.

        Returns:
            {"report": [{"date": str, "impressions": int, "clicks": int,
            "ctr": float, "cpc": int, "price": int, "price_kc": float, ...}]}

            Sklik returns a `report` array of rows. The number of rows depends
            on granularity (1 for total, N days for daily, etc.). The money
            field is `price` in haléře; `price_kc` is added in Kč for convenience.
        """
        resp = client.call(
            "client.stats",
            {"dateFrom": date_from, "dateTo": date_to, "granularity": granularity},
        )
        report = [add_kc_field(row, source="price") for row in resp.get("report", [])]
        return {"report": report}

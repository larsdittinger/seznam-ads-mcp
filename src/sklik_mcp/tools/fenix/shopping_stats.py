"""Sklik Nákupy aggregated statistics tool.

Talks to `POST /v1/nakupy/statistics/aggregated` per the official
OpenAPI spec at https://api.sklik.cz/v1/openapi.json. The endpoint takes
a `ReportParams` body with `from`/`to` ISO datetimes and an optional
granularity.
"""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.core.errors import with_sklik_error_handling
from sklik_mcp.tools.fenix.client import FenixClient

Granularity = Literal["daily", "weekly", "monthly", "quarterly", "yearly", "none"]


def register(mcp: FastMCP, client: SklikClient, fenix: FenixClient | None = None) -> None:
    if fenix is None:
        return

    @mcp.tool()
    @with_sklik_error_handling
    def get_shopping_stats(
        premise_id: int,
        date_from: str,
        date_to: str,
        granularity: Granularity = "daily",
    ) -> dict[str, Any]:
        """Aggregated Sklik Nákupy stats for a premise over a date range.

        Args:
            premise_id: Sklik premise (provozovna) ID.
            date_from: Start of the period (ISO datetime, e.g. 2026-04-01
                or 2026-04-01T00:00:00).
            date_to: End of the period, inclusive.
            granularity: One of daily, weekly, monthly, quarterly, yearly,
                or none (= single rollup row). Default daily.

        Returns:
            Raw `AggregatedStatisticsResponse` from Sklik.
        """
        body = {
            "from": date_from,
            "to": date_to,
            "granularity": granularity,
        }
        return fenix.post(
            "/nakupy/statistics/aggregated",
            json=body,
            params={"premiseId": premise_id},
        )

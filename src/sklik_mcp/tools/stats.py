"""Stats tools (statistiky / přehled výkonu) — per-entity reports + account overview."""
from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient

Entity = Literal["campaign", "group", "ad", "keyword"]
Granularity = Literal["hourly", "daily", "weekly", "monthly", "total"]

_STATS_METHOD: dict[str, str] = {
    "campaign": "campaigns.stats",
    "group": "groups.stats",
    "ad": "ads.stats",
    "keyword": "keywords.stats",
}


def _add_kc(item: dict) -> dict:
    """Augment a stats row with a Kč-formatted spend (haléře / 100)."""
    out = dict(item)
    if "spend" in out and isinstance(out["spend"], (int, float)):
        out["spend_kc"] = out["spend"] / 100
    return out


def register(mcp: FastMCP, client: SklikClient) -> None:
    @mcp.tool()
    def get_stats(
        entity: Entity,
        entity_ids: list[int],
        date_from: str,
        date_to: str,
        granularity: Granularity = "total",
    ) -> dict:
        """Get performance stats (statistiky) for a list of entities.

        Args:
            entity: Which Sklik entity type to query (campaign, group, ad, keyword).
            entity_ids: IDs of the entities to fetch stats for.
            date_from: ISO date YYYY-MM-DD (inclusive).
            date_to: ISO date YYYY-MM-DD (inclusive).
            granularity: Roll-up: hourly, daily, weekly, monthly, or total (single row).

        Returns:
            {"report": [{"id": int, "stats": [{"date": str, "impressions": int,
            "clicks": int, "spend": int, "spend_kc": float, ...}]}]}
        """
        method = _STATS_METHOD[entity]
        filt = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "granularity": granularity,
            "ids": entity_ids,
        }
        resp = client.call(method, filt)
        report = resp.get("report", [])
        for row in report:
            row["stats"] = [_add_kc(s) for s in row.get("stats", [])]
        return {"report": report}

    @mcp.tool()
    def get_account_overview(date_from: str, date_to: str) -> dict:
        """Account-level rollup (přehled celého účtu) for the given window.

        Args:
            date_from: ISO date YYYY-MM-DD (inclusive).
            date_to: ISO date YYYY-MM-DD (inclusive).

        Returns:
            {"impressions": int, "clicks": int, "spend": int, "spend_kc": float, ...}
        """
        resp = client.call("client.stats", {"dateFrom": date_from, "dateTo": date_to})
        stats = resp.get("stats", {})
        return _add_kc(stats)

"""Stats tools — account, campaigns, ad groups, ads, keywords.

Three flavours of stats endpoint, all verified live 2026-05-01:

1. **`client.stats`** (synchronous) — account-level totals, no entity breakdown.
   Used by `get_account_overview`. Supports `splitByConversions: true` for
   per-conversion-action breakdowns.

2. **`<entity>.createReport` → `<entity>.readReport`** (async-but-fast) — used
   for per-entity breakdowns (campaigns / groups / ads / keywords).
   Despite the two-call shape there is *no polling step*: readReport returns
   data immediately after createReport. Two crucial gotchas the docs hide:

   - **`allowEmptyStatistics` defaults to `false`**, which silently filters out
     entities that had no impressions/clicks in the window. Without this flag
     a `readReport` over an account with quiet keywords returns `report: []`
     and looks broken. We expose `include_zeros` (default `false` for compact
     output, `true` to surface every entity).
   - **Default response columns are minimal** (id + clickMoney + clicks + impressions).
     We always pass an explicit `displayColumns` set including ctr/avgCpc/conversions/
     totalMoney etc — without it the response is useless.

3. **Money fields are in haléře** (1 Kč = 100 haléřů). We add `*_money_kc`
   convenience fields converted to Kč alongside the raw integers.

Date in stats rows is a Sklik integer:
  - `total`/`daily`: YYYYMMDD (e.g. 20251101)
  - `monthly`: YYYYMM (e.g. 202511)
  - `quarterly`/`yearly`: YYYY (or YYYYQ for quarterly)
We pass it through as-is — converting client-side breaks ad-hoc rollups.
"""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.core.errors import with_sklik_error_handling

# Sklik docs: client.stats and <entity>.createReport both accept these six.
# `hourly` is rejected with "Bad arguments" — verified live 2026-05-01.
Granularity = Literal["total", "daily", "weekly", "monthly", "quarterly", "yearly"]

# Money fields returned in haléře by Sklik. We mirror them with `_kc` versions.
_MONEY_FIELDS = (
    "totalMoney",
    "clickMoney",
    "impressionMoney",
    "avgCpc",
    "avgCpt",
    "conversionValue",
)

# Per-entity displayColumns. Without these readReport returns only the bare
# minimum (id + 3 stats). Verified live 2026-05-01 against an active account.
_CAMPAIGN_COLS: list[str] = [
    "id", "name", "status",
    "clicks", "impressions", "ctr", "avgCpc", "avgPos",
    "conversions", "conversionValue", "transactions",
    "totalMoney", "clickMoney", "impressionMoney",
]
_GROUP_COLS: list[str] = [*_CAMPAIGN_COLS, "campaign.id", "campaign.name"]
_AD_COLS: list[str] = [
    "id", "headline1", "headline2", "status",
    "clicks", "impressions", "ctr", "avgCpc",
    "conversions", "conversionValue", "transactions",
    "totalMoney", "clickMoney", "impressionMoney",
    "group.id", "group.name", "campaign.id", "campaign.name",
]
_KEYWORD_COLS: list[str] = [
    "id", "name", "matchType", "status", "cpc",
    "clicks", "impressions", "ctr", "avgCpc", "avgPos",
    "conversions", "conversionValue", "transactions",
    "totalMoney", "clickMoney", "impressionMoney",
    "group.id", "group.name", "campaign.id", "campaign.name",
]


def _add_money_kc(row: dict[str, Any]) -> dict[str, Any]:
    """Mirror every haléř money field with a `*_kc` Kč version."""
    out = dict(row)
    for f in _MONEY_FIELDS:
        if f in out and isinstance(out[f], (int, float)):
            out[f"{f}_kc"] = out[f] / 100
    return out


def _augment_stats(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Walk a `<entity>.readReport` response and add `*_kc` to every stats row."""
    augmented: list[dict[str, Any]] = []
    for row in rows:
        new_row = dict(row)
        if "stats" in new_row and isinstance(new_row["stats"], list):
            new_row["stats"] = [_add_money_kc(s) for s in new_row["stats"]]
        augmented.append(new_row)
    return augmented


def _entity_report(
    client: SklikClient,
    entity: str,
    *,
    restriction: dict[str, Any],
    granularity: Granularity,
    include_zeros: bool,
    limit: int,
    offset: int,
    display_columns: list[str],
) -> dict[str, Any]:
    """Run the canonical createReport→readReport pair for one entity."""
    create_resp = client.call(
        f"{entity}.createReport",
        restriction,
        {"statGranularity": granularity},
    )
    report_id = create_resp.get("reportId")
    total_count = create_resp.get("totalCount", 0)
    if not report_id:
        return {"report": [], "total": 0}
    read_resp = client.call(
        f"{entity}.readReport",
        report_id,
        {
            "offset": offset,
            "limit": limit,
            "allowEmptyStatistics": include_zeros,
            "displayColumns": display_columns,
        },
    )
    rows = read_resp.get("report", []) or []
    return {"report": _augment_stats(rows), "total": int(total_count)}


def register(mcp: FastMCP, client: SklikClient) -> None:
    @mcp.tool()
    @with_sklik_error_handling
    def get_account_overview(
        date_from: str,
        date_to: str,
        granularity: Granularity = "total",
        split_by_conversions: bool = False,
    ) -> dict[str, Any]:
        """Account-level performance overview (přehled celého účtu).

        Synchronous — returns immediately. Use the per-entity stats tools
        (`get_campaign_stats` etc.) for breakdowns.

        Args:
            date_from: ISO date YYYY-MM-DD (inclusive).
            date_to: ISO date YYYY-MM-DD (inclusive).
            granularity: total / daily / weekly / monthly / quarterly / yearly.
            split_by_conversions: When True, each row includes a `conversionList`
                array with per-conversion-action breakdown.

        Returns:
            {"report": [{"date": str, "impressions": int, "clicks": int,
            "ctr": float, "cpc": int, "price": int, "price_kc": float, ...}]}

            Money fields (`price`, `cpc`, `conversionValue`, …) are in haléře;
            `*_kc` mirrors are added for human readability.
        """
        params: dict[str, Any] = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "granularity": granularity,
        }
        if split_by_conversions:
            params["splitByConversions"] = True
        resp = client.call("client.stats", params)
        rows = resp.get("report", []) or []
        out_rows: list[dict[str, Any]] = []
        for row in rows:
            new_row = _add_money_kc(row)
            # client.stats uses `price` for spend (not `totalMoney`).
            if isinstance(row.get("price"), (int, float)):
                new_row["price_kc"] = row["price"] / 100
            if isinstance(row.get("cpc"), (int, float)):
                new_row["cpc_kc"] = row["cpc"] / 100
            if isinstance(row.get("conversionAvgPrice"), (int, float)):
                new_row["conversionAvgPrice_kc"] = row["conversionAvgPrice"] / 100
            if isinstance(row.get("conversionAvgValue"), (int, float)):
                new_row["conversionAvgValue_kc"] = row["conversionAvgValue"] / 100
            # Augment per-conversion list rows too
            if isinstance(row.get("conversionList"), list):
                new_row["conversionList"] = [_add_money_kc(c) for c in row["conversionList"]]
            out_rows.append(new_row)
        return {"report": out_rows}

    @mcp.tool()
    @with_sklik_error_handling
    def get_campaign_stats(
        date_from: str,
        date_to: str,
        campaign_ids: list[int] | None = None,
        granularity: Granularity = "total",
        include_zeros: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Per-campaign stats (statistiky kampaní).

        Args:
            date_from: ISO date YYYY-MM-DD (inclusive).
            date_to: ISO date YYYY-MM-DD (inclusive).
            campaign_ids: Limit to these campaign IDs. None = all campaigns.
            granularity: total → 1 row per campaign; daily/monthly/etc → N rows.
            include_zeros: When False (default), campaigns with zero impressions
                in the window are excluded. Set True to surface them anyway.
            limit / offset: Pagination across campaigns (one campaign may
                expand to many rows once granularity > total).

        Returns:
            {"report": [{"id": int, "name": str, "status": str, "stats":
            [{"date": int, "clicks": int, "impressions": int, "ctr": float,
            "avgCpc": int, "avgCpc_kc": float, "totalMoney": int,
            "totalMoney_kc": float, "conversions": int, ...}]}], "total": int}

            Money fields are in haléře with `_kc` mirrors in Kč.
        """
        restriction: dict[str, Any] = {"dateFrom": date_from, "dateTo": date_to}
        if campaign_ids is not None:
            restriction["ids"] = campaign_ids
        return _entity_report(
            client,
            "campaigns",
            restriction=restriction,
            granularity=granularity,
            include_zeros=include_zeros,
            limit=limit,
            offset=offset,
            display_columns=_CAMPAIGN_COLS,
        )

    @mcp.tool()
    @with_sklik_error_handling
    def get_ad_group_stats(
        date_from: str,
        date_to: str,
        group_ids: list[int] | None = None,
        campaign_id: int | None = None,
        granularity: Granularity = "total",
        include_zeros: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Per-ad-group stats (statistiky sestav).

        Args:
            date_from / date_to: ISO date window (inclusive).
            group_ids: Limit to these group IDs.
            campaign_id: Limit to groups in this campaign (mutually compatible
                with group_ids — both filters AND together).
            granularity: total / daily / weekly / monthly / quarterly / yearly.
            include_zeros: Include groups with no impressions.
            limit / offset: Pagination.

        Returns:
            Same shape as `get_campaign_stats` but rows include
            `campaign: {id, name}` for navigation.
        """
        restriction: dict[str, Any] = {"dateFrom": date_from, "dateTo": date_to}
        if group_ids is not None:
            restriction["ids"] = group_ids
        if campaign_id is not None:
            restriction["campaign"] = {"ids": [campaign_id]}
        return _entity_report(
            client,
            "groups",
            restriction=restriction,
            granularity=granularity,
            include_zeros=include_zeros,
            limit=limit,
            offset=offset,
            display_columns=_GROUP_COLS,
        )

    @mcp.tool()
    @with_sklik_error_handling
    def get_ad_stats(
        date_from: str,
        date_to: str,
        ad_ids: list[int] | None = None,
        group_id: int | None = None,
        campaign_id: int | None = None,
        granularity: Granularity = "total",
        include_zeros: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Per-ad stats (statistiky inzerátů).

        Args:
            date_from / date_to: ISO date window (inclusive).
            ad_ids: Limit to these ad IDs.
            group_id: Limit to ads in this group.
            campaign_id: Limit to ads in this campaign.
            granularity: total / daily / weekly / monthly / quarterly / yearly.
            include_zeros: Include ads with no impressions.
            limit / offset: Pagination.

        Returns:
            Same row shape as `get_campaign_stats`. Banner ads return
            `headline1: null` — that's expected (no text headline to show).
        """
        restriction: dict[str, Any] = {"dateFrom": date_from, "dateTo": date_to}
        if ad_ids is not None:
            restriction["ids"] = ad_ids
        if group_id is not None:
            restriction["group"] = {"ids": [group_id]}
        if campaign_id is not None:
            restriction["campaign"] = {"ids": [campaign_id]}
        return _entity_report(
            client,
            "ads",
            restriction=restriction,
            granularity=granularity,
            include_zeros=include_zeros,
            limit=limit,
            offset=offset,
            display_columns=_AD_COLS,
        )

    @mcp.tool()
    @with_sklik_error_handling
    def get_keyword_stats(
        date_from: str,
        date_to: str,
        keyword_ids: list[int] | None = None,
        group_id: int | None = None,
        campaign_id: int | None = None,
        granularity: Granularity = "total",
        include_zeros: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Per-keyword stats (statistiky klíčových slov).

        Args:
            date_from / date_to: ISO date window (inclusive).
            keyword_ids: Limit to these keyword IDs.
            group_id: Limit to keywords in this group.
            campaign_id: Limit to keywords in this campaign.
            granularity: total / daily / weekly / monthly / quarterly / yearly.
            include_zeros: When False (default), keywords with zero
                impressions are excluded — Sklik filters them server-side via
                `allowEmptyStatistics: false`. Set True to surface every keyword
                in the filter (useful for "did this keyword ever fire?" queries).
            limit / offset: Pagination.

        Returns:
            Same row shape as `get_campaign_stats`.
        """
        restriction: dict[str, Any] = {"dateFrom": date_from, "dateTo": date_to}
        if keyword_ids is not None:
            restriction["ids"] = keyword_ids
        if group_id is not None:
            restriction["group"] = {"ids": [group_id]}
        if campaign_id is not None:
            restriction["campaign"] = {"ids": [campaign_id]}
        return _entity_report(
            client,
            "keywords",
            restriction=restriction,
            granularity=granularity,
            include_zeros=include_zeros,
            limit=limit,
            offset=offset,
            display_columns=_KEYWORD_COLS,
        )

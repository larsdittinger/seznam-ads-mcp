"""Campaign-level tools (kampaně) — list, get, create, update, pause/resume, remove.

Wire shape (verified live 2026-04-30 against api.sklik.cz/drak/json/v5):
- campaigns.list filter accepts only `ids`. No status/name filters — apply
  client-side instead.
- campaigns.update REQUIRES `type` in every payload (Sklik validates the type
  hasn't been changed). update/pause/resume auto-fetch type internally.
- Status values are `active` | `suspend` only. There is no "removed"
  status — use `*.remove` for that.
- Valid campaign types: fulltext, context, product, video, simple, zbozi.
"""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.core.errors import SklikError, with_sklik_error_handling

# Public-facing status (what the MCP tool accepts).
PublicStatus = Literal["active", "paused"]
CampaignType = Literal["fulltext", "context", "product", "video", "simple", "zbozi"]

# Public → wire status mapping. Sklik uses "suspend" instead of "paused".
_WIRE_STATUS: dict[str, str] = {"active": "active", "paused": "suspend"}


def _fetch_campaign_type(client: SklikClient, campaign_id: int) -> str:
    """Read the campaign's type via campaigns.list.

    campaigns.update insists on receiving the campaign's type in every
    payload, but the user only supplies an ID. We fetch it once internally.
    """
    resp = client.call(
        "campaigns.list", {"ids": [campaign_id]}, {"limit": 1, "offset": 0}
    )
    items = resp.get("campaigns", [])
    if not items:
        raise SklikError(f"Campaign {campaign_id} not found")
    return str(items[0]["type"])


def register(mcp: FastMCP, client: SklikClient) -> None:
    @mcp.tool()
    @with_sklik_error_handling
    def list_campaigns(
        status_filter: PublicStatus | None = None,
        name_contains: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List campaigns (seznam kampaní) with optional client-side filters.

        Sklik v5 only filters by `ids` server-side. Status/name filtering
        happens locally after fetching the page.

        Args:
            status_filter: Only return campaigns with this status (active/paused).
            name_contains: Substring match on campaign name (case-insensitive).
            limit: Max number of campaigns to fetch from Sklik per page.
            offset: Pagination offset.

        Returns:
            {"campaigns": [...], "total": int}
        """
        opts = {"limit": limit, "offset": offset}
        resp = client.call("campaigns.list", {}, opts)
        campaigns = resp.get("campaigns", [])
        if status_filter is not None:
            target = _WIRE_STATUS[status_filter]
            campaigns = [c for c in campaigns if c.get("status") == target]
        if name_contains is not None:
            needle = name_contains.lower()
            campaigns = [c for c in campaigns if needle in (c.get("name", "").lower())]
        return {"campaigns": campaigns, "total": len(campaigns)}

    @mcp.tool()
    @with_sklik_error_handling
    def get_campaign(campaign_id: int) -> dict[str, Any]:
        """Get a single campaign by ID.

        Returns:
            {"campaign": {...}} or {"campaign": null} if not found.
        """
        resp = client.call(
            "campaigns.list", {"ids": [campaign_id]}, {"limit": 1, "offset": 0}
        )
        items = resp.get("campaigns", [])
        return {"campaign": items[0] if items else None}

    @mcp.tool()
    @with_sklik_error_handling
    def create_campaign(
        name: str,
        daily_budget_kc: int,
        campaign_type: CampaignType,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Create a new campaign (vytvořit kampaň).

        Args:
            name: Campaign name.
            daily_budget_kc: Daily budget in Kč (converted to haléře internally).
            campaign_type: One of fulltext, context, product, video, simple, zbozi.
                Sklik requires this; choose based on the campaign goal:
                - "fulltext" — search ads
                - "context" — content network ads
                - "product" — Sklik's product ads (legacy)
                - "video" — video ads
                - "simple" — Easy mode (zjednodušená kampaň)
                - "zbozi" — Seznam Nákupy (Shopping)
            start_date: ISO date YYYY-MM-DD or omit.
            end_date: ISO date YYYY-MM-DD or omit.

        Returns:
            {"campaign_id": int}
        """
        body: dict[str, Any] = {
            "name": name,
            "dayBudget": daily_budget_kc * 100,  # haléře
            "type": campaign_type,
        }
        if start_date:
            body["startDate"] = start_date
        if end_date:
            body["endDate"] = end_date
        resp = client.call("campaigns.create", [body])
        ids = resp.get("campaignIds") or []
        return {"campaign_id": ids[0] if ids else None}

    @mcp.tool()
    @with_sklik_error_handling
    def update_campaign(
        campaign_id: int,
        name: str | None = None,
        daily_budget_kc: int | None = None,
        status: PublicStatus | None = None,
    ) -> dict[str, Any]:
        """Update fields on an existing campaign (only the supplied ones).

        Sklik requires `type` in every campaigns.update payload; we fetch it
        internally so the user only needs to supply the ID.

        Returns:
            {"updated": true}
        """
        body: dict[str, Any] = {
            "id": campaign_id,
            "type": _fetch_campaign_type(client, campaign_id),
        }
        if name is not None:
            body["name"] = name
        if daily_budget_kc is not None:
            body["dayBudget"] = daily_budget_kc * 100
        if status is not None:
            body["status"] = _WIRE_STATUS[status]
        client.call("campaigns.update", [body])
        return {"updated": True}

    @mcp.tool()
    @with_sklik_error_handling
    def pause_campaign(campaign_id: int) -> dict[str, Any]:
        """Pause a campaign (pozastavit kampaň)."""
        client.call(
            "campaigns.update",
            [
                {
                    "id": campaign_id,
                    "type": _fetch_campaign_type(client, campaign_id),
                    "status": "suspend",
                }
            ],
        )
        return {"paused": True, "campaign_id": campaign_id}

    @mcp.tool()
    @with_sklik_error_handling
    def resume_campaign(campaign_id: int) -> dict[str, Any]:
        """Resume a paused campaign (znovu spustit kampaň)."""
        client.call(
            "campaigns.update",
            [
                {
                    "id": campaign_id,
                    "type": _fetch_campaign_type(client, campaign_id),
                    "status": "active",
                }
            ],
        )
        return {"resumed": True, "campaign_id": campaign_id}

    @mcp.tool()
    @with_sklik_error_handling
    def remove_campaign(campaign_id: int) -> dict[str, Any]:
        """Remove (soft-delete) a campaign (smazat kampaň)."""
        client.call("campaigns.remove", [campaign_id])
        return {"removed": True, "campaign_id": campaign_id}

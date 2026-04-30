"""Campaign-level tools (kampaně) — list, get, create, update, pause/resume, remove."""
from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient

CampaignStatus = Literal["active", "paused", "removed"]


def register(mcp: FastMCP, client: SklikClient) -> None:
    @mcp.tool()
    def list_campaigns(
        status_filter: CampaignStatus | None = None,
        name_contains: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """List campaigns (seznam kampaní) with optional filters.

        Args:
            status_filter: Only return campaigns with this status (active/paused/removed).
            name_contains: Substring match on campaign name (Sklik filter `name`).
            limit: Max number of campaigns to return.
            offset: Pagination offset.

        Returns:
            {"campaigns": [...], "total": int}
        """
        filt: dict = {}
        if status_filter is not None:
            filt["status"] = status_filter
        if name_contains is not None:
            filt["name"] = name_contains
        opts = {"limit": limit, "offset": offset}
        resp = client.call("campaigns.list", filt, opts)
        return {
            "campaigns": resp.get("campaigns", []),
            "total": resp.get("totalCount", 0),
        }

    @mcp.tool()
    def get_campaign(campaign_id: int) -> dict:
        """Get a single campaign by ID.

        Returns:
            {"campaign": {...}} or {"campaign": null} if not found.
        """
        resp = client.call("campaigns.list", {"id": [campaign_id]}, {})
        items = resp.get("campaigns", [])
        return {"campaign": items[0] if items else None}

    @mcp.tool()
    def create_campaign(
        name: str,
        daily_budget_kc: int,
        currency: str = "CZK",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict:
        """Create a new campaign (vytvořit kampaň).

        Args:
            name: Campaign name.
            daily_budget_kc: Daily budget in Kč (will be converted to haléře internally).
            currency: ISO currency code (default CZK).
            start_date: ISO date YYYY-MM-DD or omit.
            end_date: ISO date YYYY-MM-DD or omit.

        Returns:
            {"campaign_id": int}
        """
        body: dict = {
            "name": name,
            "dayBudget": daily_budget_kc * 100,  # haléře
            "currency": currency,
        }
        if start_date:
            body["startDate"] = start_date
        if end_date:
            body["endDate"] = end_date
        resp = client.call("campaigns.create", [body])
        ids = resp.get("campaignIds") or []
        return {"campaign_id": ids[0] if ids else None}

    @mcp.tool()
    def update_campaign(
        campaign_id: int,
        name: str | None = None,
        daily_budget_kc: int | None = None,
        status: CampaignStatus | None = None,
    ) -> dict:
        """Update fields on an existing campaign (only the supplied ones).

        Returns:
            {"updated": true}
        """
        body: dict = {"id": campaign_id}
        if name is not None:
            body["name"] = name
        if daily_budget_kc is not None:
            body["dayBudget"] = daily_budget_kc * 100
        if status is not None:
            body["status"] = status
        client.call("campaigns.update", [body])
        return {"updated": True}

    @mcp.tool()
    def pause_campaign(campaign_id: int) -> dict:
        """Pause a campaign (pozastavit kampaň)."""
        client.call("campaigns.update", [{"id": campaign_id, "status": "paused"}])
        return {"paused": True, "campaign_id": campaign_id}

    @mcp.tool()
    def resume_campaign(campaign_id: int) -> dict:
        """Resume a paused campaign (znovu spustit kampaň)."""
        client.call("campaigns.update", [{"id": campaign_id, "status": "active"}])
        return {"resumed": True, "campaign_id": campaign_id}

    @mcp.tool()
    def remove_campaign(campaign_id: int) -> dict:
        """Remove (soft-delete) a campaign (smazat kampaň)."""
        client.call("campaigns.remove", [campaign_id])
        return {"removed": True, "campaign_id": campaign_id}

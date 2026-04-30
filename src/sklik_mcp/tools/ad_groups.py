"""Ad group tools (sestavy) — list, get, create, update, pause/resume, remove."""
from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient

GroupStatus = Literal["active", "paused", "removed"]


def register(mcp: FastMCP, client: SklikClient) -> None:
    @mcp.tool()
    def list_ad_groups(
        campaign_id: int | None = None,
        status_filter: GroupStatus | None = None,
        name_contains: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """List ad groups (seznam sestav) with optional filters.

        Args:
            campaign_id: Limit to ad groups in this campaign (Sklik filter `campaignIds`).
            status_filter: Only return groups with this status (active/paused/removed).
            name_contains: Substring match on group name.
            limit: Max number of groups to return.
            offset: Pagination offset.

        Returns:
            {"groups": [...], "total": int}
        """
        filt: dict = {}
        if campaign_id is not None:
            filt["campaignIds"] = [campaign_id]
        if status_filter is not None:
            filt["status"] = status_filter
        if name_contains is not None:
            filt["name"] = name_contains
        opts = {"limit": limit, "offset": offset}
        resp = client.call("groups.list", filt, opts)
        return {
            "groups": resp.get("groups", []),
            "total": resp.get("totalCount", 0),
        }

    @mcp.tool()
    def get_ad_group(group_id: int) -> dict:
        """Get a single ad group by ID.

        Returns:
            {"group": {...}} or {"group": null} if not found.
        """
        resp = client.call("groups.list", {"id": [group_id]}, {})
        items = resp.get("groups", [])
        return {"group": items[0] if items else None}

    @mcp.tool()
    def create_ad_group(
        campaign_id: int,
        name: str,
        max_cpc_kc: int,
    ) -> dict:
        """Create a new ad group (vytvořit sestavu).

        Args:
            campaign_id: Parent campaign ID.
            name: Ad group name.
            max_cpc_kc: Max CPC bid in Kč (converted to haléře internally).

        Returns:
            {"group_id": int}
        """
        body: dict = {
            "campaignId": campaign_id,
            "name": name,
            "maxCpc": max_cpc_kc * 100,  # haléře
        }
        resp = client.call("groups.create", [body])
        ids = resp.get("groupIds") or []
        return {"group_id": ids[0] if ids else None}

    @mcp.tool()
    def update_ad_group(
        group_id: int,
        name: str | None = None,
        max_cpc_kc: int | None = None,
        status: GroupStatus | None = None,
    ) -> dict:
        """Update fields on an existing ad group (only the supplied ones).

        Returns:
            {"updated": true}
        """
        body: dict = {"id": group_id}
        if name is not None:
            body["name"] = name
        if max_cpc_kc is not None:
            body["maxCpc"] = max_cpc_kc * 100
        if status is not None:
            body["status"] = status
        client.call("groups.update", [body])
        return {"updated": True}

    @mcp.tool()
    def pause_ad_group(group_id: int) -> dict:
        """Pause an ad group (pozastavit sestavu)."""
        client.call("groups.update", [{"id": group_id, "status": "paused"}])
        return {"paused": True, "group_id": group_id}

    @mcp.tool()
    def resume_ad_group(group_id: int) -> dict:
        """Resume a paused ad group (znovu spustit sestavu)."""
        client.call("groups.update", [{"id": group_id, "status": "active"}])
        return {"resumed": True, "group_id": group_id}

    @mcp.tool()
    def remove_ad_group(group_id: int) -> dict:
        """Remove (soft-delete) an ad group (smazat sestavu)."""
        client.call("groups.remove", [group_id])
        return {"removed": True, "group_id": group_id}

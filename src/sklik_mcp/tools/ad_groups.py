"""Ad group tools (sestavy) — list, get, create, update, pause/resume, remove.

Wire shape (verified live 2026-04-30):
- groups.list filter accepts only `ids` and nested `campaign: {ids: [...]}`.
  No status/name filters — apply client-side.
- Bid field name is `cpc` (NOT `maxCpc`) on both create and update.
- Status values are `active` | `suspend` only. Use `groups.remove` to
  hard-remove.
"""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.core.errors import with_sklik_error_handling

PublicStatus = Literal["active", "paused"]
_WIRE_STATUS: dict[str, str] = {"active": "active", "paused": "suspend"}

# Default response columns. Without these Sklik would only return
# id/name/campaign/status — hiding the deleted flag and the bid.
_DEFAULT_COLUMNS: list[str] = [
    "id",
    "name",
    "status",
    "deleted",
    "deleteDate",
    "createDate",
    "maxCpc",
    "campaign.id",
    "campaign.name",
]


def register(mcp: FastMCP, client: SklikClient) -> None:
    @mcp.tool()
    @with_sklik_error_handling
    def list_ad_groups(
        campaign_id: int | None = None,
        status_filter: PublicStatus | None = None,
        name_contains: str | None = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List ad groups (seznam sestav) with optional client-side filters.

        Args:
            campaign_id: Limit to ad groups in this campaign.
            status_filter: Only return groups with this status (active/paused).
            name_contains: Substring match on group name (case-insensitive).
            include_deleted: If False (default), soft-deleted groups are hidden.
            limit: Max number of groups to fetch from Sklik per page.
            offset: Pagination offset.

        Returns:
            {"groups": [...], "total": int}
        """
        filt: dict[str, Any] = {}
        if campaign_id is not None:
            filt["campaign"] = {"ids": [campaign_id]}
        opts = {"limit": limit, "offset": offset, "displayColumns": _DEFAULT_COLUMNS}
        resp = client.call("groups.list", filt, opts)
        groups = resp.get("groups", [])
        if not include_deleted:
            groups = [g for g in groups if not g.get("deleted", False)]
        if status_filter is not None:
            target = _WIRE_STATUS[status_filter]
            groups = [g for g in groups if g.get("status") == target]
        if name_contains is not None:
            needle = name_contains.lower()
            groups = [g for g in groups if needle in (g.get("name", "").lower())]
        return {"groups": groups, "total": len(groups)}

    @mcp.tool()
    @with_sklik_error_handling
    def get_ad_group(group_id: int) -> dict[str, Any]:
        """Get a single ad group by ID.

        Returns:
            {"group": {...}} or {"group": null} if not found.
        """
        resp = client.call(
            "groups.list",
            {"ids": [group_id]},
            {"limit": 1, "offset": 0, "displayColumns": _DEFAULT_COLUMNS},
        )
        items = resp.get("groups", [])
        return {"group": items[0] if items else None}

    @mcp.tool()
    @with_sklik_error_handling
    def create_ad_group(
        campaign_id: int,
        name: str,
        max_cpc_kc: int,
    ) -> dict[str, Any]:
        """Create a new ad group (vytvořit sestavu).

        Args:
            campaign_id: Parent campaign ID.
            name: Ad group name.
            max_cpc_kc: Max CPC bid in Kč (converted to haléře internally).

        Returns:
            {"group_id": int}
        """
        body: dict[str, Any] = {
            "campaignId": campaign_id,
            "name": name,
            "cpc": max_cpc_kc * 100,  # haléře — Sklik's group bid field is `cpc`
        }
        resp = client.call("groups.create", [body])
        ids = resp.get("groupIds") or []
        return {"group_id": ids[0] if ids else None}

    @mcp.tool()
    @with_sklik_error_handling
    def update_ad_group(
        group_id: int,
        name: str | None = None,
        max_cpc_kc: int | None = None,
        status: PublicStatus | None = None,
    ) -> dict[str, Any]:
        """Update fields on an existing ad group (only the supplied ones).

        Returns:
            {"updated": true}
        """
        body: dict[str, Any] = {"id": group_id}
        if name is not None:
            body["name"] = name
        if max_cpc_kc is not None:
            body["cpc"] = max_cpc_kc * 100
        if status is not None:
            body["status"] = _WIRE_STATUS[status]
        client.call("groups.update", [body])
        return {"updated": True}

    @mcp.tool()
    @with_sklik_error_handling
    def pause_ad_group(group_id: int) -> dict[str, Any]:
        """Pause an ad group (pozastavit sestavu)."""
        client.call("groups.update", [{"id": group_id, "status": "suspend"}])
        return {"paused": True, "group_id": group_id}

    @mcp.tool()
    @with_sklik_error_handling
    def resume_ad_group(group_id: int) -> dict[str, Any]:
        """Resume a paused ad group (znovu spustit sestavu)."""
        client.call("groups.update", [{"id": group_id, "status": "active"}])
        return {"resumed": True, "group_id": group_id}

    @mcp.tool()
    @with_sklik_error_handling
    def remove_ad_group(group_id: int) -> dict[str, Any]:
        """Remove (soft-delete) an ad group (smazat sestavu)."""
        client.call("groups.remove", [group_id])
        return {"removed": True, "group_id": group_id}

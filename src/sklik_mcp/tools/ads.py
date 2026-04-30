"""Ad tools (inzeráty) — list, get, create text/dynamic, update, pause/resume, remove."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.core.errors import with_sklik_error_handling

AdStatus = Literal["active", "paused", "removed"]


def register(mcp: FastMCP, client: SklikClient) -> None:
    @mcp.tool()
    @with_sklik_error_handling
    def list_ads(
        group_id: int | None = None,
        status: AdStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List ads (seznam inzerátů) with optional filters.

        Args:
            group_id: Limit to ads in this ad group.
            status: Only return ads with this status (active/paused/removed).
            limit: Max number of ads to return.
            offset: Pagination offset.

        Returns:
            {"ads": [...], "total": int}
        """
        filt: dict[str, Any] = {}
        if group_id is not None:
            # Sklik nests parent-entity filters: {"group": {"ids": [...]}}.
            filt["group"] = {"ids": [group_id]}
        if status is not None:
            filt["status"] = status
        opts = {"limit": limit, "offset": offset}
        resp = client.call("ads.list", filt, opts)
        return {
            "ads": resp.get("ads", []),
            "total": resp.get("totalCount", 0),
        }

    @mcp.tool()
    @with_sklik_error_handling
    def get_ad(ad_id: int) -> dict[str, Any]:
        """Get a single ad by ID.

        Returns:
            {"ad": {...}} or {"ad": null} if not found.
        """
        resp = client.call("ads.list", {"ids": [ad_id]}, {"limit": 1, "offset": 0})
        items = resp.get("ads", [])
        return {"ad": items[0] if items else None}

    @mcp.tool()
    @with_sklik_error_handling
    def create_text_ad(
        group_id: int,
        headline1: str,
        headline2: str,
        description1: str,
        final_url: str,
        headline3: str | None = None,
        description2: str | None = None,
    ) -> dict[str, Any]:
        """Create a text ad (textový inzerát) in the given ad group.

        Args:
            group_id: Parent ad group ID.
            headline1: First headline (required).
            headline2: Second headline (required).
            description1: First description line (required).
            final_url: Landing page URL (required).
            headline3: Optional third headline.
            description2: Optional second description line.

        Returns:
            {"ad_id": int}
        """
        body: dict[str, Any] = {
            "type": "text",
            "groupId": group_id,
            "headline1": headline1,
            "headline2": headline2,
            "description1": description1,
            "finalUrl": final_url,
        }
        if headline3 is not None:
            body["headline3"] = headline3
        if description2 is not None:
            body["description2"] = description2
        resp = client.call("ads.create", [body])
        ids = resp.get("adIds") or []
        return {"ad_id": ids[0] if ids else None}

    @mcp.tool()
    @with_sklik_error_handling
    def create_dynamic_ad(
        group_id: int,
        final_url: str,
        description1: str | None = None,
    ) -> dict[str, Any]:
        """Create a dynamic ad (dynamický inzerát) in the given ad group.

        Dynamic ads have most fields auto-generated from the landing page.
        Currently exposes the minimal Sklik fields; extend as needed.

        Args:
            group_id: Parent ad group ID.
            final_url: Landing page URL.
            description1: Optional description line override.

        Returns:
            {"ad_id": int}
        """
        body: dict[str, Any] = {
            "type": "dynamic",
            "groupId": group_id,
            "finalUrl": final_url,
        }
        if description1 is not None:
            body["description1"] = description1
        resp = client.call("ads.create", [body])
        ids = resp.get("adIds") or []
        return {"ad_id": ids[0] if ids else None}

    @mcp.tool()
    @with_sklik_error_handling
    def update_ad(
        ad_id: int,
        headline1: str | None = None,
        headline2: str | None = None,
        headline3: str | None = None,
        description1: str | None = None,
        description2: str | None = None,
        final_url: str | None = None,
        status: AdStatus | None = None,
    ) -> dict[str, Any]:
        """Update fields on an existing ad (only the supplied ones).

        Returns:
            {"updated": true}
        """
        body: dict[str, Any] = {"id": ad_id}
        if headline1 is not None:
            body["headline1"] = headline1
        if headline2 is not None:
            body["headline2"] = headline2
        if headline3 is not None:
            body["headline3"] = headline3
        if description1 is not None:
            body["description1"] = description1
        if description2 is not None:
            body["description2"] = description2
        if final_url is not None:
            body["finalUrl"] = final_url
        if status is not None:
            body["status"] = status
        client.call("ads.update", [body])
        return {"updated": True}

    @mcp.tool()
    @with_sklik_error_handling
    def pause_ad(ad_id: int) -> dict[str, Any]:
        """Pause an ad (pozastavit inzerát)."""
        client.call("ads.update", [{"id": ad_id, "status": "paused"}])
        return {"paused": True, "ad_id": ad_id}

    @mcp.tool()
    @with_sklik_error_handling
    def resume_ad(ad_id: int) -> dict[str, Any]:
        """Resume a paused ad (znovu spustit inzerát)."""
        client.call("ads.update", [{"id": ad_id, "status": "active"}])
        return {"resumed": True, "ad_id": ad_id}

    @mcp.tool()
    @with_sklik_error_handling
    def remove_ad(ad_id: int) -> dict[str, Any]:
        """Remove (soft-delete) an ad (smazat inzerát)."""
        client.call("ads.remove", [ad_id])
        return {"removed": True, "ad_id": ad_id}

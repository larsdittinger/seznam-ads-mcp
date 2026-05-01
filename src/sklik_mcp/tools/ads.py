"""Ad tools (inzeráty) — list, get, create text, update, pause/resume, remove.

Wire shape (verified live 2026-04-30 — ads.create probed exhaustively
on 2026-05-01):

- ads.list filter accepts only `ids` and nested `group: {ids: [...]}`.
  No status filter — apply client-side.
- ads.create / ads.update do NOT accept a `type` or `creativeType` field
  — the server explicitly rejects them with `not_allowed_struct_field`.
  ads.create has a SINGLE wire shape: `groupId`, `headline1`, `headline2`,
  `description`, `finalUrl` (all required), plus optional `headline3` and
  `description2`. There is no separate dynamic-search-ad creation
  endpoint in Drak v5 — `ads.createDynamic`, `dsa.create`,
  `dynamicAds.create`, `groups.createDynamic` etc. all return 404, and
  `groups.update` rejects `dynamicTarget` / `dsaTarget` / `creativeType`.
  Sklik's web UI must be using a non-public route for DSA; until that's
  exposed in v5 (or a future API version) we don't ship a dynamic-ad
  tool — `create_text_ad` is the only verified path.
- Description field on ads is `description` (singular, the first line) and
  optionally `description2` for the second line. There is no `description1`.
- Status values are `active` | `suspend` only. Use `ads.remove` for delete.
"""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.core.errors import with_sklik_error_handling

PublicStatus = Literal["active", "paused"]
_WIRE_STATUS: dict[str, str] = {"active": "active", "paused": "suspend"}

# Default response columns. Without an explicit displayColumns Sklik
# returns finalUrl as `null` (it stores the URL but the default response
# omits it), and the deleted flag is hidden.
_DEFAULT_COLUMNS: list[str] = [
    "id",
    "name",
    "adType",
    "status",
    "deleted",
    "deleteDate",
    "createDate",
    "headline1",
    "headline2",
    "headline3",
    "description",
    "description2",
    "finalUrl",
    "mobileFinalUrl",
    "group.id",
    "group.name",
    "campaign.id",
    "campaign.name",
]


def register(mcp: FastMCP, client: SklikClient) -> None:
    @mcp.tool()
    @with_sklik_error_handling
    def list_ads(
        group_id: int | None = None,
        status: PublicStatus | None = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List ads (seznam inzerátů) with optional client-side filters.

        Args:
            group_id: Limit to ads in this ad group.
            status: Only return ads with this status (active/paused).
            include_deleted: If False (default), soft-deleted ads are hidden.
            limit: Max number of ads to fetch per page.
            offset: Pagination offset.

        Returns:
            {"ads": [...], "total": int}
        """
        filt: dict[str, Any] = {}
        if group_id is not None:
            filt["group"] = {"ids": [group_id]}
        opts = {"limit": limit, "offset": offset, "displayColumns": _DEFAULT_COLUMNS}
        resp = client.call("ads.list", filt, opts)
        ads = resp.get("ads", [])
        if not include_deleted:
            ads = [a for a in ads if not a.get("deleted", False)]
        if status is not None:
            target = _WIRE_STATUS[status]
            ads = [a for a in ads if a.get("status") == target]
        return {"ads": ads, "total": len(ads)}

    @mcp.tool()
    @with_sklik_error_handling
    def get_ad(ad_id: int) -> dict[str, Any]:
        """Get a single ad by ID.

        Returns the ad with all common fields populated (headlines,
        description, finalUrl, status, deleted, …). The default Sklik
        response omits finalUrl, so we request it explicitly.

        Returns:
            {"ad": {...}} or {"ad": null} if not found.
        """
        resp = client.call(
            "ads.list",
            {"ids": [ad_id]},
            {"limit": 1, "offset": 0, "displayColumns": _DEFAULT_COLUMNS},
        )
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
            description1: First description line (required). Sent as
                Sklik's `description` field.
            final_url: Landing page URL (required).
            headline3: Optional third headline.
            description2: Optional second description line.

        Returns:
            {"ad_id": int}
        """
        body: dict[str, Any] = {
            "groupId": group_id,
            "headline1": headline1,
            "headline2": headline2,
            "description": description1,  # Sklik's first description field is just "description"
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
    def update_ad(
        ad_id: int,
        headline1: str | None = None,
        headline2: str | None = None,
        headline3: str | None = None,
        description1: str | None = None,
        description2: str | None = None,
        final_url: str | None = None,
        status: PublicStatus | None = None,
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
            body["description"] = description1
        if description2 is not None:
            body["description2"] = description2
        if final_url is not None:
            body["finalUrl"] = final_url
        if status is not None:
            body["status"] = _WIRE_STATUS[status]
        client.call("ads.update", [body])
        return {"updated": True}

    @mcp.tool()
    @with_sklik_error_handling
    def pause_ad(ad_id: int) -> dict[str, Any]:
        """Pause an ad (pozastavit inzerát)."""
        client.call("ads.update", [{"id": ad_id, "status": "suspend"}])
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

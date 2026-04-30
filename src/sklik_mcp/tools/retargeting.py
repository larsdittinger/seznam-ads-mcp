"""Retargeting tools (retargetingové seznamy) — list, create, update, remove.

Verified against live API 2026-04-30: methods live under the `retargeting.lists.*`
namespace, response field is `lists` (not `retargetingLists`).
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.core.errors import with_sklik_error_handling


def register(mcp: FastMCP, client: SklikClient) -> None:
    @mcp.tool()
    @with_sklik_error_handling
    def list_retargeting_lists() -> dict[str, Any]:
        """List all retargeting lists (retargetingové seznamy) on the active account.

        Returns:
            {"retargeting_lists": [{"id": int, "name": str, ...}, ...]}
        """
        resp = client.call("retargeting.lists.list")
        return {"retargeting_lists": resp.get("lists", [])}

    @mcp.tool()
    @with_sklik_error_handling
    def create_retargeting_list(
        name: str,
        membership_lifespan_days: int = 30,
    ) -> dict[str, Any]:
        """Create a new retargeting list.

        Args:
            name: Display name for the list.
            membership_lifespan_days: How many days a visitor stays on the list (default 30).

        Returns:
            {"retargeting_id": int}
        """
        body = {"name": name, "membershipLifespan": membership_lifespan_days}
        resp = client.call("retargeting.lists.create", body)
        return {"retargeting_id": resp.get("retargetingId")}

    @mcp.tool()
    @with_sklik_error_handling
    def update_retargeting_list(
        retargeting_id: int,
        name: str | None = None,
        membership_lifespan_days: int | None = None,
    ) -> dict[str, Any]:
        """Update fields on an existing retargeting list (only the supplied ones).

        Args:
            retargeting_id: Target list ID.
            name: New display name (optional).
            membership_lifespan_days: New lifespan in days (optional).

        Returns:
            {"updated": true}
        """
        body: dict[str, Any] = {"id": retargeting_id}
        if name is not None:
            body["name"] = name
        if membership_lifespan_days is not None:
            body["membershipLifespan"] = membership_lifespan_days
        # Sklik update_* methods are uniformly bulk: pass [body] like the others.
        client.call("retargeting.lists.update", [body])
        return {"updated": True}

    @mcp.tool()
    @with_sklik_error_handling
    def remove_retargeting_list(retargeting_id: int) -> dict[str, Any]:
        """Remove a retargeting list (smazat seznam)."""
        client.call("retargeting.lists.remove", {"id": retargeting_id})
        return {"removed": True, "retargeting_id": retargeting_id}

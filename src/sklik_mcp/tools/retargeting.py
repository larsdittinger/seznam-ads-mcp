"""Retargeting tools (retargetingové seznamy) — list, create, update, remove.

Wire shape (verified live 2026-04-30 — test list created and deleted):
- Method namespace: retargeting.lists.* (`list`, `create`, `update`, `remove`).
- list-response uses `lists` array; each item has `listId` (NOT `id`).
- create takes [{"attributes": {name, membership, useHistoricData, takeAllUsers}}]
  — note the wrapping `attributes` struct and the `lists` array carrier.
  Response: `listIds: [int, ...]`.
- update takes [{"listId": ..., "attributes": {...}}]; element key is `listId`.
- remove takes a bare list of ids: `[id, id, ...]` (NOT `{"id": ...}`).
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
            {"retargeting_lists": [{"listId": int, "name": str,
                "status": str, "deleted": bool}, ...]}
        """
        resp = client.call("retargeting.lists.list")
        return {"retargeting_lists": resp.get("lists", [])}

    @mcp.tool()
    @with_sklik_error_handling
    def create_retargeting_list(
        name: str,
        membership_days: int = 30,
        use_historic_data: bool = False,
        take_all_users: bool = True,
    ) -> dict[str, Any]:
        """Create a new retargeting list.

        Args:
            name: Display name for the list.
            membership_days: How many days a visitor stays on the list (default 30).
            use_historic_data: If true, include users who matched the rules in the
                past (before list creation). Default false.
            take_all_users: If true, the list collects every visitor. Default true;
                set to false only when paired with custom filters (advanced).

        Returns:
            {"retargeting_id": int}
        """
        attributes = {
            "name": name,
            "membership": membership_days,
            "useHistoricData": use_historic_data,
            "takeAllUsers": take_all_users,
        }
        resp = client.call("retargeting.lists.create", [{"attributes": attributes}])
        ids = resp.get("listIds") or []
        return {"retargeting_id": ids[0] if ids else None}

    @mcp.tool()
    @with_sklik_error_handling
    def update_retargeting_list(
        retargeting_id: int,
        name: str | None = None,
        membership_days: int | None = None,
    ) -> dict[str, Any]:
        """Update fields on an existing retargeting list (only the supplied ones).

        Args:
            retargeting_id: Target list ID.
            name: New display name (optional).
            membership_days: New lifespan in days (optional).

        Returns:
            {"updated": true}
        """
        attributes: dict[str, Any] = {}
        if name is not None:
            attributes["name"] = name
        if membership_days is not None:
            attributes["membership"] = membership_days
        body: dict[str, Any] = {"listId": retargeting_id}
        if attributes:
            body["attributes"] = attributes
        client.call("retargeting.lists.update", [body])
        return {"updated": True}

    @mcp.tool()
    @with_sklik_error_handling
    def remove_retargeting_list(retargeting_id: int) -> dict[str, Any]:
        """Remove a retargeting list (smazat seznam)."""
        # Sklik takes a bare list of IDs.
        client.call("retargeting.lists.remove", [retargeting_id])
        return {"removed": True, "retargeting_id": retargeting_id}

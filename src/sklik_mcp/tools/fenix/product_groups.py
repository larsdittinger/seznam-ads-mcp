"""Fénix product group (skupiny produktů) tools."""

# UNVERIFIED: The Fénix paths in this module (productGroups,
# productGroups/{id}/bid) are best-effort guesses based on Fénix's documentation
# conventions. They have NOT been verified against the live API yet. If a call
# returns 404, consult api.sklik.cz/fenix/ and adjust the path string.
# Tracked for v0.1.1.

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.core.errors import with_sklik_error_handling
from sklik_mcp.tools.fenix.client import FenixClient


def register(mcp: FastMCP, client: SklikClient, fenix: FenixClient | None = None) -> None:
    if fenix is None:
        return

    @mcp.tool()
    @with_sklik_error_handling
    def list_product_groups(campaign_id: int) -> dict[str, Any]:
        """List Fénix product groups (skupiny produktů) for a shopping campaign.

        Args:
            campaign_id: Sklik campaign ID for a shopping campaign.

        Returns:
            {"product_groups": [...]}
        """
        resp = fenix.get("productGroups", campaignId=campaign_id)
        return {"product_groups": resp.get("items", [])}

    @mcp.tool()
    @with_sklik_error_handling
    def update_product_group_bid(product_group_id: int, max_cpc_kc: int) -> dict[str, Any]:
        """Update max CPC bid (Kč) for a Fénix product group.

        Args:
            product_group_id: Product group ID.
            max_cpc_kc: New max CPC in whole Kč. Converted to haléře (x100).

        Returns:
            Raw API response from Fénix.
        """
        resp = fenix.post(
            f"productGroups/{product_group_id}/bid",
            json={"maxCpc": max_cpc_kc * 100},
        )
        return resp

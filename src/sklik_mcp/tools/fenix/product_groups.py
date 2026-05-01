"""Sklik Nákupy (Fénix) shop-item tools.

Talks to the unified `/v1/nakupy/shop-items/` endpoints discovered from the
official OpenAPI spec at https://api.sklik.cz/v1/openapi.json. In Sklik
terminology, the v1 API uses "shop items" rather than "product groups";
each shop item is one row from the user's product feed (XML feed item)
with its own bid attributes.

Wire shape (per OpenAPI 1.5.2, 2026-05-01):

- GET `/nakupy/shop-items/?premiseId={id}&...` — list items for a premise
  (provozovna). Many optional filters; we expose the most useful.
- PATCH `/nakupy/shop-items/?premiseId={id}` body
  `{"items": [{"id": "...", "searchMaxCpc": 3.50, "productMaxCpc": 5.00,
  "availability": 0, "price": 999.0, "priceBeforeDiscount": 1099.0}]}`.
  Bids are in whole Kč with two decimal places (NOT haléře).
"""

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
    def list_shop_items(
        premise_id: int,
        item_id: str | None = None,
        paired: bool | None = None,
        product_category_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List Sklik Nákupy shop items (položky z feedu) for a premise.

        Args:
            premise_id: Sklik premise (provozovna) ID. Each Sklik account can
                have multiple premises; you can discover yours via the Sklik
                web UI under Nákupy.
            item_id: Filter to a single shop-item ID (matches ITEM_ID from
                the XML feed).
            paired: If True, only items currently paired with a Zboží.cz
                product. If False, only unpaired. Omit for both.
            product_category_id: Limit to a specific product category.
            limit: Max items per page (default 100).
            offset: Pagination offset.

        Returns:
            Raw `ListShopItemsResponse` from Sklik (typically `{"items": [...]}`).
        """
        return fenix.get(
            "/nakupy/shop-items/",
            premiseId=premise_id,
            itemId=item_id,
            paired=paired,
            productCategoryId=product_category_id,
            limit=limit,
            offset=offset,
        )

    @mcp.tool()
    @with_sklik_error_handling
    def update_shop_item_bid(
        premise_id: int,
        item_id: str,
        search_max_cpc_kc: float | None = None,
        product_max_cpc_kc: float | None = None,
    ) -> dict[str, Any]:
        """Update CPC bids on a Sklik Nákupy shop item.

        Sklik exposes two separate bids per item:

        - `searchMaxCpc` — bid for Seznam Nákupy search results (fulltext).
        - `productMaxCpc` — bid for clicks from the product detail page.

        Args:
            premise_id: Sklik premise ID containing the item.
            item_id: Shop-item ID (string, from your XML feed's ITEM_ID).
            search_max_cpc_kc: Max CPC in Kč for search-result bidding.
                Two decimal places allowed. Omit to leave unchanged.
            product_max_cpc_kc: Max CPC in Kč for product-detail bidding.
                Two decimal places allowed. Omit to leave unchanged.

        Returns:
            Raw response from Sklik.
        """
        change: dict[str, Any] = {"id": item_id}
        if search_max_cpc_kc is not None:
            change["searchMaxCpc"] = search_max_cpc_kc
        if product_max_cpc_kc is not None:
            change["productMaxCpc"] = product_max_cpc_kc
        return fenix.patch(
            "/nakupy/shop-items/",
            json={"items": [change]},
            params={"premiseId": premise_id},
        )

    @mcp.tool()
    @with_sklik_error_handling
    def list_shopping_campaigns(premise_id: int) -> dict[str, Any]:
        """List Sklik Nákupy campaigns for a premise.

        Args:
            premise_id: Sklik premise (provozovna) ID.

        Returns:
            Raw response from Sklik.
        """
        return fenix.get("/nakupy/campaigns/", premiseId=premise_id)

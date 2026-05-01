from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.tools.fenix import product_groups
from sklik_mcp.tools.fenix.client import FenixClient


def _setup(get_returns=None, patch_returns=None):
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    fenix = MagicMock(spec=FenixClient)
    if get_returns is not None:
        fenix.get.return_value = get_returns
    if patch_returns is not None:
        fenix.patch.return_value = patch_returns
    product_groups.register(mcp, client, fenix)
    return mcp, fenix


async def _invoke(mcp: FastMCP, name: str, arguments: dict):
    tool = mcp._tool_manager._tools[name]
    return await tool.run(arguments)


async def test_list_shop_items_passes_premise_id_and_pagination():
    mcp, fenix = _setup(get_returns={"items": [{"id": "abc"}]})
    out = await _invoke(mcp, "list_shop_items", {"premise_id": 42})
    assert out == {"items": [{"id": "abc"}]}
    fenix.get.assert_called_once_with(
        "/nakupy/shop-items/",
        premiseId=42,
        itemId=None,
        paired=None,
        productCategoryId=None,
        limit=100,
        offset=0,
    )


async def test_list_shop_items_passes_optional_filters():
    mcp, fenix = _setup(get_returns={"items": []})
    await _invoke(
        mcp,
        "list_shop_items",
        {
            "premise_id": 42,
            "item_id": "X-001",
            "paired": True,
            "product_category_id": 7,
            "limit": 50,
            "offset": 100,
        },
    )
    fenix.get.assert_called_once_with(
        "/nakupy/shop-items/",
        premiseId=42,
        itemId="X-001",
        paired=True,
        productCategoryId=7,
        limit=50,
        offset=100,
    )


async def test_update_shop_item_bid_sends_search_only_when_provided():
    mcp, fenix = _setup(patch_returns={"items": [{"id": "abc"}]})
    await _invoke(
        mcp,
        "update_shop_item_bid",
        {"premise_id": 42, "item_id": "abc", "search_max_cpc_kc": 3.5},
    )
    fenix.patch.assert_called_once_with(
        "/nakupy/shop-items/",
        json={"items": [{"id": "abc", "searchMaxCpc": 3.5}]},
        params={"premiseId": 42},
    )


async def test_update_shop_item_bid_sends_both_bids():
    mcp, fenix = _setup(patch_returns={})
    await _invoke(
        mcp,
        "update_shop_item_bid",
        {
            "premise_id": 42,
            "item_id": "abc",
            "search_max_cpc_kc": 3.5,
            "product_max_cpc_kc": 5.25,
        },
    )
    body = fenix.patch.call_args[1]["json"]
    assert body == {"items": [{"id": "abc", "searchMaxCpc": 3.5, "productMaxCpc": 5.25}]}


async def test_list_shopping_campaigns():
    mcp, fenix = _setup(get_returns={"campaigns": [{"id": 1}]})
    out = await _invoke(mcp, "list_shopping_campaigns", {"premise_id": 42})
    assert out == {"campaigns": [{"id": 1}]}
    fenix.get.assert_called_once_with("/nakupy/campaigns/", premiseId=42)


def test_register_noop_when_fenix_missing():
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    product_groups.register(mcp, client, None)
    assert "list_shop_items" not in mcp._tool_manager._tools
    assert "update_shop_item_bid" not in mcp._tool_manager._tools
    assert "list_shopping_campaigns" not in mcp._tool_manager._tools

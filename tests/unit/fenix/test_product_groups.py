from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.tools.fenix import product_groups
from sklik_mcp.tools.fenix.client import FenixClient


def _setup(get_returns=None, post_returns=None):
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    fenix = MagicMock(spec=FenixClient)
    if get_returns is not None:
        fenix.get.return_value = get_returns
    if post_returns is not None:
        fenix.post.return_value = post_returns
    product_groups.register(mcp, client, fenix)
    return mcp, fenix


async def _invoke(mcp: FastMCP, name: str, arguments: dict):
    tool = mcp._tool_manager._tools[name]
    return await tool.run(arguments)


async def test_list_product_groups():
    mcp, fenix = _setup(get_returns={"items": [{"id": 1}]})
    out = await _invoke(mcp, "list_product_groups", {"campaign_id": 5})
    assert out["product_groups"] == [{"id": 1}]
    fenix.get.assert_called_once_with("productGroups", campaignId=5)


async def test_update_product_group_bid():
    mcp, fenix = _setup(post_returns={"updated": True})
    out = await _invoke(
        mcp,
        "update_product_group_bid",
        {"product_group_id": 99, "max_cpc_kc": 5},
    )
    assert out["updated"] is True
    fenix.post.assert_called_once_with("productGroups/99/bid", json={"maxCpc": 500})


def test_register_noop_when_fenix_missing():
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    product_groups.register(mcp, client, None)
    assert "list_product_groups" not in mcp._tool_manager._tools
    assert "update_product_group_bid" not in mcp._tool_manager._tools

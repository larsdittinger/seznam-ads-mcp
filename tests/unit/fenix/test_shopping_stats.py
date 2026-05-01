from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.tools.fenix import shopping_stats
from sklik_mcp.tools.fenix.client import FenixClient


def _setup(post_returns=None):
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    fenix = MagicMock(spec=FenixClient)
    if post_returns is not None:
        fenix.post.return_value = post_returns
    shopping_stats.register(mcp, client, fenix)
    return mcp, fenix


async def _invoke(mcp: FastMCP, name: str, arguments: dict):
    tool = mcp._tool_manager._tools[name]
    return await tool.run(arguments)


async def test_get_shopping_stats_default_granularity_daily():
    mcp, fenix = _setup(post_returns={"rows": [{"date": "2026-04-01", "clicks": 10}]})
    out = await _invoke(
        mcp,
        "get_shopping_stats",
        {"premise_id": 42, "date_from": "2026-04-01", "date_to": "2026-04-30"},
    )
    assert out == {"rows": [{"date": "2026-04-01", "clicks": 10}]}
    fenix.post.assert_called_once_with(
        "/nakupy/statistics/aggregated",
        json={"from": "2026-04-01", "to": "2026-04-30", "granularity": "daily"},
        params={"premiseId": 42},
    )


async def test_get_shopping_stats_explicit_granularity():
    mcp, fenix = _setup(post_returns={"rows": []})
    await _invoke(
        mcp,
        "get_shopping_stats",
        {
            "premise_id": 42,
            "date_from": "2026-04-01",
            "date_to": "2026-04-30",
            "granularity": "monthly",
        },
    )
    body = fenix.post.call_args[1]["json"]
    assert body["granularity"] == "monthly"


def test_register_noop_when_fenix_missing():
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    shopping_stats.register(mcp, client, None)
    assert "get_shopping_stats" not in mcp._tool_manager._tools

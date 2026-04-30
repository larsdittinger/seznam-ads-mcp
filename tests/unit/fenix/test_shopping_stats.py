from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.tools.fenix import shopping_stats
from sklik_mcp.tools.fenix.client import FenixClient


def _setup(get_returns=None):
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    fenix = MagicMock(spec=FenixClient)
    if get_returns is not None:
        fenix.get.return_value = get_returns
    shopping_stats.register(mcp, client, fenix)
    return mcp, fenix


async def _invoke(mcp: FastMCP, name: str, arguments: dict):
    tool = mcp._tool_manager._tools[name]
    return await tool.run(arguments)


async def test_get_shopping_stats_default_group_by_day():
    mcp, fenix = _setup(get_returns={"rows": [{"date": "2026-04-01", "clicks": 10}]})
    out = await _invoke(
        mcp,
        "get_shopping_stats",
        {"date_from": "2026-04-01", "date_to": "2026-04-30"},
    )
    assert out == {"rows": [{"date": "2026-04-01", "clicks": 10}]}
    fenix.get.assert_called_once_with(
        "stats/shopping",
        dateFrom="2026-04-01",
        dateTo="2026-04-30",
        groupBy="day",
    )


async def test_get_shopping_stats_group_by_campaign():
    mcp, fenix = _setup(get_returns={"rows": []})
    await _invoke(
        mcp,
        "get_shopping_stats",
        {
            "date_from": "2026-04-01",
            "date_to": "2026-04-30",
            "group_by": "campaign",
        },
    )
    fenix.get.assert_called_once_with(
        "stats/shopping",
        dateFrom="2026-04-01",
        dateTo="2026-04-30",
        groupBy="campaign",
    )


def test_register_noop_when_fenix_missing():
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    shopping_stats.register(mcp, client, None)
    assert "get_shopping_stats" not in mcp._tool_manager._tools

from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.tools import conversions


def _setup(call_returns):
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    client.call.return_value = call_returns
    conversions.register(mcp, client)
    return mcp, client


async def _invoke(mcp, name, args):
    return await mcp._tool_manager._tools[name].run(args)


async def test_list_conversions_calls_correct_method():
    mcp, client = _setup(
        {
            "status": 200,
            "conversions": [{"id": 1, "name": "objednávka"}],
        }
    )
    out = await _invoke(mcp, "list_conversions", {})
    assert client.call.call_args[0][0] == "conversions.list"
    assert out["conversions"][0]["name"] == "objednávka"


async def test_get_conversion_stats_passes_filter():
    mcp, client = _setup(
        {
            "status": 200,
            "stats": {"conversions": 12, "spend": 50_000, "value": 12_345},
        }
    )
    out = await _invoke(
        mcp,
        "get_conversion_stats",
        {"conversion_id": 9, "date_from": "2026-04-01", "date_to": "2026-04-30"},
    )
    args = client.call.call_args
    assert args[0][0] == "conversions.stats"
    assert args[0][1] == {"id": 9, "dateFrom": "2026-04-01", "dateTo": "2026-04-30"}
    # spend converted to Kč
    assert out["spend_kc"] == 500.0


async def test_get_conversion_stats_handles_missing_spend():
    mcp, client = _setup({"status": 200, "stats": {"conversions": 5}})
    out = await _invoke(
        mcp,
        "get_conversion_stats",
        {"conversion_id": 1, "date_from": "2026-04-01", "date_to": "2026-04-30"},
    )
    assert out["conversions"] == 5
    assert "spend_kc" not in out

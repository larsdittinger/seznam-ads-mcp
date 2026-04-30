from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.tools import stats


def _setup(call_returns):
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    client.call.return_value = call_returns
    stats.register(mcp, client)
    return mcp, client


async def _invoke(mcp, name, args):
    return await mcp._tool_manager._tools[name].run(args)


async def test_get_account_overview_passes_required_granularity():
    mcp, client = _setup(
        {
            "status": 200,
            "report": [{"date": "20260423T00:00:00+0000", "impressions": 0, "price": 0}],
        }
    )
    await _invoke(
        mcp,
        "get_account_overview",
        {"date_from": "2026-04-01", "date_to": "2026-04-30"},
    )
    args = client.call.call_args
    assert args[0][0] == "client.stats"
    # Sklik requires granularity; default is "total"
    assert args[0][1] == {
        "dateFrom": "2026-04-01",
        "dateTo": "2026-04-30",
        "granularity": "total",
    }


async def test_get_account_overview_converts_price_to_kc():
    mcp, _client = _setup(
        {
            "status": 200,
            "report": [
                {"date": "x", "impressions": 1000, "clicks": 50, "price": 50_000},
            ],
        }
    )
    out = await _invoke(
        mcp,
        "get_account_overview",
        {"date_from": "2026-04-01", "date_to": "2026-04-30"},
    )
    assert out["report"][0]["price_kc"] == 500.0
    assert out["report"][0]["impressions"] == 1000


async def test_get_account_overview_passes_explicit_granularity():
    mcp, client = _setup({"status": 200, "report": []})
    await _invoke(
        mcp,
        "get_account_overview",
        {"date_from": "2026-04-01", "date_to": "2026-04-30", "granularity": "daily"},
    )
    assert client.call.call_args[0][1]["granularity"] == "daily"


async def test_get_account_overview_handles_empty_report():
    mcp, _client = _setup({"status": 200, "report": []})
    out = await _invoke(
        mcp,
        "get_account_overview",
        {"date_from": "2026-04-01", "date_to": "2026-04-30"},
    )
    assert out == {"report": []}

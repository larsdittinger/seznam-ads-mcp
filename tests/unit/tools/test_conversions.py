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
    # No extra args, just auth (auto-prepended by SklikClient.call)
    assert client.call.call_args == (("conversions.list",), {})
    assert out["conversions"][0]["name"] == "objednávka"


async def test_get_conversion_stats_uses_client_stats_with_split_flag():
    """conversions.stats does not exist — we ride client.stats(splitByConversions)."""
    mcp, client = _setup(
        {
            "status": 200,
            "report": [
                {
                    "date": "20260101T00:00:00+0000",
                    "conversionList": [
                        {
                            "id": 9,
                            "conversions": 12,
                            "conversionValue": 50_000,
                            "price": 12_345,
                        },
                        {"id": 99, "conversions": 1, "conversionValue": 1000},
                    ],
                },
            ],
        }
    )
    out = await _invoke(
        mcp,
        "get_conversion_stats",
        {
            "conversion_id": 9,
            "date_from": "2026-04-01",
            "date_to": "2026-04-30",
        },
    )
    args = client.call.call_args
    # Must use client.stats, NOT a non-existent conversions.stats
    assert args[0][0] == "client.stats"
    assert args[0][1]["splitByConversions"] is True
    assert args[0][1]["dateFrom"] == "2026-04-01"
    assert args[0][1]["granularity"] == "total"
    # Only the matching conversion entry surfaces in the output
    assert len(out["report"]) == 1
    rec = out["report"][0]
    assert rec["id"] == 9
    assert rec["conversions"] == 12
    # Money fields converted to Kč
    assert rec["conversionValue_kc"] == 500.0
    assert rec["price_kc"] == 123.45


async def test_get_conversion_stats_returns_empty_when_id_missing():
    mcp, _client = _setup(
        {
            "status": 200,
            "report": [
                {
                    "date": "x",
                    "conversionList": [{"id": 999, "conversions": 1}],
                }
            ],
        }
    )
    out = await _invoke(
        mcp,
        "get_conversion_stats",
        {
            "conversion_id": 1,  # no row matches
            "date_from": "2026-04-01",
            "date_to": "2026-04-30",
        },
    )
    assert out == {"report": []}


async def test_get_conversion_stats_passes_explicit_granularity():
    mcp, client = _setup({"status": 200, "report": []})
    await _invoke(
        mcp,
        "get_conversion_stats",
        {
            "conversion_id": 1,
            "date_from": "2026-04-01",
            "date_to": "2026-04-30",
            "granularity": "monthly",
        },
    )
    assert client.call.call_args[0][1]["granularity"] == "monthly"

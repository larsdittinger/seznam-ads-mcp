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


async def test_get_stats_campaign_daily():
    mcp, client = _setup(
        {
            "status": 200,
            "report": [
                {
                    "id": 1,
                    "stats": [
                        {
                            "date": "2026-04-01",
                            "impressions": 100,
                            "clicks": 5,
                            "spend": 12345,
                        }
                    ],
                }
            ],
        }
    )
    out = await _invoke(
        mcp,
        "get_stats",
        {
            "entity": "campaign",
            "entity_ids": [1],
            "date_from": "2026-04-01",
            "date_to": "2026-04-30",
            "granularity": "daily",
        },
    )
    args = client.call.call_args
    assert args[0][0] == "campaigns.stats"
    filt = args[0][1]
    assert filt["dateFrom"] == "2026-04-01"
    assert filt["dateTo"] == "2026-04-30"
    assert filt["granularity"] == "daily"
    assert filt["ids"] == [1]
    assert out["report"][0]["id"] == 1
    # spend formatted to Kč
    assert out["report"][0]["stats"][0]["spend_kc"] == 123.45


async def test_get_stats_default_granularity_total():
    mcp, client = _setup({"status": 200, "report": []})
    await _invoke(
        mcp,
        "get_stats",
        {
            "entity": "ad",
            "entity_ids": [9, 10],
            "date_from": "2026-04-01",
            "date_to": "2026-04-02",
        },
    )
    args = client.call.call_args
    assert args[0][0] == "ads.stats"
    assert args[0][1]["granularity"] == "total"
    assert args[0][1]["ids"] == [9, 10]


async def test_get_stats_keyword_method():
    mcp, client = _setup({"status": 200, "report": []})
    await _invoke(
        mcp,
        "get_stats",
        {
            "entity": "keyword",
            "entity_ids": [1],
            "date_from": "2026-04-01",
            "date_to": "2026-04-02",
        },
    )
    assert client.call.call_args[0][0] == "keywords.stats"


async def test_get_stats_group_method():
    mcp, client = _setup({"status": 200, "report": []})
    await _invoke(
        mcp,
        "get_stats",
        {
            "entity": "group",
            "entity_ids": [1],
            "date_from": "2026-04-01",
            "date_to": "2026-04-02",
        },
    )
    assert client.call.call_args[0][0] == "groups.stats"


async def test_get_account_overview():
    mcp, client = _setup(
        {
            "status": 200,
            "stats": {"impressions": 1000, "clicks": 50, "spend": 50_000},
        }
    )
    out = await _invoke(
        mcp,
        "get_account_overview",
        {"date_from": "2026-04-01", "date_to": "2026-04-30"},
    )
    args = client.call.call_args
    assert args[0][0] == "client.stats"
    assert args[0][1] == {"dateFrom": "2026-04-01", "dateTo": "2026-04-30"}
    assert out["spend_kc"] == 500.0
    assert out["impressions"] == 1000

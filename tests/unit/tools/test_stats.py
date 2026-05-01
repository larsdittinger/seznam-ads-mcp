from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.tools import stats


def _setup(call_returns):
    """Single-shot mock — every client.call returns the same dict."""
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    client.call.return_value = call_returns
    stats.register(mcp, client)
    return mcp, client


def _setup_seq(side_effects):
    """Sequential mock — first client.call returns side_effects[0], etc.

    Used for the createReport→readReport flow in per-entity stats tools.
    """
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    client.call.side_effect = side_effects
    stats.register(mcp, client)
    return mcp, client


async def _invoke(mcp, name, args):
    return await mcp._tool_manager._tools[name].run(args)


# ── client.stats (account overview) ─────────────────────────────────────────


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
                {"date": "x", "impressions": 1000, "clicks": 50, "price": 50_000, "cpc": 1000},
            ],
        }
    )
    out = await _invoke(
        mcp,
        "get_account_overview",
        {"date_from": "2026-04-01", "date_to": "2026-04-30"},
    )
    assert out["report"][0]["price_kc"] == 500.0
    assert out["report"][0]["cpc_kc"] == 10.0
    assert out["report"][0]["impressions"] == 1000


async def test_get_account_overview_passes_explicit_granularity():
    mcp, client = _setup({"status": 200, "report": []})
    await _invoke(
        mcp,
        "get_account_overview",
        {"date_from": "2026-04-01", "date_to": "2026-04-30", "granularity": "monthly"},
    )
    assert client.call.call_args[0][1]["granularity"] == "monthly"


async def test_get_account_overview_handles_empty_report():
    mcp, _client = _setup({"status": 200, "report": []})
    out = await _invoke(
        mcp,
        "get_account_overview",
        {"date_from": "2026-04-01", "date_to": "2026-04-30"},
    )
    assert out == {"report": []}


async def test_get_account_overview_split_by_conversions_passes_flag():
    mcp, client = _setup(
        {
            "status": 200,
            "report": [
                {
                    "date": "20260101T00:00:00+0000",
                    "impressions": 10,
                    "conversionList": [
                        {"id": 100, "conversions": 3, "conversionValue": 50_000},
                    ],
                },
            ],
        }
    )
    out = await _invoke(
        mcp,
        "get_account_overview",
        {
            "date_from": "2026-04-01",
            "date_to": "2026-04-30",
            "split_by_conversions": True,
        },
    )
    args = client.call.call_args
    assert args[0][1]["splitByConversions"] is True
    # conversionList entries get _kc fields too
    cl = out["report"][0]["conversionList"][0]
    assert cl["conversionValue_kc"] == 500.0


# ── per-entity stats: campaigns ─────────────────────────────────────────────


async def test_get_campaign_stats_create_then_read_flow():
    mcp, client = _setup_seq(
        [
            {"status": 200, "reportId": "rep-123", "totalCount": 1},
            {
                "status": 200,
                "report": [
                    {
                        "id": 6994504,
                        "name": "kampan",
                        "status": "active",
                        "stats": [
                            {
                                "date": 202511,
                                "clicks": 27,
                                "impressions": 10703,
                                "totalMoney": 25171,
                                "avgCpc": 932,
                            },
                        ],
                    },
                ],
            },
        ]
    )
    out = await _invoke(
        mcp,
        "get_campaign_stats",
        {
            "date_from": "2025-11-01",
            "date_to": "2026-04-30",
            "campaign_ids": [6994504],
            "granularity": "monthly",
        },
    )
    # Verified two-call sequence
    assert client.call.call_count == 2
    create_call = client.call.call_args_list[0]
    read_call = client.call.call_args_list[1]

    assert create_call[0][0] == "campaigns.createReport"
    assert create_call[0][1] == {
        "dateFrom": "2025-11-01",
        "dateTo": "2026-04-30",
        "ids": [6994504],
    }
    assert create_call[0][2] == {"statGranularity": "monthly"}

    assert read_call[0][0] == "campaigns.readReport"
    assert read_call[0][1] == "rep-123"
    # default include_zeros=False maps to allowEmptyStatistics=False
    assert read_call[0][2]["allowEmptyStatistics"] is False
    # explicit displayColumns are always sent
    assert "totalMoney" in read_call[0][2]["displayColumns"]
    assert "ctr" in read_call[0][2]["displayColumns"]

    # Money fields get _kc mirrors
    row = out["report"][0]
    assert row["stats"][0]["totalMoney_kc"] == 251.71
    assert row["stats"][0]["avgCpc_kc"] == 9.32
    assert out["total"] == 1


async def test_get_campaign_stats_no_ids_filter():
    mcp, client = _setup_seq(
        [
            {"status": 200, "reportId": "x", "totalCount": 0},
            {"status": 200, "report": []},
        ]
    )
    await _invoke(
        mcp,
        "get_campaign_stats",
        {"date_from": "2026-01-01", "date_to": "2026-04-30"},
    )
    create_filter = client.call.call_args_list[0][0][1]
    assert "ids" not in create_filter


async def test_get_campaign_stats_include_zeros_passes_through():
    mcp, client = _setup_seq(
        [{"status": 200, "reportId": "x", "totalCount": 0}, {"status": 200, "report": []}]
    )
    await _invoke(
        mcp,
        "get_campaign_stats",
        {"date_from": "2026-01-01", "date_to": "2026-04-30", "include_zeros": True},
    )
    read_opts = client.call.call_args_list[1][0][2]
    assert read_opts["allowEmptyStatistics"] is True


async def test_get_campaign_stats_no_report_id_handles_gracefully():
    mcp, _client = _setup_seq([{"status": 200}])  # createReport returns no reportId
    out = await _invoke(
        mcp,
        "get_campaign_stats",
        {"date_from": "2026-01-01", "date_to": "2026-04-30"},
    )
    assert out == {"report": [], "total": 0}


# ── per-entity stats: groups ────────────────────────────────────────────────


async def test_get_ad_group_stats_filters_by_campaign():
    mcp, client = _setup_seq(
        [
            {"status": 200, "reportId": "g-1", "totalCount": 4},
            {"status": 200, "report": [{"id": 147102422, "stats": []}]},
        ]
    )
    await _invoke(
        mcp,
        "get_ad_group_stats",
        {
            "date_from": "2025-11-01",
            "date_to": "2026-04-30",
            "campaign_id": 6994504,
        },
    )
    create_filter = client.call.call_args_list[0][0][1]
    # campaign filter is nested
    assert create_filter["campaign"] == {"ids": [6994504]}
    # method is groups.createReport
    assert client.call.call_args_list[0][0][0] == "groups.createReport"


# ── per-entity stats: ads ───────────────────────────────────────────────────


async def test_get_ad_stats_filters_by_group():
    mcp, client = _setup_seq(
        [
            {"status": 200, "reportId": "a-1", "totalCount": 3},
            {"status": 200, "report": []},
        ]
    )
    await _invoke(
        mcp,
        "get_ad_stats",
        {
            "date_from": "2025-11-01",
            "date_to": "2026-04-30",
            "group_id": 147102422,
        },
    )
    create_filter = client.call.call_args_list[0][0][1]
    assert create_filter["group"] == {"ids": [147102422]}
    assert client.call.call_args_list[0][0][0] == "ads.createReport"


# ── per-entity stats: keywords ──────────────────────────────────────────────


async def test_get_keyword_stats_filter_combinations():
    mcp, client = _setup_seq(
        [
            {"status": 200, "reportId": "k-1", "totalCount": 0},
            {"status": 200, "report": []},
        ]
    )
    await _invoke(
        mcp,
        "get_keyword_stats",
        {
            "date_from": "2025-11-01",
            "date_to": "2026-04-30",
            "keyword_ids": [1, 2, 3],
            "campaign_id": 100,
            "granularity": "weekly",
        },
    )
    create_args = client.call.call_args_list[0][0]
    assert create_args[0] == "keywords.createReport"
    assert create_args[1]["ids"] == [1, 2, 3]
    assert create_args[1]["campaign"] == {"ids": [100]}
    assert create_args[2] == {"statGranularity": "weekly"}

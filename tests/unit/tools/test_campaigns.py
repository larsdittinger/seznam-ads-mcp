from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.tools import campaigns


def _setup(call_returns):
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    client.call.return_value = call_returns
    campaigns.register(mcp, client)
    return mcp, client


async def _invoke(mcp, name, args):
    return await mcp._tool_manager._tools[name].run(args)


async def test_list_campaigns_calls_correct_method():
    mcp, client = _setup(
        {
            "status": 200,
            "campaigns": [{"id": 1, "name": "test", "status": "active"}],
            "totalCount": 1,
        }
    )
    out = await _invoke(mcp, "list_campaigns", {})
    assert out["campaigns"][0]["id"] == 1
    assert out["total"] == 1
    args = client.call.call_args
    assert args[0][0] == "campaigns.list"
    # filter struct (2nd) and options struct (3rd)
    assert args[0][1] == {}
    # Limit/offset always set; allow defaults
    assert "limit" in args[0][2]
    assert "offset" in args[0][2]


async def test_list_campaigns_passes_filters():
    mcp, client = _setup({"status": 200, "campaigns": [], "totalCount": 0})
    await _invoke(
        mcp,
        "list_campaigns",
        {"status_filter": "active", "name_contains": "foo", "limit": 50},
    )
    args = client.call.call_args
    assert args[0][0] == "campaigns.list"
    filter_struct = args[0][1]
    assert filter_struct["status"] == "active"
    assert filter_struct["name"] == "foo"
    options = args[0][2]
    assert options["limit"] == 50


async def test_get_campaign_filters_by_id():
    mcp, client = _setup({"status": 200, "campaigns": [{"id": 7, "name": "x"}]})
    out = await _invoke(mcp, "get_campaign", {"campaign_id": 7})
    assert out["campaign"]["id"] == 7
    args = client.call.call_args
    assert args[0][0] == "campaigns.list"
    assert args[0][1]["id"] == [7]


async def test_pause_campaign_sets_status():
    mcp, client = _setup({"status": 200})
    await _invoke(mcp, "pause_campaign", {"campaign_id": 9})
    args = client.call.call_args
    assert args[0][0] == "campaigns.update"
    assert args[0][1] == [{"id": 9, "status": "paused"}]


async def test_resume_campaign_sets_status_active():
    mcp, client = _setup({"status": 200})
    await _invoke(mcp, "resume_campaign", {"campaign_id": 9})
    args = client.call.call_args
    assert args[0][1] == [{"id": 9, "status": "active"}]


async def test_create_campaign_passes_fields():
    mcp, client = _setup({"status": 200, "campaignIds": [123]})
    out = await _invoke(
        mcp,
        "create_campaign",
        {"name": "Q2 brand", "daily_budget_kc": 500, "currency": "CZK"},
    )
    assert out["campaign_id"] == 123
    args = client.call.call_args
    assert args[0][0] == "campaigns.create"
    body = args[0][1][0]
    assert body["name"] == "Q2 brand"
    # 500 Kč → 50000 haléřů
    assert body["dayBudget"] == 50_000
    assert body["currency"] == "CZK"


async def test_update_campaign_sends_partial():
    mcp, client = _setup({"status": 200})
    await _invoke(mcp, "update_campaign", {"campaign_id": 1, "name": "renamed"})
    body = client.call.call_args[0][1][0]
    assert body == {"id": 1, "name": "renamed"}


async def test_remove_campaign():
    mcp, client = _setup({"status": 200})
    await _invoke(mcp, "remove_campaign", {"campaign_id": 5})
    assert client.call.call_args[0] == ("campaigns.remove", [5])

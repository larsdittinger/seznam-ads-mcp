from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.tools import ad_groups


def _setup(call_returns):
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    client.call.return_value = call_returns
    ad_groups.register(mcp, client)
    return mcp, client


async def _invoke(mcp, name, args):
    return await mcp._tool_manager._tools[name].run(args)


async def test_list_ad_groups_calls_correct_method():
    mcp, client = _setup(
        {
            "status": 200,
            "groups": [{"id": 1, "name": "test", "status": "active"}],
            "totalCount": 1,
        }
    )
    out = await _invoke(mcp, "list_ad_groups", {})
    assert out["groups"][0]["id"] == 1
    assert out["total"] == 1
    args = client.call.call_args
    assert args[0][0] == "groups.list"
    assert args[0][1] == {}


async def test_list_ad_groups_filters_by_campaign():
    mcp, client = _setup({"status": 200, "groups": [], "totalCount": 0})
    await _invoke(mcp, "list_ad_groups", {"campaign_id": 5})
    args = client.call.call_args
    assert args[0][0] == "groups.list"
    filter_struct = args[0][1]
    # Sklik nests parent-entity filters: {"campaign": {"ids": [...]}}.
    assert filter_struct == {"campaign": {"ids": [5]}}


async def test_list_ad_groups_passes_filters():
    mcp, client = _setup({"status": 200, "groups": [], "totalCount": 0})
    await _invoke(
        mcp,
        "list_ad_groups",
        {"status_filter": "active", "name_contains": "foo", "limit": 50},
    )
    args = client.call.call_args
    filter_struct = args[0][1]
    assert filter_struct["status"] == "active"
    assert filter_struct["name"] == "foo"
    options = args[0][2]
    assert options["limit"] == 50


async def test_get_ad_group_filters_by_id():
    mcp, client = _setup({"status": 200, "groups": [{"id": 7, "name": "x"}]})
    out = await _invoke(mcp, "get_ad_group", {"group_id": 7})
    assert out["group"]["id"] == 7
    args = client.call.call_args
    assert args[0][0] == "groups.list"
    assert args[0][1]["ids"] == [7]


async def test_pause_ad_group_sets_status():
    mcp, client = _setup({"status": 200})
    await _invoke(mcp, "pause_ad_group", {"group_id": 9})
    args = client.call.call_args
    assert args[0][0] == "groups.update"
    assert args[0][1] == [{"id": 9, "status": "paused"}]


async def test_resume_ad_group_sets_status_active():
    mcp, client = _setup({"status": 200})
    await _invoke(mcp, "resume_ad_group", {"group_id": 9})
    args = client.call.call_args
    assert args[0][1] == [{"id": 9, "status": "active"}]


async def test_create_ad_group_passes_fields():
    mcp, client = _setup({"status": 200, "groupIds": [321]})
    out = await _invoke(
        mcp,
        "create_ad_group",
        {"campaign_id": 11, "name": "brand-cz", "max_cpc_kc": 4},
    )
    assert out["group_id"] == 321
    args = client.call.call_args
    assert args[0][0] == "groups.create"
    body = args[0][1][0]
    assert body["campaignId"] == 11
    assert body["name"] == "brand-cz"
    # 4 Kč → 400 haléřů
    assert body["maxCpc"] == 400


async def test_update_ad_group_sends_partial():
    mcp, client = _setup({"status": 200})
    await _invoke(mcp, "update_ad_group", {"group_id": 1, "name": "renamed"})
    body = client.call.call_args[0][1][0]
    assert body == {"id": 1, "name": "renamed"}


async def test_remove_ad_group():
    mcp, client = _setup({"status": 200})
    await _invoke(mcp, "remove_ad_group", {"group_id": 5})
    assert client.call.call_args[0] == ("groups.remove", [5])

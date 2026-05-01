from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.tools import ads


def _setup(call_returns):
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    client.call.return_value = call_returns
    ads.register(mcp, client)
    return mcp, client


async def _invoke(mcp, name, args):
    return await mcp._tool_manager._tools[name].run(args)


async def test_list_ads_happy_path():
    mcp, client = _setup(
        {
            "status": 200,
            "ads": [{"id": 1, "type": "text", "status": "active"}],
            "totalCount": 1,
        }
    )
    out = await _invoke(mcp, "list_ads", {})
    assert out["ads"][0]["id"] == 1
    assert out["total"] == 1
    args = client.call.call_args
    assert args[0][0] == "ads.list"
    assert args[0][1] == {}


async def test_list_ads_filters_by_group_clientside_status():
    mcp, client = _setup(
        {
            "status": 200,
            "ads": [
                {"id": 1, "status": "active"},
                {"id": 2, "status": "suspend"},
            ],
        }
    )
    out = await _invoke(
        mcp,
        "list_ads",
        {"group_id": 9, "status": "active", "limit": 25},
    )
    args = client.call.call_args
    filt = args[0][1]
    # Sklik nests parent-entity filters: {"group": {"ids": [...]}}.
    assert filt["group"] == {"ids": [9]}
    # status is NOT sent on the wire — applied client-side.
    assert "status" not in filt
    opts = args[0][2]
    assert opts["limit"] == 25
    assert [a["id"] for a in out["ads"]] == [1]


async def test_get_ad_filters_by_id():
    mcp, client = _setup({"status": 200, "ads": [{"id": 7, "type": "text"}]})
    out = await _invoke(mcp, "get_ad", {"ad_id": 7})
    assert out["ad"]["id"] == 7
    args = client.call.call_args
    assert args[0][0] == "ads.list"
    assert args[0][1]["ids"] == [7]


async def test_create_text_ad_sends_correct_body():
    mcp, client = _setup({"status": 200, "adIds": [555]})
    out = await _invoke(
        mcp,
        "create_text_ad",
        {
            "group_id": 1,
            "headline1": "Hlavní nadpis",
            "headline2": "Druhý nadpis",
            "description1": "Popisek",
            "final_url": "https://example.cz",
        },
    )
    assert out["ad_id"] == 555
    args = client.call.call_args
    assert args[0][0] == "ads.create"
    body = args[0][1][0]
    # ads.create does NOT accept a `type` field (Sklik infers from group/fields).
    assert "type" not in body
    assert body["groupId"] == 1
    assert body["headline1"] == "Hlavní nadpis"
    assert body["headline2"] == "Druhý nadpis"
    # Sklik's first description field is just "description" (singular, no "1").
    assert body["description"] == "Popisek"
    assert "description1" not in body
    assert body["finalUrl"] == "https://example.cz"
    # Optional fields not set
    assert "headline3" not in body
    assert "description2" not in body


async def test_create_text_ad_includes_optional_fields():
    mcp, client = _setup({"status": 200, "adIds": [556]})
    await _invoke(
        mcp,
        "create_text_ad",
        {
            "group_id": 1,
            "headline1": "h1",
            "headline2": "h2",
            "headline3": "h3",
            "description1": "d1",
            "description2": "d2",
            "final_url": "https://example.cz",
        },
    )
    body = client.call.call_args[0][1][0]
    assert body["headline3"] == "h3"
    assert body["description2"] == "d2"


async def test_update_ad_sends_partial_fields():
    mcp, client = _setup({"status": 200})
    await _invoke(
        mcp,
        "update_ad",
        {"ad_id": 11, "headline1": "nový nadpis"},
    )
    args = client.call.call_args
    assert args[0][0] == "ads.update"
    body = args[0][1][0]
    assert body == {"id": 11, "headline1": "nový nadpis"}


async def test_pause_ad_sends_status_suspend():
    """Sklik wire status is 'suspend', not 'paused'."""
    mcp, client = _setup({"status": 200})
    await _invoke(mcp, "pause_ad", {"ad_id": 9})
    args = client.call.call_args
    assert args[0][0] == "ads.update"
    assert args[0][1] == [{"id": 9, "status": "suspend"}]


async def test_resume_ad_sends_status_active():
    mcp, client = _setup({"status": 200})
    await _invoke(mcp, "resume_ad", {"ad_id": 9})
    args = client.call.call_args
    assert args[0][1] == [{"id": 9, "status": "active"}]


async def test_remove_ad_uses_correct_method():
    mcp, client = _setup({"status": 200})
    await _invoke(mcp, "remove_ad", {"ad_id": 5})
    assert client.call.call_args[0] == ("ads.remove", [5])

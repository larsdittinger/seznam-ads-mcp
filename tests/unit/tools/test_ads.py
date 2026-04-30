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


async def test_list_ads_filters_by_group_and_status():
    mcp, client = _setup({"status": 200, "ads": [], "totalCount": 0})
    await _invoke(
        mcp,
        "list_ads",
        {"group_id": 9, "status": "active", "limit": 25},
    )
    args = client.call.call_args
    filt = args[0][1]
    # Sklik nests parent-entity filters: {"group": {"ids": [...]}}.
    assert filt["group"] == {"ids": [9]}
    assert filt["status"] == "active"
    opts = args[0][2]
    assert opts["limit"] == 25


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
    assert body["type"] == "text"
    assert body["groupId"] == 1
    assert body["headline1"] == "Hlavní nadpis"
    assert body["headline2"] == "Druhý nadpis"
    assert body["description1"] == "Popisek"
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


async def test_create_dynamic_ad_sends_correct_body():
    mcp, client = _setup({"status": 200, "adIds": [777]})
    out = await _invoke(
        mcp,
        "create_dynamic_ad",
        {
            "group_id": 2,
            "final_url": "https://shop.cz",
            "description1": "Popis dynamicky",
        },
    )
    assert out["ad_id"] == 777
    body = client.call.call_args[0][1][0]
    assert body["type"] == "dynamic"
    assert body["groupId"] == 2
    assert body["finalUrl"] == "https://shop.cz"
    assert body["description1"] == "Popis dynamicky"


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


async def test_pause_ad_sends_status_paused():
    mcp, client = _setup({"status": 200})
    await _invoke(mcp, "pause_ad", {"ad_id": 9})
    args = client.call.call_args
    assert args[0][0] == "ads.update"
    assert args[0][1] == [{"id": 9, "status": "paused"}]


async def test_resume_ad_sends_status_active():
    mcp, client = _setup({"status": 200})
    await _invoke(mcp, "resume_ad", {"ad_id": 9})
    args = client.call.call_args
    assert args[0][1] == [{"id": 9, "status": "active"}]


async def test_remove_ad_uses_correct_method():
    mcp, client = _setup({"status": 200})
    await _invoke(mcp, "remove_ad", {"ad_id": 5})
    assert client.call.call_args[0] == ("ads.remove", [5])

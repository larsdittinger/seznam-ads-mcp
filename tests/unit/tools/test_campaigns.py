from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.core.errors import NotFoundError
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


async def test_list_campaigns_passes_filters_clientside():
    """status_filter and name_contains are applied client-side; Sklik v5
    doesn't accept them in the wire filter struct."""
    mcp, client = _setup(
        {
            "status": 200,
            "campaigns": [
                {"id": 1, "name": "Foo letní", "status": "active"},
                {"id": 2, "name": "Bar letní", "status": "suspend"},
                {"id": 3, "name": "FOOzimní", "status": "active"},
            ],
        }
    )
    out = await _invoke(
        mcp,
        "list_campaigns",
        {"status_filter": "active", "name_contains": "foo", "limit": 50},
    )
    args = client.call.call_args
    assert args[0][0] == "campaigns.list"
    # Wire filter struct is empty (or only has fields Sklik accepts).
    assert args[0][1] == {}
    options = args[0][2]
    assert options["limit"] == 50
    # Client-side filtering: only active+name-contains-foo (case-insensitive).
    ids = [c["id"] for c in out["campaigns"]]
    assert ids == [1, 3]


async def test_get_campaign_filters_by_id():
    mcp, client = _setup({"status": 200, "campaigns": [{"id": 7, "name": "x"}]})
    out = await _invoke(mcp, "get_campaign", {"campaign_id": 7})
    assert out["campaign"]["id"] == 7
    args = client.call.call_args
    assert args[0][0] == "campaigns.list"
    # Sklik filters by id with the key "ids" (plural list).
    assert args[0][1]["ids"] == [7]


async def test_pause_campaign_sets_status():
    """pause uses Sklik wire status 'suspend' and includes the auto-fetched type."""
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    # First call (campaigns.list) returns the type; second call (update) returns OK.
    client.call.side_effect = [
        {"status": 200, "campaigns": [{"id": 9, "type": "fulltext", "status": "active"}]},
        {"status": 200},
    ]
    campaigns.register(mcp, client)
    await _invoke(mcp, "pause_campaign", {"campaign_id": 9})
    update_call = client.call.call_args  # last call
    assert update_call[0][0] == "campaigns.update"
    assert update_call[0][1] == [{"id": 9, "type": "fulltext", "status": "suspend"}]


async def test_resume_campaign_sets_status_active():
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    client.call.side_effect = [
        {"status": 200, "campaigns": [{"id": 9, "type": "context"}]},
        {"status": 200},
    ]
    campaigns.register(mcp, client)
    await _invoke(mcp, "resume_campaign", {"campaign_id": 9})
    update_call = client.call.call_args
    assert update_call[0][1] == [{"id": 9, "type": "context", "status": "active"}]


async def test_create_campaign_passes_fields():
    mcp, client = _setup({"status": 200, "campaignIds": [123]})
    out = await _invoke(
        mcp,
        "create_campaign",
        {"name": "Q2 brand", "daily_budget_kc": 500, "campaign_type": "fulltext"},
    )
    assert out["campaign_id"] == 123
    args = client.call.call_args
    assert args[0][0] == "campaigns.create"
    body = args[0][1][0]
    assert body["name"] == "Q2 brand"
    # 500 Kč → 50000 haléřů
    assert body["dayBudget"] == 50_000
    # type is required by Sklik on create
    assert body["type"] == "fulltext"


async def test_update_campaign_sends_partial_with_fetched_type():
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    client.call.side_effect = [
        {"status": 200, "campaigns": [{"id": 1, "type": "zbozi"}]},
        {"status": 200},
    ]
    campaigns.register(mcp, client)
    await _invoke(mcp, "update_campaign", {"campaign_id": 1, "name": "renamed"})
    body = client.call.call_args[0][1][0]
    # campaigns.update demands `type`; we auto-fetch and inject it.
    assert body == {"id": 1, "type": "zbozi", "name": "renamed"}


async def test_remove_campaign():
    mcp, client = _setup({"status": 200})
    await _invoke(mcp, "remove_campaign", {"campaign_id": 5})
    assert client.call.call_args[0] == ("campaigns.remove", [5])


async def test_tool_wraps_sklik_error_with_czech_hint():
    """SklikError raised by the client should be turned into a structured dict
    with a Czech-language `hint_cs`, not propagated as an exception."""
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    client.call.side_effect = NotFoundError(
        "Campaign 999 not found", status=404, details=["no such id"]
    )
    campaigns.register(mcp, client)
    out = await _invoke(mcp, "get_campaign", {"campaign_id": 999})
    assert out["error"] is True
    assert out["error_type"] == "NotFoundError"
    assert out["message"] == "Campaign 999 not found"
    assert out["status"] == 404
    assert out["details"] == ["no such id"]
    # Czech hint must be present and mention the right thing
    assert "neexistuje" in out["hint_cs"]

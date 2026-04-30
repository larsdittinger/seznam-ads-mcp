from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.tools import negative_keywords


def _setup(call_returns):
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    client.call.return_value = call_returns
    negative_keywords.register(mcp, client)
    return mcp, client


async def _invoke(mcp, name, args):
    return await mcp._tool_manager._tools[name].run(args)


async def test_set_campaign_negative_keywords_replaces_full_list():
    mcp, client = _setup({"status": 200})
    out = await _invoke(
        mcp,
        "set_campaign_negative_keywords",
        {
            "campaign_id": 7,
            "campaign_type": "fulltext",
            "keywords": [
                {"name": "zdarma", "match_type": "broad"},
                {"name": "levně", "match_type": "exact"},
            ],
        },
    )
    assert out == {"updated": True, "count": 2}
    args = client.call.call_args
    assert args[0][0] == "campaigns.update"
    # campaigns.update expects a list of update structs.
    body = args[0][1]
    assert isinstance(body, list) and len(body) == 1
    update = body[0]
    assert update["id"] == 7
    assert update["type"] == "fulltext"
    # match_type values map to negativeBroad / negativePhrase / negativeExact.
    assert update["negativeKeywords"] == [
        {"name": "zdarma", "matchType": "negativeBroad"},
        {"name": "levně", "matchType": "negativeExact"},
    ]


async def test_set_campaign_negative_keywords_empty_list_clears():
    mcp, client = _setup({"status": 200})
    out = await _invoke(
        mcp,
        "set_campaign_negative_keywords",
        {"campaign_id": 7, "campaign_type": "context", "keywords": []},
    )
    assert out == {"updated": True, "count": 0}
    body = client.call.call_args[0][1]
    assert body[0]["negativeKeywords"] == []


async def test_set_campaign_negative_keywords_default_match_type_is_broad():
    mcp, client = _setup({"status": 200})
    await _invoke(
        mcp,
        "set_campaign_negative_keywords",
        {
            "campaign_id": 7,
            "campaign_type": "fulltext",
            "keywords": [{"name": "ahoj"}],  # no match_type → default broad
        },
    )
    body = client.call.call_args[0][1]
    assert body[0]["negativeKeywords"] == [{"name": "ahoj", "matchType": "negativeBroad"}]

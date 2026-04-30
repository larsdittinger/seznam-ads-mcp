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


async def test_list_negative_keywords_campaign_scope():
    mcp, client = _setup({"status": 200, "negativeKeywords": []})
    await _invoke(mcp, "list_negative_keywords", {"scope": "campaign", "scope_id": 5})
    assert client.call.call_args[0][0] == "campaigns.getNegativeKeywords"
    assert client.call.call_args[0][1] == {"id": 5}


async def test_list_negative_keywords_group_scope():
    mcp, client = _setup({"status": 200, "negativeKeywords": []})
    await _invoke(mcp, "list_negative_keywords", {"scope": "group", "scope_id": 5})
    assert client.call.call_args[0][0] == "groups.getNegativeKeywords"
    assert client.call.call_args[0][1] == {"id": 5}


async def test_list_negative_keywords_returns_data():
    mcp, _client = _setup(
        {
            "status": 200,
            "negativeKeywords": [{"id": 1, "keyword": "zdarma"}],
        }
    )
    out = await _invoke(mcp, "list_negative_keywords", {"scope": "campaign", "scope_id": 5})
    assert out["negative_keywords"][0]["keyword"] == "zdarma"


async def test_add_negative_keywords_campaign_scope():
    mcp, client = _setup({"status": 200, "negativeKeywordIds": [11, 12]})
    out = await _invoke(
        mcp,
        "add_negative_keywords",
        {"scope": "campaign", "scope_id": 7, "keywords": ["zdarma", "diy"]},
    )
    assert out["added"] == 2
    assert out["ids"] == [11, 12]
    args = client.call.call_args
    assert args[0][0] == "campaigns.addNegativeKeywords"
    assert args[0][1] == {"id": 7}
    assert args[0][2] == [{"keyword": "zdarma"}, {"keyword": "diy"}]


async def test_add_negative_keywords_group_scope_routes_correctly():
    mcp, client = _setup({"status": 200, "negativeKeywordIds": [99]})
    await _invoke(
        mcp,
        "add_negative_keywords",
        {"scope": "group", "scope_id": 3, "keywords": ["foo"]},
    )
    assert client.call.call_args[0][0] == "groups.addNegativeKeywords"


async def test_remove_negative_keyword_campaign_scope():
    mcp, client = _setup({"status": 200})
    out = await _invoke(
        mcp,
        "remove_negative_keyword",
        {"scope": "campaign", "scope_id": 5, "negative_keyword_id": 42},
    )
    assert out == {"removed": True}
    args = client.call.call_args
    assert args[0][0] == "campaigns.removeNegativeKeyword"
    assert args[0][1] == {"id": 5, "negativeKeywordId": 42}


async def test_remove_negative_keyword_group_scope():
    mcp, client = _setup({"status": 200})
    await _invoke(
        mcp,
        "remove_negative_keyword",
        {"scope": "group", "scope_id": 5, "negative_keyword_id": 42},
    )
    assert client.call.call_args[0][0] == "groups.removeNegativeKeyword"

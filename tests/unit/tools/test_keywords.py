from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.tools import keywords


def _setup(call_returns):
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    client.call.return_value = call_returns
    keywords.register(mcp, client)
    return mcp, client


async def _invoke(mcp, name, args):
    return await mcp._tool_manager._tools[name].run(args)


async def test_list_keywords_happy_path():
    mcp, client = _setup(
        {
            "status": 200,
            "keywords": [{"id": 1, "keyword": "boty", "matchType": "broad"}],
            "totalCount": 1,
        }
    )
    out = await _invoke(mcp, "list_keywords", {})
    assert out["keywords"][0]["id"] == 1
    assert out["total"] == 1
    args = client.call.call_args
    assert args[0][0] == "keywords.list"
    assert args[0][1] == {}


async def test_list_keywords_filters_by_group_and_status():
    mcp, client = _setup({"status": 200, "keywords": [], "totalCount": 0})
    await _invoke(
        mcp,
        "list_keywords",
        {"group_id": 9, "status": "active", "limit": 25},
    )
    args = client.call.call_args
    filt = args[0][1]
    # Sklik nests parent-entity filters: {"group": {"ids": [...]}}.
    assert filt["group"] == {"ids": [9]}
    assert filt["status"] == "active"
    opts = args[0][2]
    assert opts["limit"] == 25


async def test_get_keyword_filters_by_id():
    mcp, client = _setup({"status": 200, "keywords": [{"id": 7, "keyword": "x"}]})
    out = await _invoke(mcp, "get_keyword", {"keyword_id": 7})
    assert out["keyword"]["id"] == 7
    args = client.call.call_args
    assert args[0][0] == "keywords.list"
    assert args[0][1]["ids"] == [7]


async def test_add_keywords_sends_batch_with_match_types():
    mcp, client = _setup({"status": 200, "keywordIds": [1, 2]})
    out = await _invoke(
        mcp,
        "add_keywords",
        {
            "group_id": 10,
            "keywords": [
                {"keyword": "foto", "match_type": "exact", "max_cpc_kc": 5},
                {"keyword": "obraz", "match_type": "phrase", "max_cpc_kc": None},
            ],
        },
    )
    assert out["keyword_ids"] == [1, 2]
    body = client.call.call_args[0][1]
    # Sklik wants the keyword text under "name", and matchType is broad/phrase/exact verbatim.
    assert body[0] == {"groupId": 10, "name": "foto", "matchType": "exact", "maxCpc": 500}
    assert body[1] == {"groupId": 10, "name": "obraz", "matchType": "phrase"}


async def test_add_keywords_uses_correct_method():
    mcp, client = _setup({"status": 200, "keywordIds": [42]})
    await _invoke(
        mcp,
        "add_keywords",
        {
            "group_id": 1,
            "keywords": [{"keyword": "test", "match_type": "broad", "max_cpc_kc": 3}],
        },
    )
    assert client.call.call_args[0][0] == "keywords.create"


async def test_update_keyword_sends_partial_fields():
    mcp, client = _setup({"status": 200})
    await _invoke(
        mcp,
        "update_keyword",
        {"keyword_id": 11, "max_cpc_kc": 7},
    )
    args = client.call.call_args
    assert args[0][0] == "keywords.update"
    body = args[0][1][0]
    # 7 Kč → 700 haléřů
    assert body == {"id": 11, "maxCpc": 700}


async def test_pause_keyword_sets_status_paused():
    mcp, client = _setup({"status": 200})
    await _invoke(mcp, "pause_keyword", {"keyword_id": 9})
    args = client.call.call_args
    assert args[0][0] == "keywords.update"
    assert args[0][1] == [{"id": 9, "status": "paused"}]


async def test_resume_keyword_sets_status_active():
    mcp, client = _setup({"status": 200})
    await _invoke(mcp, "resume_keyword", {"keyword_id": 9})
    args = client.call.call_args
    assert args[0][1] == [{"id": 9, "status": "active"}]


async def test_remove_keyword_uses_correct_method():
    mcp, client = _setup({"status": 200})
    await _invoke(mcp, "remove_keyword", {"keyword_id": 5})
    assert client.call.call_args[0] == ("keywords.remove", [5])

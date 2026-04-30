from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.tools import retargeting


def _setup(call_returns):
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    client.call.return_value = call_returns
    retargeting.register(mcp, client)
    return mcp, client


async def _invoke(mcp, name, args):
    return await mcp._tool_manager._tools[name].run(args)


async def test_list_retargeting_lists_calls_correct_method():
    mcp, client = _setup(
        {
            "status": 200,
            "lists": [{"id": 1, "name": "vrátí se"}],
        }
    )
    out = await _invoke(mcp, "list_retargeting_lists", {})
    # No extra args, just auth (auto-prepended by SklikClient.call)
    assert client.call.call_args == (("retargeting.lists.list",), {})
    assert out["retargeting_lists"][0]["id"] == 1


async def test_create_retargeting_list_default_lifespan():
    mcp, client = _setup({"status": 200, "retargetingId": 42})
    out = await _invoke(mcp, "create_retargeting_list", {"name": "návštěvníci"})
    args = client.call.call_args
    assert args[0][0] == "retargeting.lists.create"
    assert args[0][1] == {"name": "návštěvníci", "membershipLifespan": 30}
    assert out["retargeting_id"] == 42


async def test_create_retargeting_list_custom_lifespan():
    mcp, client = _setup({"status": 200, "retargetingId": 7})
    await _invoke(
        mcp,
        "create_retargeting_list",
        {"name": "kupující", "membership_lifespan_days": 90},
    )
    body = client.call.call_args[0][1]
    assert body["membershipLifespan"] == 90


async def test_update_retargeting_list_partial_fields():
    mcp, client = _setup({"status": 200})
    await _invoke(
        mcp,
        "update_retargeting_list",
        {"retargeting_id": 11, "name": "nový název"},
    )
    args = client.call.call_args
    assert args[0][0] == "retargeting.lists.update"
    # Sklik bulk-update convention: body wrapped in a list, matches update_campaign etc.
    assert args[0][1] == [{"id": 11, "name": "nový název"}]


async def test_update_retargeting_list_lifespan_only():
    mcp, client = _setup({"status": 200})
    await _invoke(
        mcp,
        "update_retargeting_list",
        {"retargeting_id": 11, "membership_lifespan_days": 60},
    )
    body = client.call.call_args[0][1]
    assert body == [{"id": 11, "membershipLifespan": 60}]


async def test_remove_retargeting_list():
    mcp, client = _setup({"status": 200})
    await _invoke(mcp, "remove_retargeting_list", {"retargeting_id": 5})
    args = client.call.call_args
    assert args[0][0] == "retargeting.lists.remove"
    assert args[0][1] == {"id": 5}

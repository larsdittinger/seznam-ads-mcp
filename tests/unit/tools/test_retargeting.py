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
            "lists": [{"listId": 1, "name": "vrátí se"}],
        }
    )
    out = await _invoke(mcp, "list_retargeting_lists", {})
    # No extra args, just auth (auto-prepended by SklikClient.call).
    assert client.call.call_args == (("retargeting.lists.list",), {})
    # Sklik returns each list with `listId`, not `id`.
    assert out["retargeting_lists"][0]["listId"] == 1


async def test_create_retargeting_list_default_membership():
    mcp, client = _setup({"status": 200, "listIds": [42]})
    out = await _invoke(mcp, "create_retargeting_list", {"name": "návštěvníci"})
    args = client.call.call_args
    assert args[0][0] == "retargeting.lists.create"
    # Sklik wants [{"attributes": {...}}] with the four required keys.
    assert args[0][1] == [
        {
            "attributes": {
                "name": "návštěvníci",
                "membership": 30,
                "useHistoricData": False,
                "takeAllUsers": True,
            }
        }
    ]
    assert out["retargeting_id"] == 42


async def test_create_retargeting_list_custom_membership_and_flags():
    mcp, client = _setup({"status": 200, "listIds": [7]})
    await _invoke(
        mcp,
        "create_retargeting_list",
        {
            "name": "kupující",
            "membership_days": 90,
            "use_historic_data": True,
            "take_all_users": False,
        },
    )
    attrs = client.call.call_args[0][1][0]["attributes"]
    assert attrs["membership"] == 90
    assert attrs["useHistoricData"] is True
    assert attrs["takeAllUsers"] is False


async def test_update_retargeting_list_partial_fields():
    mcp, client = _setup({"status": 200})
    await _invoke(
        mcp,
        "update_retargeting_list",
        {"retargeting_id": 11, "name": "nový název"},
    )
    args = client.call.call_args
    assert args[0][0] == "retargeting.lists.update"
    # Element key is `listId` (not `id`); editable fields nest under `attributes`.
    assert args[0][1] == [{"listId": 11, "attributes": {"name": "nový název"}}]


async def test_update_retargeting_list_membership_only():
    mcp, client = _setup({"status": 200})
    await _invoke(
        mcp,
        "update_retargeting_list",
        {"retargeting_id": 11, "membership_days": 60},
    )
    body = client.call.call_args[0][1]
    assert body == [{"listId": 11, "attributes": {"membership": 60}}]


async def test_remove_retargeting_list():
    mcp, client = _setup({"status": 200})
    await _invoke(mcp, "remove_retargeting_list", {"retargeting_id": 5})
    args = client.call.call_args
    assert args[0][0] == "retargeting.lists.remove"
    # Sklik wants `[id, ...]` — a bare list of ids in a single positional.
    assert args[0][1] == [5]

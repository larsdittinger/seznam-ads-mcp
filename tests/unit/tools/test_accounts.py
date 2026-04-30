from unittest.mock import MagicMock

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.tools import accounts


def _make_mcp_with_client(call_returns):
    mcp = FastMCP("test")
    client = MagicMock(spec=SklikClient)
    client.call.return_value = call_returns
    client.session = MagicMock(active_user_id=None, token_owner_user_id=10)
    accounts.register(mcp, client)
    return mcp, client


async def _invoke_tool(mcp: FastMCP, name: str, arguments: dict):
    # FastMCP stores tools in mcp._tool_manager._tools (private API but stable in 1.27)
    tool = mcp._tool_manager._tools[name]
    return await tool.run(arguments)


async def test_list_managed_accounts_returns_list():
    mcp, client = _make_mcp_with_client(
        {
            "status": 200,
            "user": {
                "users": [
                    {"userId": 1, "username": "a"},
                    {"userId": 2, "username": "b"},
                ]
            },
        }
    )
    out = await _invoke_tool(mcp, "list_managed_accounts", {})
    assert out["accounts"] == [
        {"user_id": 1, "username": "a"},
        {"user_id": 2, "username": "b"},
    ]
    client.call.assert_called_once_with("client.get")


async def test_switch_account_sets_active():
    mcp, client = _make_mcp_with_client({})
    out = await _invoke_tool(mcp, "switch_account", {"user_id": 42})
    client.set_active_account.assert_called_once_with(42)
    assert out == {"active_user_id": 42}


async def test_current_account_returns_state():
    mcp, client = _make_mcp_with_client({})
    client.session.active_user_id = 7
    out = await _invoke_tool(mcp, "current_account", {})
    assert out == {"active_user_id": 7, "token_owner_user_id": 10}

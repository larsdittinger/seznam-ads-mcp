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


async def test_list_managed_accounts_returns_foreign_accounts():
    mcp, client = _make_mcp_with_client(
        {
            "status": 200,
            "user": {"userId": 100, "username": "owner"},
            "foreignAccounts": [
                {"userId": 1, "username": "a", "access": "rwa"},
                {"userId": 2, "username": "b", "access": "r"},
            ],
        }
    )
    out = await _invoke_tool(mcp, "list_managed_accounts", {})
    assert out["accounts"] == [
        {"user_id": 1, "username": "a", "access": "rwa"},
        {"user_id": 2, "username": "b", "access": "r"},
    ]
    client.call.assert_called_once_with("client.get")


async def test_list_managed_accounts_handles_no_foreign_accounts():
    mcp, _client = _make_mcp_with_client(
        {"status": 200, "user": {"userId": 100, "username": "owner"}}
    )
    out = await _invoke_tool(mcp, "list_managed_accounts", {})
    assert out["accounts"] == []


async def test_switch_account_sets_active():
    mcp, client = _make_mcp_with_client({})
    out = await _invoke_tool(mcp, "switch_account", {"user_id": 42})
    client.set_active_account.assert_called_once_with(42)
    assert out == {"active_user_id": 42}


async def test_current_account_returns_state_when_already_known():
    mcp, client = _make_mcp_with_client({})
    client.session.active_user_id = 7
    client.session.token_owner_user_id = 10
    out = await _invoke_tool(mcp, "current_account", {})
    assert out == {"active_user_id": 7, "token_owner_user_id": 10}
    # No need to refresh — already knew the owner.
    client.call.assert_not_called()


async def test_current_account_refreshes_when_owner_unknown():
    mcp, client = _make_mcp_with_client(
        {"status": 200, "user": {"userId": 999, "username": "x"}}
    )
    client.session.active_user_id = None
    client.session.token_owner_user_id = None
    out = await _invoke_tool(mcp, "current_account", {})
    # _refresh_user_info mutates session.token_owner_user_id; verify call happened.
    client.call.assert_called_once_with("client.get")
    # The mock's session is a MagicMock so we can't easily assert the post-write value;
    # what matters is the refresh path was triggered.
    assert "token_owner_user_id" in out
    assert "active_user_id" in out

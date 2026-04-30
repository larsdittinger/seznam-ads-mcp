"""Multi-account / impersonation tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient


def register(mcp: FastMCP, client: SklikClient) -> None:
    @mcp.tool()
    def list_managed_accounts() -> dict[str, Any]:
        """List Sklik accounts the API token can manage (impersonate / převtělit).

        Returns:
            {"accounts": [{"user_id": int, "username": str}]}
        """
        resp = client.call("client.get")
        users = (resp.get("user") or {}).get("users") or []
        return {
            "accounts": [
                {"user_id": int(u["userId"]), "username": u.get("username", "")} for u in users
            ]
        }

    @mcp.tool()
    def switch_account(user_id: int) -> dict[str, Any]:
        """Switch active Sklik account (převtělit se / impersonate).

        All subsequent tool calls will operate on the account with this user_id.
        Pass 0 or omit to clear and use the token owner's own account.

        Returns:
            {"active_user_id": int | null}
        """
        target = user_id if user_id > 0 else None
        client.set_active_account(target)
        return {"active_user_id": target}

    @mcp.tool()
    def current_account() -> dict[str, Any]:
        """Show which account is currently active (used for all calls).

        Returns:
            {"active_user_id": int | null, "token_owner_user_id": int | null}
        """
        return {
            "active_user_id": client.session.active_user_id,
            "token_owner_user_id": client.session.token_owner_user_id,
        }

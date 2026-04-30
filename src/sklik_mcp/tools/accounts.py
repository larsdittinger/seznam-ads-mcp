"""Multi-account / impersonation tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.core.errors import with_sklik_error_handling


def _refresh_user_info(client: SklikClient) -> dict[str, Any]:
    """Call client.get to refresh token-owner identity + foreign accounts.

    Side effect: sets `client.session.token_owner_user_id` from the response.
    Sklik's login response doesn't carry userId, so this is the canonical way
    to know who the token belongs to.
    """
    resp: dict[str, Any] = client.call("client.get")
    user = resp.get("user") or {}
    if "userId" in user:
        client.session.token_owner_user_id = int(user["userId"])
    return resp


def register(mcp: FastMCP, client: SklikClient) -> None:
    @mcp.tool()
    @with_sklik_error_handling
    def list_managed_accounts() -> dict[str, Any]:
        """List Sklik accounts the API token can manage (impersonate / převtělit).

        Returns the foreignAccounts list — accounts the token owner has been
        granted access to. Empty list = no impersonation; you operate as the
        token owner only.

        Returns:
            {"accounts": [{"user_id": int, "username": str, "access": str}]}
        """
        resp = _refresh_user_info(client)
        foreign = resp.get("foreignAccounts") or []
        return {
            "accounts": [
                {
                    "user_id": int(u["userId"]),
                    "username": u.get("username", ""),
                    "access": u.get("access", ""),
                }
                for u in foreign
            ]
        }

    @mcp.tool()
    @with_sklik_error_handling
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
    @with_sklik_error_handling
    def current_account() -> dict[str, Any]:
        """Show which account is currently active (used for all calls).

        Lazily fetches token-owner identity via client.get if not yet known
        (login response doesn't carry userId).

        Returns:
            {"active_user_id": int | null, "token_owner_user_id": int | null}
        """
        if client.session.token_owner_user_id is None:
            _refresh_user_info(client)
        return {
            "active_user_id": client.session.active_user_id,
            "token_owner_user_id": client.session.token_owner_user_id,
        }

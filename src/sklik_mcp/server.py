"""sklik-mcp entry point. Wires SklikClient + FenixClient + FastMCP and runs over stdio."""

from __future__ import annotations

import logging
import sys

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.core.config import Settings
from sklik_mcp.tools.fenix.client import FenixClient


def _register_all(mcp: FastMCP, client: SklikClient, fenix: FenixClient | None) -> None:
    from sklik_mcp.tools import (
        accounts,
        ad_groups,
        ads,
        campaigns,
        conversions,
        keywords,
        negative_keywords,
        retargeting,
        stats,
    )
    from sklik_mcp.tools.fenix import account as fenix_account
    from sklik_mcp.tools.fenix import product_groups, shopping_stats

    for drak_module in (
        accounts,
        campaigns,
        ad_groups,
        ads,
        keywords,
        negative_keywords,
        stats,
        retargeting,
        conversions,
    ):
        drak_module.register(mcp, client)
    # Fénix tools only registered when SKLIK_FENIX_TOKEN is set — otherwise
    # they'd all fail with the same auth error and confuse users about why.
    if fenix is not None:
        for fenix_module in (fenix_account, product_groups, shopping_stats):
            fenix_module.register(mcp, client, fenix)


def build_server() -> FastMCP:
    # api_token is loaded from env (SKLIK_API_TOKEN); pydantic-settings populates it
    # at runtime, but mypy can't see that and flags it as a missing required arg.
    settings = Settings()  # type: ignore[call-arg]
    logging.basicConfig(
        stream=sys.stderr,  # MUST be stderr — stdout is reserved for MCP JSON-RPC
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    client = SklikClient(
        token=settings.api_token,
        endpoint=settings.endpoint,
        timeout_s=settings.request_timeout_s,
    )
    # Fénix uses an OAuth2 refresh→access flow with its own refresh token
    # (SKLIK_FENIX_TOKEN). When unset, Fénix tools will surface a clear error
    # rather than silently using the Drak API token.
    fenix = FenixClient(
        refresh_token=settings.fenix_token or "",
        endpoint=settings.fenix_endpoint,
        timeout_s=settings.request_timeout_s,
    ) if settings.fenix_token else None
    mcp = FastMCP("sklik-mcp")
    _register_all(mcp, client, fenix)
    return mcp


def main() -> None:
    mcp = build_server()
    mcp.run()


if __name__ == "__main__":
    main()

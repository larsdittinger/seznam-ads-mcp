"""sklik-mcp entry point. Wires SklikClient + FastMCP and runs over stdio."""
from __future__ import annotations

import logging
import sys

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.core.config import Settings


def build_server() -> FastMCP:
    settings = Settings()
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
    mcp = FastMCP("sklik-mcp")
    # Tool modules will register themselves here in later tasks:
    from sklik_mcp.tools import accounts, ad_groups, ads, campaigns, conversions, keywords
    from sklik_mcp.tools import negative_keywords, retargeting, stats
    from sklik_mcp.tools.fenix import product_groups, shopping_stats

    for module in (
        accounts,
        campaigns,
        ad_groups,
        ads,
        keywords,
        negative_keywords,
        stats,
        retargeting,
        conversions,
        product_groups,
        shopping_stats,
    ):
        module.register(mcp, client)
    return mcp


def main() -> None:
    mcp = build_server()
    mcp.run()


if __name__ == "__main__":
    main()

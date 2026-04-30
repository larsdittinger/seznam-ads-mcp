"""Negative-keyword tools (vylučující klíčová slova) — campaign-level only.

Sklik v5 reality (verified live 2026-04-30):

- Negative keywords are NOT a separate JSON-RPC namespace. They live as a
  field `negativeKeywords` on the campaign struct, and are written via
  `campaigns.update` with the whole list replaced at once.
- Element shape is {"name": str, "matchType": "negativeBroad" |
  "negativePhrase" | "negativeExact"}.
- Only available for campaign types `context`, `fulltext`, `product`,
  `simple` — NOT `zbozi` (Shopping). For Shopping, use product groups
  (Fénix) instead.
- READING negative keywords back via the JSON API is not supported in v5
  (`negativeKeywords` is not a valid `displayColumns` value on
  campaigns.list). Callers must track them externally; this module
  provides set-only.
- Group-level negative keywords are NOT supported in v5.
"""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from typing_extensions import TypedDict

from sklik_mcp.core.client import SklikClient
from sklik_mcp.core.errors import with_sklik_error_handling

NegativeMatchType = Literal["broad", "phrase", "exact"]

# Sklik v5 wire values for negative match types — prefixed, unlike regular keywords.
_SKLIK_NEG_MATCH: dict[str, str] = {
    "broad": "negativeBroad",
    "phrase": "negativePhrase",
    "exact": "negativeExact",
}

# Campaign types where negative keywords are valid (per Sklik schema).
_NEGATIVE_OK_TYPES: tuple[str, ...] = ("context", "fulltext", "product", "simple")


class NegativeKeywordInput(TypedDict, total=False):
    """One row passed to set_campaign_negative_keywords."""

    name: str
    match_type: NegativeMatchType


def _build_negative(kw: NegativeKeywordInput) -> dict[str, str]:
    return {
        "name": kw["name"],
        "matchType": _SKLIK_NEG_MATCH[kw.get("match_type", "broad")],
    }


def register(mcp: FastMCP, client: SklikClient) -> None:
    @mcp.tool()
    @with_sklik_error_handling
    def set_campaign_negative_keywords(
        campaign_id: int,
        campaign_type: Literal["context", "fulltext", "product", "simple"],
        keywords: list[NegativeKeywordInput],
    ) -> dict[str, Any]:
        """Replace the entire negative-keyword list on a campaign.

        Sklik v5 stores negative keywords as a field on the campaign and
        only supports replacing the whole list at once (no incremental
        add/remove). Callers must pass the full desired list.

        Args:
            campaign_id: Campaign to modify.
            campaign_type: Must match the campaign's type. Sklik requires it
                in every campaigns.update call. Use one of context, fulltext,
                product, simple. Negative keywords are NOT available for
                "zbozi" (Shopping) campaigns.
            keywords: Full list of negative keywords. Each entry is
                {"name": str, "match_type": "broad"|"phrase"|"exact"}.
                Pass an empty list to clear.

        Returns:
            {"updated": true, "count": int}
        """
        body = {
            "id": campaign_id,
            "type": campaign_type,
            "negativeKeywords": [_build_negative(kw) for kw in keywords],
        }
        client.call("campaigns.update", [body])
        return {"updated": True, "count": len(keywords)}

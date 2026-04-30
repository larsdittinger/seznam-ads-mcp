"""Keyword tools (klíčová slova) — list, get, add (batch), update, pause/resume, remove."""
from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP
from typing_extensions import TypedDict

from sklik_mcp.core.client import SklikClient

KeywordStatus = Literal["active", "paused", "removed"]
MatchType = Literal["broad", "phrase", "exact"]

# Sklik wire-level match types (its API uses "broad" / "phraseMatch" / "exactMatch")
_SKLIK_MATCH: dict[str, str] = {
    "broad": "broad",
    "phrase": "phraseMatch",
    "exact": "exactMatch",
}


class KeywordInput(TypedDict, total=False):
    """One row passed to add_keywords. `max_cpc_kc` is optional."""

    keyword: str
    match_type: MatchType
    max_cpc_kc: int | None


def _build_keyword_create(group_id: int, kw: KeywordInput) -> dict:
    body: dict = {
        "groupId": group_id,
        "keyword": kw["keyword"],
        "matchType": _SKLIK_MATCH[kw["match_type"]],
    }
    if kw.get("max_cpc_kc") is not None:
        body["maxCpc"] = kw["max_cpc_kc"] * 100  # Kč → haléře
    return body


def register(mcp: FastMCP, client: SklikClient) -> None:
    @mcp.tool()
    def list_keywords(
        group_id: int | None = None,
        status: KeywordStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """List keywords (seznam klíčových slov) with optional filters.

        Args:
            group_id: Limit to keywords in this ad group (Sklik filter `groupIds`).
            status: Only return keywords with this status (active/paused/removed).
            limit: Max number of keywords to return.
            offset: Pagination offset.

        Returns:
            {"keywords": [...], "total": int}
        """
        filt: dict = {}
        if group_id is not None:
            filt["groupIds"] = [group_id]
        if status is not None:
            filt["status"] = status
        opts = {"limit": limit, "offset": offset}
        resp = client.call("keywords.list", filt, opts)
        return {
            "keywords": resp.get("keywords", []),
            "total": resp.get("totalCount", 0),
        }

    @mcp.tool()
    def get_keyword(keyword_id: int) -> dict:
        """Get a single keyword by ID.

        Returns:
            {"keyword": {...}} or {"keyword": null} if not found.
        """
        resp = client.call("keywords.list", {"id": [keyword_id]}, {})
        items = resp.get("keywords", [])
        return {"keyword": items[0] if items else None}

    @mcp.tool()
    def add_keywords(group_id: int, keywords: list[KeywordInput]) -> dict:
        """Add a batch of keywords (přidat klíčová slova) to an ad group.

        Args:
            group_id: Parent ad group ID applied to every row.
            keywords: List of {keyword, match_type, max_cpc_kc?} structs. `match_type`
                must be one of "broad", "phrase", "exact". `max_cpc_kc` is in Kč
                (will be converted to haléře internally) — pass `None` to omit.

        Returns:
            {"keyword_ids": [int, ...]}
        """
        body = [_build_keyword_create(group_id, kw) for kw in keywords]
        resp = client.call("keywords.create", body)
        return {"keyword_ids": resp.get("keywordIds") or []}

    @mcp.tool()
    def update_keyword(
        keyword_id: int,
        max_cpc_kc: int | None = None,
        status: KeywordStatus | None = None,
    ) -> dict:
        """Update fields on an existing keyword (only the supplied ones).

        Args:
            keyword_id: Target keyword ID.
            max_cpc_kc: New max CPC in Kč (converted to haléře).
            status: New status (active/paused/removed).

        Returns:
            {"updated": true}
        """
        body: dict = {"id": keyword_id}
        if max_cpc_kc is not None:
            body["maxCpc"] = max_cpc_kc * 100
        if status is not None:
            body["status"] = status
        client.call("keywords.update", [body])
        return {"updated": True}

    @mcp.tool()
    def pause_keyword(keyword_id: int) -> dict:
        """Pause a keyword (pozastavit klíčové slovo)."""
        client.call("keywords.update", [{"id": keyword_id, "status": "paused"}])
        return {"paused": True, "keyword_id": keyword_id}

    @mcp.tool()
    def resume_keyword(keyword_id: int) -> dict:
        """Resume a paused keyword (znovu spustit klíčové slovo)."""
        client.call("keywords.update", [{"id": keyword_id, "status": "active"}])
        return {"resumed": True, "keyword_id": keyword_id}

    @mcp.tool()
    def remove_keyword(keyword_id: int) -> dict:
        """Remove (soft-delete) a keyword (smazat klíčové slovo)."""
        client.call("keywords.remove", [keyword_id])
        return {"removed": True, "keyword_id": keyword_id}

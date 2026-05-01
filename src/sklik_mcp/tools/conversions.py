"""Conversion tools (konverze) — list defined conversions and fetch stats.

Wire shape, verified live 2026-05-01:

- `conversions.list` returns the conversion definitions configured on the account.
- There is **no** `conversions.stats` / `conversions.readReport` / `conversions.createReport`
  method in Drak v5 — they all return non-JSON 404. Instead Sklik exposes
  per-conversion-action stats via `client.stats(splitByConversions: true)`,
  which returns a `conversionList` array per row with one entry per defined
  conversion.

`get_conversion_stats` rides on that flow: it calls `client.stats` once with
`splitByConversions=true` and pulls the matching `conversionList` entry out.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from sklik_mcp.core.client import SklikClient
from sklik_mcp.core.errors import with_sklik_error_handling

_CONV_MONEY_FIELDS = (
    "price",
    "conversionValue",
    "conversionAvgPrice",
    "conversionAvgValue",
    "transactionAvgPrice",
    "transactionAvgValue",
)


def _add_conv_kc(item: dict[str, Any]) -> dict[str, Any]:
    out = dict(item)
    for f in _CONV_MONEY_FIELDS:
        if f in out and isinstance(out[f], (int, float)):
            out[f"{f}_kc"] = out[f] / 100
    return out


def register(mcp: FastMCP, client: SklikClient) -> None:
    @mcp.tool()
    @with_sklik_error_handling
    def list_conversions() -> dict[str, Any]:
        """List all conversion definitions (konverze) on the active account.

        Returns:
            {"conversions": [{"id": int, "name": str, ...}, ...]}
        """
        resp = client.call("conversions.list")
        return {"conversions": resp.get("conversions", [])}

    @mcp.tool()
    @with_sklik_error_handling
    def get_conversion_stats(
        conversion_id: int,
        date_from: str,
        date_to: str,
        granularity: str = "total",
    ) -> dict[str, Any]:
        """Get stats for a single conversion definition over a date window.

        Drak v5 has no dedicated conversions stats endpoint. Under the hood
        this calls `client.stats(splitByConversions: true)` and pulls the
        matching `conversionList` entry from each row.

        Args:
            conversion_id: ID from `list_conversions`.
            date_from: ISO date YYYY-MM-DD (inclusive).
            date_to: ISO date YYYY-MM-DD (inclusive).
            granularity: total / daily / weekly / monthly / quarterly / yearly.

        Returns:
            {"report": [{"date": str, "conversions": int, "conversionValue": int,
            "conversionValue_kc": float, "transactions": int, ...}]}
            One row per period. Money fields in haléře with `_kc` mirrors.
            Empty `report` if the conversion never fired in the window.
        """
        resp = client.call(
            "client.stats",
            {
                "dateFrom": date_from,
                "dateTo": date_to,
                "granularity": granularity,
                "splitByConversions": True,
            },
        )
        out: list[dict[str, Any]] = []
        for row in resp.get("report", []) or []:
            for entry in row.get("conversionList") or []:
                if entry.get("id") == conversion_id:
                    rec = _add_conv_kc(entry)
                    rec["date"] = row.get("date")
                    out.append(rec)
                    break
        return {"report": out}

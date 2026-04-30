"""Czech-friendly formatters for money, percentages, dates."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


def format_money_haler(haler: int) -> str:
    """Sklik reports spend/bids in haléře. 100 haléřů = 1 Kč."""
    return f"{haler / 100:.2f} Kč"


def format_pct(ratio: float) -> str:
    return f"{ratio * 100:.2f}%"


def parse_date(s: str | date | datetime) -> date:
    if isinstance(s, datetime):
        return s.date()
    if isinstance(s, date):
        return s
    return date.fromisoformat(s)


def add_kc_field(item: dict[str, Any], source: str = "spend") -> dict[str, Any]:
    """Augment a stats row with a Kč-formatted field (haléře / 100).

    Returns a shallow copy of `item` with `{source}_kc` added when `source`
    holds an int/float. Used by stats / conversions / any money report.
    """
    out = dict(item)
    val = out.get(source)
    if isinstance(val, (int, float)):
        out[f"{source}_kc"] = val / 100
    return out

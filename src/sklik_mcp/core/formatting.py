"""Czech-friendly formatters for money, percentages, dates."""
from __future__ import annotations

from datetime import date, datetime


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

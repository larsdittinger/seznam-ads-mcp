from sklik_mcp.core.formatting import format_money_haler, format_pct, parse_date


def test_format_money_haler_to_kc():
    # Sklik returns money in haléře (1 Kč = 100 haléřů)
    assert format_money_haler(12345) == "123.45 Kč"
    assert format_money_haler(0) == "0.00 Kč"
    assert format_money_haler(100) == "1.00 Kč"


def test_format_pct():
    assert format_pct(0.1234) == "12.34%"
    assert format_pct(0) == "0.00%"


def test_parse_date_iso():
    d = parse_date("2026-04-30")
    assert d.year == 2026
    assert d.month == 4
    assert d.day == 30
